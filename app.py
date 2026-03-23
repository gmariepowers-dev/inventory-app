from flask import Flask, request, render_template, redirect, url_for, abort, flash, jsonify
from models import db, Item, User, AuditLog
import os
from functools import wraps

from barcode import Code128
from barcode.writer import ImageWriter

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

# --------------------
# App setup
# --------------------
app = Flask(__name__, static_folder="static", template_folder="templates", instance_relative_config=True)
app.config["SECRET_KEY"] = "dev-secret-change-later"

os.makedirs(app.instance_path, exist_ok=True)
db_path = os.path.join(app.instance_path, "inventory.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# --------------------
# Login manager
# --------------------
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --------------------
# Admin guard
# --------------------
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped

# --------------------
# Audit logger
# --------------------
def log_audit(action, target=None, details=None):
    db.session.add(
        AuditLog(
            actor_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            target=target,
            details=details
        )
    )
    db.session.commit()

# --------------------
# Auth
# --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            log_audit("login", target=user.username)
            return redirect(request.args.get("next") or url_for("index"))
        flash("Invalid username or password", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    log_audit("logout", target=current_user.username)
    logout_user()
    return redirect(url_for("login"))

# --------------------
# Inventory
# --------------------
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        sku = request.form["sku"]

        if Item.query.filter_by(sku=sku).first():
            flash("SKU already exists", "error")
            return redirect(url_for("index"))

        barcode_dir = os.path.join(app.static_folder, "barcodes")
        os.makedirs(barcode_dir, exist_ok=True)

        barcode = Code128(sku, writer=ImageWriter())
        barcode.save(os.path.join(barcode_dir, sku))
        barcode_path = f"/static/barcodes/{sku}.png"

        image = request.files.get("image")
        image_path = None

        if image and image.filename:
            image_dir = os.path.join(app.static_folder, "uploads")
            os.makedirs(image_dir, exist_ok=True)
            filename = f"{sku}_{image.filename}"
            image.save(os.path.join(image_dir, filename))
            image_path = f"/static/uploads/{filename}"

        item = Item(
            name=request.form["name"],
            sku=sku,
            quantity=int(request.form.get("quantity") or 0),
            dimensions=request.form.get("dimensions"),
            colorways=request.form.get("colorways"),
            manufacturer=request.form.get("manufacturer"),
            cost_price=float(request.form.get("cost_price") or 0),
            retail_price=float(request.form.get("retail_price") or 0),
            barcode_path=barcode_path,
            image_path=image_path
        )

        db.session.add(item)
        db.session.commit()

        log_audit("create_item", target=item.sku, details=item.name)

        flash("Item added successfully", "success")
        return redirect(url_for("index"))

    items = Item.query.all()
    return render_template("index.html", items=items)

@app.route("/set-quantity/<int:item_id>", methods=["POST"])
@login_required
def set_quantity(item_id):

    item = Item.query.get_or_404(item_id)

    data = request.get_json()
    new_qty = int(data.get("quantity",0))

    item.quantity = new_qty

    db.session.commit()

    return jsonify({"success": True})
# --------------------
# Summary
# --------------------
@app.route("/summary")
@login_required
def summary():

    items = Item.query.all()

    total_items = len(items)
    total_quantity = sum(item.quantity or 0 for item in items)
    total_value = sum((item.quantity or 0) * (item.cost_price or 0) for item in items)

    labels = [item.name for item in items]
    quantities = [item.quantity or 0 for item in items]

    return render_template(
        "summary.html",
        total_items=total_items,
        total_quantity=total_quantity,
        total_value=total_value,
        items=items,
        labels=labels,
        quantities=quantities
    )
# --------------------
# Labels
# --------------------
@app.route("/labels")
@login_required
def labels_page():
    items = Item.query.all()
    return render_template("labels.html", items=items)


@app.route("/generate-label/<int:item_id>")
@login_required
def generate_label(item_id):

    item = Item.query.get_or_404(item_id)

    return render_template(
        "labels.html",
        item=item
    )
# --------------------
# Item API (modal)
# --------------------
@app.route("/item/<int:item_id>")
@login_required
def get_item(item_id):
    item = Item.query.get_or_404(item_id)
    return jsonify(item.to_dict())

# --------------------
# Admin
# --------------------
@app.route("/admin")
@login_required
@admin_required
def admin():
    users = User.query.all()
    logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(10).all()

    return render_template(
        "admin.html",
        users=users,
        logs=logs
    )

@app.route("/admin/users/create", methods=["POST"])
@login_required
@admin_required
def create_user():

    username = request.form["username"]
    password = request.form["password"]
    is_admin = bool(request.form.get("is_admin"))

    if User.query.filter_by(username=username).first():
        flash("User already exists", "error")
        return redirect(url_for("admin"))

    new_user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role="admin" if is_admin else "viewer"
    )

    db.session.add(new_user)
    db.session.commit()

    log_audit("create_user", target=username)

    flash("User created", "success")

    return redirect(url_for("admin"))

from werkzeug.security import generate_password_hash

@app.route("/admin/add-user", methods=["GET", "POST"])
@login_required
@admin_required
def add_user():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("admin"))  # ✅ INSIDE function

    return render_template("add_user.html")

@app.route("/admin/users/edit/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def edit_user(user_id):

    user = User.query.get_or_404(user_id)

    # Prevent deleting/changing yourself dangerously later if you want
    new_role = request.form["role"]
    user.role = new_role

    db.session.commit()

    log_audit("edit_user", target=user.username, details=f"role -> {new_role}")

    flash("User updated", "success")
    return redirect(url_for("admin"))


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):

    user = User.query.get_or_404(user_id)

    if user.username == "admin":
        flash("Cannot delete main admin", "error")
        return redirect(url_for("admin"))

    db.session.delete(user)
    db.session.commit()

    log_audit("delete_user", target=user.username)

    flash("User deleted", "success")
    return redirect(url_for("admin"))

# --------------------
# Audit Logs Page
# --------------------
@app.route("/admin/logs")
@login_required
@admin_required
def view_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(200).all()
    return render_template("audit_logs.html", logs=logs)

from flask import Response
import csv

@app.route("/admin/audit/export")
@login_required
@admin_required
def export_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()

    def generate():
        data = csv.writer([])
        yield "timestamp,user,action,item\n"
        for log in logs:
            yield f"{log.created_at},{log.actor_id},{log.action},{log.target}\n"

    return Response(generate(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=audit_logs.csv"})

# --------------------
# Barcode Scanner
# --------------------
@app.route("/scan/<barcode>")
@login_required
def scan_item(barcode):

    barcode = barcode.strip()

    item = Item.query.filter(Item.sku.contains(barcode)).first()

    if not item:
        return {"found": False}

    return {
        "found": True,
        "id": item.id
    }

# --------------------
# Create default admin
# --------------------
def create_admin_if_missing():

    if not User.query.filter_by(username="admin").first():

        admin = User(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            role="admin"
        )

        db.session.add(admin)
        db.session.commit()


# --------------------
# Run
# --------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_admin_if_missing()

    app.run(debug=True)
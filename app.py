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
        if user and check_password_hash(user.password, request.form["password"]):
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
def labels():
    return render_template("labels.html", items=Item.query.all())

@app.route("/generate-label/<int:item_id>")
@login_required
def generate_label(item_id):
    item = Item.query.get_or_404(item_id)

    barcode_dir = os.path.join(app.static_folder, "barcodes")
    os.makedirs(barcode_dir, exist_ok=True)
    barcode = Code128(item.sku, writer=ImageWriter())
    barcode.save(os.path.join(barcode_dir, item.sku))

    log_audit("generate_label", target=item.sku)
    flash("Label generated!", "success")
    return redirect(url_for("index"))

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
    log_audit("view_admin")
    return render_template("admin.html", users=User.query.all())

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

    db.session.add(User(username=username, password=generate_password_hash(password), is_admin=is_admin))
    db.session.commit()

    log_audit("create_user", target=username)
    flash("User created", "success")
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

# --------------------
# Create default admin
# --------------------
def create_admin_if_missing():
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password=generate_password_hash("admin123"), is_admin=True))
        db.session.commit()

# --------------------
# Run
# --------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_admin_if_missing()
    app.run(debug=True)
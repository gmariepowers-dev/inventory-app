from flask import Flask, request, render_template, redirect, url_for, abort, flash, jsonify, Response
from models import db, Item, User, AuditLog
import os,time, shutil, csv
import time
import shutil
import csv

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
from werkzeug.utils import secure_filename

# --------------------
# Config
# --------------------
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# --------------------
# App setup
# --------------------
app = Flask(__name__, static_folder="static", template_folder="templates", instance_relative_config=True)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 #5MB upload limit

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

        # Validation
        if not sku:
            flash("SKU is required", "error")
            return redirect(url_for("index"))

        if not request.form["name"]:
            flash("Item name is required", "error")
            return redirect(url_for("index"))
        
        if len(request.form["name"]) > 200:
            flash("Name too long", "error")
            return redirect(url_for("index"))
        
        if len(sku) > 100:
            flash("SKU too long", "error")
            return redirect(url_for("index"))

        if Item.query.filter_by(sku=sku).first():
            flash("SKU already exists", "error")
            return redirect(url_for("index"))

        # Quantity validation
        qty = int(request.form.get("quantity") or 0)

        if qty < 0:
            flash("Quantity cannot be negative", "error")
            return redirect(url_for("index"))

        # Barcode 
        barcode_dir = os.path.join(app.static_folder, "barcodes")
        os.makedirs(barcode_dir, exist_ok=True)

        barcode = Code128(sku, writer=ImageWriter())
        barcode.save(os.path.join(barcode_dir, sku))
        barcode_path = f"/static/barcodes/{sku}.png"

        # Image upload
        image = request.files.get("image")
        image_path = None

        if image and image.filename:
            if not allowed_file(image.filename):
                flash("Invalid image type", "error")
                return redirect(url_for("index"))
            
            image_dir = os.path.join(app.static_folder, "uploads")
            os.makedirs(image_dir, exist_ok=True)

            filename = secure_filename(f"{sku}_{image.filename}")
            image.save(os.path.join(image_dir, filename))
            image_path = f"/static/uploads/{filename}"

        # Create item
        item = Item(
            name=request.form["name"],
            sku=sku,
            quantity=qty,
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
# Item APIs
# --------------------
@app.route("/item/<int:item_id>")
@login_required
def get_item(item_id):
    return jsonify(Item.query.get_or_404(item_id).to_dict())

@app.route("/edit-item/<int:item_id>", methods=["POST"])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    data = request.get_json()

    item.manufacturer = data.get("manufacturer")
    item.dimensions = data.get("dimensions")
    item.colorways = data.get("colorways")
    item.cost_price = float(data.get("cost_price") or 0)
    item.retail_price = float(data.get("retail_price") or 0)

    db.session.commit()
    log_audit("edit_item", target=item.sku)

    return jsonify({"success": True})

@app.route("/set-quantity/<int:item_id>", methods=["POST"])
@login_required
def set_quantity(item_id):
    item = Item.query.get_or_404(item_id)
    data = request.get_json()

    new_qty = int(data.get("quantity", 0))
    if new_qty < 0:
        return jsonify({"error": "Invalid quantity"}), 400

    item.quantity = new_qty
    db.session.commit()

    log_audit("set_quantity", target=item.sku, details=str(new_qty))

    return jsonify({"success": True})

@app.route("/adjust-quantity/<int:item_id>", methods=["POST"])
@login_required
def adjust_quantity(item_id):
    item = Item.query.get_or_404(item_id)
    data = request.get_json()

    change = int(data.get("change", 0))
    item.quantity = max(0, (item.quantity or 0) + change)

    db.session.commit()

    return jsonify({"new_quantity": item.quantity})

@app.route("/delete-item/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)

    db.session.delete(item)
    db.session.commit()

    log_audit("delete_item", target=item.sku)

    flash("Item deleted", "success")
    return redirect(url_for("index"))

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
    return render_template("labels.html", items=Item.query.all())

@app.route("/generate-label/<int:item_id>")
@login_required
def generate_label(item_id):
    return render_template("labels.html", item=Item.query.get_or_404(item_id))

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

@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot delete yourself", "error")
        return redirect(url_for("admin"))

    if user.username == "admin":
        flash("Cannot delete main admin", "error")
        return redirect(url_for("admin"))

    db.session.delete(user)
    db.session.commit()

    log_audit("delete_user", target=user.username)

    flash("User deleted", "success")
    return redirect(url_for("admin"))

@app.route("/admin/users/edit/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def edit_user(user_id):

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot change your own role", "error")
        return redirect(url_for("admin"))

    new_role = request.form["role"]
    user.role = new_role

    db.session.commit()

    log_audit("edit_user", target=user.username, details=f"role -> {new_role}")

    flash("User updated", "success")
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
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).all()

    def generate():
        yield "timestamp,user,action,item\n"
        for log in logs:
            yield f"{log.created_at},{log.actor_id},{log.action},{log.target}\n"

    return Response(generate(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=audit_logs.csv"})

# --------------------
# Backup
# --------------------
@app.route("/admin/backup")
@login_required
@admin_required
def backup_db():
    backup_path = os.path.join(app.instance_path, f"backup_{int(time.time())}.db")
    shutil.copy(db_path, backup_path)
    flash("Backup created", "success")
    return redirect(url_for("admin"))


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
# Error handlers
# --------------------
@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

# --------------------
# Run
# --------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_admin_if_missing()

    app.run(debug=False)

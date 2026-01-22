from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from models import db, Item
import os
import uuid
from barcode import Code128
from barcode.writer import ImageWriter

# --------------------
# App setup
# --------------------
app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
    instance_relative_config=True
)

# Ensure instance folder exists BEFORE database connection
os.makedirs(app.instance_path, exist_ok=True)

# Absolute path to SQLite DB (this is the key fix)
db_path = os.path.join(app.instance_path, "inventory.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# --------------------
# File storage
# --------------------
UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
BARCODE_FOLDER = os.path.join(app.static_folder, "barcodes")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BARCODE_FOLDER, exist_ok=True)

# --------------------
# Routes
# --------------------
@app.route("/", methods=["GET", "POST"])
def index():
    search_query = request.args.get("search", "").lower()

    if request.method == "POST":
        name = request.form.get("name")
        sku = request.form.get("sku")
        weight = request.form.get("weight")
        price = request.form.get("price")
        photo = request.files.get("photo")

        if Item.query.filter_by(sku=sku).first():
            return "SKU already exists", 400

        photo_path = ""
        if photo and photo.filename:
            ext = photo.filename.rsplit(".", 1)[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            photo_path = f"uploads/{filename}"
            photo.save(os.path.join(app.static_folder, photo_path))

        barcode = Code128(sku, writer=ImageWriter())
        barcode.save(os.path.join(BARCODE_FOLDER, sku))

        item = Item(
            name=name,
            sku=sku,
            weight=weight,
            price=float(price) if price else None,
            quantity=1,
            photo_path=photo_path,
            barcode_path=f"/static/barcodes/{sku}.png"
        )

        db.session.add(item)
        db.session.commit()

        return redirect(url_for("index"))

    items = Item.query.all()

    if search_query:
        items = [
            item for item in items
            if search_query in item.name.lower()
            or search_query in item.sku.lower()
        ]
    print("ITEM COUNT:", len(items))

    return render_template("index.html", items=items, search_query=search_query)

# --------------------
# Quantity controls
# --------------------
@app.route("/quantity/<int:item_id>/<action>", methods=["POST"])
def update_quantity(item_id, action):
    item = Item.query.get_or_404(item_id)

    if action == "increase":
        item.quantity += 1
    elif action == "decrease" and item.quantity > 0:
        item.quantity -= 1

    db.session.commit()
    return redirect(url_for("index"))

@app.route("/quantity/set/<int:item_id>", methods=["POST"])
def set_quantity(item_id):
    item = Item.query.get_or_404(item_id)

    try:
        qty = int(request.form.get("quantity", item.quantity))
        if qty >= 0:
            item.quantity = qty
            db.session.commit()
    except ValueError:
        pass

    return redirect(url_for("index"))

# --------------------
# Admin
# --------------------
@app.route("/admin")
def admin():
    return render_template("admin.html")

# --------------------
# Run
# --------------------
if __name__ == "__main__":
    app.run(debug=True)
#if __name__ == "__main__":
    #app.run(debug=True, port=5001)

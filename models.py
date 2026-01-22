from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)

    price = db.Column(db.Float)
    weight = db.Column(db.String(50))

    color = db.Column(db.String(50))
    length = db.Column(db.Float)
    width = db.Column(db.Float)
    height = db.Column(db.Float)

    quantity = db.Column(db.Integer, default=1)

    barcode_path = db.Column(db.String(200))
    photo_path = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

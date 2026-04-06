from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()

# --------------------
# User
# --------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    role = db.Column(db.String(20), default="viewer")
    # roles: admin, editor, viewer

    audit_logs = db.relationship(
        "AuditLog",
        back_populates="actor",
        cascade="all, delete-orphan",
    )

    @property
    def is_active(self):
        return True
    
    @property
    def is_admin(self):
        return self.role == "admin"
    
# --------------------
# Item
# --------------------
class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(100), unique=True, nullable=False)

    quantity = db.Column(db.Integer, default=0)

    weight = db.Column(db.String(50))
    dimensions = db.Column(db.String(200))
    colorways = db.Column(db.String(200))
    manufacturer = db.Column(db.String(200))

    cost_price = db.Column(db.Float, default=0)
    retail_price = db.Column(db.Float, default=0)
    low_stock_threshold = db.Column(db.Integer, default=5)

    order_link = db.Column(db.String(300))

    barcode_path = db.Column(db.String(300))
    image_path = db.Column(db.String(300))

    def to_dict(self):
        quantity = self.quantity or 0
        retail_price = self.retail_price or 0

        return {
            "id": self.id,
            "name": self.name,
            "sku": self.sku,
            "quantity": quantity,
            "manufacturer": self.manufacturer,
            "dimensions": self.dimensions,
            "colorways": self.colorways,
            "cost_price": self.cost_price,
            "retail_price": retail_price,
            "image_path": self.image_path,
            "barcode_path": self.barcode_path,
            "order_link": self.order_link,
            "weight": self.weight,
            "low_stock_threshold": self.low_stock_threshold,
            "total_retail_value": quantity * retail_price
        }

    def __repr__(self):
        return f"<Item {self.name} ({self.sku})>"
# --------------------
# Audit Log
# --------------------
class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    action = db.Column(db.String(200), nullable=False)
    target = db.Column(db.String(200))
    details = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    actor = db.relationship("User", back_populates="audit_logs")

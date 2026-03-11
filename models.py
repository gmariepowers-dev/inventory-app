from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()

# --------------------
# User
# --------------------
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    is_admin = db.Column(db.Boolean, default=False)

    audit_logs = db.relationship(
        "AuditLog",
        back_populates="actor",
        cascade="all, delete-orphan",
    )

    # Flask-Login expects this attribute
    @property
    def is_active(self):
        return True


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

    cost_price = db.Column(db.Float)
    retail_price = db.Column(db.Float)

    order_link = db.Column(db.String(300))

    barcode_path = db.Column(db.String(300))
    image_path = db.Column(db.String(300))


    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "sku": self.sku,
            "quantity": self.quantity,
            "weight": self.weight,
            "dimensions": self.dimensions,
            "colorways": self.colorways,
            "manufacturer": self.manufacturer,
            "order_link": self.order_link,
            "image_url": self.image_path,
            "barcode_url": self.barcode_path
        }
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

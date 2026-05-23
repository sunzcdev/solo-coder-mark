from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "username": self.username}


whiteboard_members = db.Table(
    "whiteboard_members",
    db.Column("whiteboard_id", db.Integer, db.ForeignKey("whiteboards.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)


class Whiteboard(db.Model):
    __tablename__ = "whiteboards"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    invite_token = db.Column(db.String(32), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("User", foreign_keys=[owner_id], backref=db.backref("owned_boards", lazy=True))
    members = db.relationship("User", secondary=whiteboard_members, backref=db.backref("boards", lazy="dynamic"))
    shapes = db.relationship("Shape", back_populates="whiteboard", cascade="all, delete-orphan", order_by="Shape.order_index")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "owner_id": self.owner_id,
            "invite_token": self.invite_token,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Shape(db.Model):
    __tablename__ = "shapes"
    id = db.Column(db.Integer, primary_key=True)
    whiteboard_id = db.Column(db.Integer, db.ForeignKey("whiteboards.id"), nullable=False, index=True)
    type = db.Column(db.String(16), nullable=False)  # pen | rect | circle | clear
    color = db.Column(db.String(16), nullable=False, default="#000000")
    width = db.Column(db.Integer, nullable=False, default=3)
    data = db.Column(db.Text, nullable=False, default="[]")  # JSON payload
    order_index = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    whiteboard = db.relationship("Whiteboard", back_populates="shapes")

    def to_dict(self):
        import json
        try:
            points = json.loads(self.data)
        except Exception:
            points = []
        return {
            "id": self.id,
            "type": self.type,
            "color": self.color,
            "width": self.width,
            "points": points,
        }

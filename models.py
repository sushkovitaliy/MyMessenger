from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
import enum

db = SQLAlchemy()

def current_time():
    return datetime.now(timezone.utc) + timedelta(hours=3)

class RoleEnum(enum.Enum):
    USER = 'обычный'
    ADMIN = 'админ'
    
    def __str__(self):
        return self.value

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    avatar = db.Column(db.String(200), nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Enum(RoleEnum), default=RoleEnum.USER)
    is_blocked = db.Column(db.Boolean, default=False)
    blocked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=current_time)
    
    # Отношения
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == RoleEnum.ADMIN
    
    def block(self):
        self.is_blocked = True
        self.blocked_at = current_time()
    
    def unblock(self):
        self.is_blocked = False
        self.blocked_at = None
        
    def get_avatar_letter(self):
        return self.username[0].upper() if self.username else '?'

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    is_deleted_for_sender = db.Column(db.Boolean, default=False)
    is_deleted_for_receiver = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=current_time)
    
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def delete_for_user(self, user_id):
        # Удаляет сообщение для конкретного пользователя
        if self.sender_id == user_id:
            self.is_deleted_for_sender = True
        elif self.receiver_id == user_id:
            self.is_deleted_for_receiver = True
    
    def is_visible_for_user(self, user_id):
        # Проверяет, видимо ли сообщение для пользователя
        if self.sender_id == user_id:
            return not self.is_deleted_for_sender
        elif self.receiver_id == user_id:
            return not self.is_deleted_for_receiver
        return False
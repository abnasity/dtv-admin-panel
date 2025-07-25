from datetime import datetime
from flask_login import UserMixin
from flask import current_app, url_for, has_request_context
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db 
from app import bcrypt, login_manager
from sqlalchemy import text, Numeric, func
from itsdangerous import URLSafeTimedSerializer
import os
from app.utils.image_utils import save_device_image, cloudinary_or_default
from cloudinary.utils import cloudinary_url  
from app.utils.mixins import ResetTokenMixin



# USERS MODEL
# This model represents both admin and staff users in the system.
# Admins have full access, while staff have limited permissions.
class User(UserMixin, db.Model, ResetTokenMixin): #usermodel for authentication and authorization
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='staff')  # 'admin' or 'staff'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    
    # Relationships
    sales = db.relationship('Sale', backref='seller', lazy='dynamic')
    created_by = db.relationship('User', backref='created_users',  remote_side=[id], uselist=False)
   
    
    def set_password(self, password):
        """Hash and set user password using bcrypt"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Verify password against hash using bcrypt"""
        return bcrypt.check_password_hash(self.password_hash, password)
    def is_staff(self):
        return self.role == 'staff'
    def is_admin(self):
        """Check if user has admin role"""
        return str(self.role).lower() == 'admin'
    
    
    def get_id(self):
      return f'user-{self.id}'
  
  
    def to_dict(self):
        """Convert user object to dictionary for API responses"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'address' : self.address,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_seen': self.last_seen.isoformat()
        }
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

        


def static_image_path(filename):
    if has_request_context():
        return url_for('static', filename=filename)
    return f"/static/{filename}"       
#  DEVICE MODEL
class Device(db.Model):
    """Enhanced Device model with advanced image management"""
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    imei = db.Column(db.String(15), unique=True, nullable=True, index=True)
    brand = db.Column(db.String(50), nullable=False, index=True)
    model = db.Column(db.String(100), nullable=False, index=True)
    ram = db.Column(db.String(20), nullable=False)
    rom = db.Column(db.String(20), nullable=False)
    purchase_price = db.Column(Numeric(10, 2), nullable=False)
    price_cash = db.Column(Numeric(10, 2), nullable=True)
    price_credit = db.Column(Numeric(10, 2), nullable=True)
    description = db.Column(db.Text, default="No description available.")
    status = db.Column(db.String(20), default='available', index=True)
    arrival_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    color = db.Column(db.String(50), nullable=True)
    image_variants = db.Column(db.JSON, default=dict, nullable=True)
    main_image = db.Column(db.String(255), nullable=True) 
    image_folder = db.Column(db.String(255), nullable=True)
    specs_id = db.Column(db.Integer, db.ForeignKey('device_specs.id'), nullable=True)
    slug = db.Column(db.String(100), unique=True, index=True)
    featured = db.Column(db.Boolean, default=False)
    deleted = db.Column(db.Boolean, default=False, nullable=False)
    

 
    # Relationships
    sale = db.relationship('Sale', back_populates='device', uselist=False)
    specs = db.relationship('DeviceSpecs', back_populates='device', uselist=False, foreign_keys=[specs_id])

    transactions = db.relationship('InventoryTransaction', back_populates='device')
    alerts = db.relationship('Alert', back_populates='device')
    
    @classmethod
    def get_featured(cls):
        return cls.query.filter(cls.featured == True, cls.deleted == False).all()
    @staticmethod
    def get_available():
        return Device.query.filter(Device.deleted == False, Device.status == 'available').all()

    @property
    def is_available(self):
     """Check if device is available for sale"""
     return str(self.status).lower() == 'available'
     
    def mark_as_sold(self):
        """Mark device as sold and update timestamp"""
        self.status = 'sold'
        self.modified_at = datetime.utcnow()
        db.session.commit()

    # Status Management
    # Image Handling

    @property
    def image_url(self):
      return cloudinary_or_default(self.main_image)
   
    @property
    def thumbnail_url(self):
        return cloudinary_or_default(self.main_image, thumbnail=True)



    # Serialization
    def to_dict(self, include_variants=False):
        """Enhanced serialization with image support"""
        data = {
            'id': self.id,
            'imei': self.imei,
            'brand': self.brand,
            'model': self.model,
            'color': self.color,
            'ram': self.ram,
            'rom': self.rom,
            'status': self.status,
            'purchase_price': float(self.purchase_price),
            'price_cash': float(self.price_cash) if self.price_cash else None,
            'price_credit': float(self.price_credit) if self.price_credit else None,
            'image_url': self.image_url,
            'thumbnail_url': self.thumbnail_url,
            'arrival_date': self.arrival_date.isoformat(),
            'modified_at': self.modified_at.isoformat()
        }
        
        if include_variants:
            data['image_variants'] = self.get_image_variants()
            
        return data

    def __repr__(self):
        return f"<Device {self.brand} {self.model} ({self.color or 'no color'})>"

# DEVICE SPECS
class DeviceSpecs(db.Model):
    __tablename__ = 'device_specs'
    id = db.Column(db.Integer, primary_key=True)
    details = db.Column(db.Text)  

    device = db.relationship(
            'Device',
            back_populates='specs',
            uselist=False
        )


# INVENTORY TRANSACTION MODEL
# This model tracks all inventory transactions for products, including purchases, sales, adjustments, and stock movements.
class InventoryTransaction(db.Model):
    __tablename__ = 'inventory_transactions'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    type = db.Column(db.String(20), nullable=False)  # 'arrival', 'sale', 'adjustment'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    # Relationships
    device = db.relationship('Device', back_populates='transactions')
    staff = db.relationship('User', backref='inventory_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'type': self.type,
            'staff_id': self.staff_id,
            'timestamp': self.timestamp.isoformat(),
            'notes': self.notes
        }


    
# SALE MODEL FOR DEVICES ONLY
# This model tracks sales of devices, linking them to the device and seller.
class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    sale_price = db.Column(db.Numeric(10, 2), nullable=False)
    payment_type = db.Column(db.String(20), nullable=False)  # 'cash', 'credit'
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)

    # Foreign Keys
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), unique=True, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device = db.relationship("Device", back_populates="sale")
        
    @property
    def is_fully_paid(self):
      return self.amount_paid >= self.sale_price

# RECEIPT ITEM MODEL
class ReceiptItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey('receipts.id'))
    product_name = db.Column(db.String(100))
    price = db.Column(db.Float)
    quantity = db.Column(db.Integer)
    total = db.Column(db.Float)

# RECEIPT MODEL
class Receipt(db.Model):
    __tablename__ = 'receipts'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id')) 
    date = db.Column(db.Date, default=datetime.utcnow)
    time = db.Column(db.Time, default=func.now())
    total = db.Column(db.Float, nullable=False)

    # Relationship
    items = db.relationship('ReceiptItem', backref='receipt', lazy=True)


  
# NOTIFICATION MODEL
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)   
    type = db.Column(db.String(50))  # e.g., 'assignment', 'approval', 'reminder'
    recipient_type = db.Column(db.String(20), default='staff')  

    # Relationship
    user = db.relationship('User', backref='notifications', lazy=True)

    def __repr__(self):
        return f"<Notification id={self.id} user_id={self.user_id} read={self.is_read} message='{self.message[:30]}...'>"

        
# ALERT MODEL
# This model tracks alerts for products, such as low stock or new product arrivals.
class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(30), nullable=False)  # e.g., 'low_stock', 'arrival'
    status = db.Column(db.String(20), nullable=False, default='active')
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text)

    # Relationships
    device = db.relationship('Device', back_populates='alerts')
    created_by = db.relationship('User', backref='created_alerts')

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'type': self.type,
            'triggered_at': self.triggered_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'status': self.status,
            'notes': self.notes,
            'created_by': self.created_by.to_dict() if self.created_by else None
        }

    def __repr__(self):
        return f"<Alert Device ID: {self.device_id}, Type: {self.type}, Status: {self.status}>"
 

@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith("user-"):
        return User.query.get(int(user_id.replace("user-", "")))
    return None



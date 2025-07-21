from datetime import datetime
from flask_login import UserMixin
from flask import current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db 
from app import bcrypt, login_manager
from sqlalchemy import text, Numeric
from itsdangerous import URLSafeTimedSerializer
import os
from app.utils.image_utils import save_device_image
from cloudinary.utils import cloudinary_url  




# USERS MODEL
# This model represents both admin and staff users in the system.
# Admins have full access, while staff have limited permissions.
class User(UserMixin, db.Model): #usermodel for authentication and authorization
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
    
    def is_customer(self):
        return False
    
    def get_id(self):
      return f'user-{self.id}'
  
    def get_reset_token(self, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=1800)['user_id']
        except Exception:
            return None
        return User.query.get(user_id)
    
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

        
        
# CUSTOMERS MODEL
class Customer(UserMixin, db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    id_number = db.Column(db.String(30), nullable=True, unique=True, comment="Kenyan National ID Number")
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True, unique=True)
    # Customer-specific
    delivery_address = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='customer')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    


    # Relationship: customer purchases (you must add customer_id in Sale model)
    cart_items = db.relationship('CartItem', back_populates='customer', lazy=True, cascade='all, delete-orphan')
    purchases = db.relationship('Sale', backref='customer', cascade='all, delete-orphan', foreign_keys='Sale.customer_id')
    orders = db.relationship( 'CustomerOrder', back_populates='customer',cascade='all, delete-orphan',lazy=True
)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_customer(self):
        return self.role == 'customer'
   
    def is_admin(self):
        return False
    
    def is_staff(self):
     return False

    def get_id(self):
        return f'customer-{self.id}'  # distinguish from admin/staff users

    def __repr__(self):
        return f'<Customer {self.email}>'
    
    def get_reset_token(self, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'customer_id': self.id})
    
    
    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            customer_id = s.loads(token, max_age=expires_sec)['customer_id']
        except Exception:
            return None
        return Customer.query.get(customer_id)


    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'phone_number': self.phone_number,
            'delivery_address' : self.delivery_address,
            'created_at': self.created_at.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'role': self.role,
            'is_active': self.is_active
        }
    def __repr__(self):
        return f"<Customer {self.full_name} ({self.email})>"
    

 
#  CUSTOMERORDER MODEL
# This model represents customer orders, which can include multiple products.
class CustomerOrder(db.Model):
    __tablename__ = 'customer_orders'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'cancelled', 'rejected'
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    delivery_address = db.Column(db.String(255))
    payment_option = db.Column(db.String(20), nullable=False)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_staff = db.relationship('User', backref='assigned_customers', foreign_keys=[assigned_staff_id])
    is_deleted = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)

# relationships
    customer = db.relationship('Customer', back_populates='orders')
    items = db.relationship(
        'CustomerOrderItem', 
        back_populates='customer_order',  # Changed from 'order'
        lazy=True,
        cascade='all, delete-orphan',
        foreign_keys='CustomerOrderItem.order_id'
    )

    approved_by = db.relationship('User', foreign_keys=[approved_by_id])

    def is_pending(self):
        return self.status == 'pending'
    
    def total_amount(self):
        return sum(item.unit_price for item in self.items)

    def get_total(self):
         return sum(item.device.purchase_price or 0 for item in self.items)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'approved_by': self.approved_by.to_dict() if self.approved_by else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'delivery_address' : self.delivery_address,
            'items': [item.to_dict() for item in self.items],
            'notes': self.notes
        }

    def __repr__(self):
        return f"<CustomerOrder ID: {self.id} - Status: {self.status}>"


# CARTITEM MODEL FOR DEVICES ONLY
class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)  
    quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='active')  # active, ordered, received 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    device = db.relationship(
        "Device",
        back_populates="cart_items"
    )
    customer = db.relationship(
        "Customer",
        back_populates="cart_items"
    )

    def __repr__(self):
        return f"<CartItem customer={self.customer_id} device={self.device_id} quantity={self.quantity}>"



# CUSTOMER ORDER ITEM MODEL
# This model represents items in customer orders, linking products to customer orders.
class CustomerOrderItem(db.Model):
    __tablename__ = 'customer_order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('customer_orders.id', ondelete='CASCADE'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)

    # Relationship to device
    customer_order = db.relationship(
        "CustomerOrder",
        back_populates="items"  # Matches the name above
    )
    
    device = db.relationship(
        "Device",
        back_populates="items"
    )

    def to_dict(self):
     return {
        'device': self.device.to_dict() if self.device else None,
        'unit_price': float(self.unit_price)  # ensure it's serializable
    }


    def __repr__(self):
        return f"<CustomerOrderItem Device ID: {self.device_id}, Price: {self.unit_price}>"

    
        
#  DEVICE MODEL
class Device(db.Model):
    """Enhanced Device model with advanced image management"""
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    imei = db.Column(db.String(15), unique=True, nullable=True, index=True)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    ram = db.Column(db.String(20), nullable=False)
    rom = db.Column(db.String(20), nullable=False)
    purchase_price = db.Column(Numeric(10, 2), nullable=False)
    price_cash = db.Column(Numeric(10, 2), nullable=True)
    price_credit = db.Column(Numeric(10, 2), nullable=True)
    description = db.Column(db.Text, default="No description available.")
    status = db.Column(db.String(20), default='available')
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

    items = db.relationship(
        'CustomerOrderItem', 
        back_populates='device', 
        lazy=True,
        cascade='all, delete-orphan'
    )
    cart_items = db.relationship('CartItem', back_populates='device', lazy=True)
    transactions = db.relationship('InventoryTransaction', back_populates='device')
    alerts = db.relationship('Alert', back_populates='device')
    
    @classmethod
    def get_featured(cls):
        return cls.query.filter(cls.featured == True, cls.deleted == False).all()

    @staticmethod
    def get_available():
        return Device.query.filter_by(deleted=False, is_available=True).all()


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
        if self.main_image:
            url, _ = cloudinary_url(self.main_image, format="jpg", secure=True)
            return url
        return url_for('static', filename='images/default-device.jpg')

    @property
    def thumbnail_url(self):
        if self.main_image:
            url, _ = cloudinary_url(self.main_image, width=300, height=300, crop="fill", gravity="auto", secure=True)
            return url
        return url_for('static', filename='images/default-device.jpg')


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

# SOLD DEVICE MODEL
class SoldDevice(db.Model):
    __tablename__ = 'sold_devices'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('customer_orders.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sold_at = db.Column(db.DateTime, default=datetime.utcnow)



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
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    device = db.relationship("Device", back_populates="sale")
        
    @property
    def is_fully_paid(self):
      return self.amount_paid >= self.sale_price
  
# NOTIFICATION MODEL
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)   
    type = db.Column(db.String(50))  # e.g., 'assignment', 'approval', 'reminder'
    recipient_type = db.Column(db.String(20), default='customer')  

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
    """Flask-Login user loader callback for multiple user types"""
    if user_id.startswith("user-"):
        return User.query.get(int(user_id.replace("user-", "")))
    elif user_id.startswith("customer-"):
        return Customer.query.get(int(user_id.replace("customer-", "")))
    return None


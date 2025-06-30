from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db 
from app import bcrypt, login_manager
from sqlalchemy import text

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
 
     
    def get_id(self):
        return f'customer-{self.id}'  # distinguish from admin/staff users

    def __repr__(self):
        return f'<Customer {self.email}>'

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
    approved_at = db.Column(db.DateTime, nullable=True)
    delivery_address = db.Column(db.String(255))
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_staff = db.relationship('User', backref='assigned_customers', foreign_keys=[assigned_staff_id])
    notes = db.Column(db.Text)

# relationships
    customer = db.relationship('Customer', back_populates='orders')
    items = db.relationship('CustomerOrderItem', backref='order', lazy=True, cascade='all, delete-orphan', foreign_keys='CustomerOrderItem.order_id')

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
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)  
    status = db.Column(db.String(20), default='active')  # active, ordered, received 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', back_populates='cart_items')
    device = db.relationship('Device', backref='cart_items')

    def __repr__(self):
        return f"<CartItem customer={self.customer_id} device={self.device_id}>"


# CUSTOMER ORDER ITEM MODEL
# This model represents items in customer orders, linking products to customer orders.
class CustomerOrderItem(db.Model):
    __tablename__ = 'customer_order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('customer_orders.id', ondelete='CASCADE'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)

    # Relationship to device
    device = db.relationship("Device", backref="order_items")

    def to_dict(self):
     return {
        'device': self.device.to_dict() if self.device else None
    }

    def to_dict(self):
     return {
        'device': self.device.to_dict() if self.device else None,
        'unit_price': float(self.unit_price)  # ensure it's serializable
    }


    def __repr__(self):
        return f"<CustomerOrderItem Device ID: {self.device_id}, Price: {self.unit_price}>"

    
        
#  DEVICE MODEL
class Device(db.Model):
    """Device model for mobile phone inventory management"""
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    imei = db.Column(db.String(15), unique=True, nullable=False, index=True)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    ram = db.Column(db.String(20), nullable=False)  # e.g., '4GB', '6GB'
    rom = db.Column(db.String(20), nullable=False)  # e.g., '64GB', '128GB'
    purchase_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='available')  # available, sold
    arrival_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Relationship
    sale = db.relationship('Sale', backref='device', uselist=False)

    @property
    def is_available(self):
        """Check if device is available for sale"""
        return self.status == 'available'

    def mark_as_sold(self):
        """Mark device as sold"""
        self.status = 'sold'
        self.modified_at = datetime.utcnow()
    
    def to_dict(self):
     return {
        'id': self.id,
        'imei': self.imei,
        'brand': self.brand,
        'model': self.model,
        'ram': self.ram,
        'rom': self.rom,
        'status': self.status,
        'purchase_price': str(self.purchase_price),
        'arrival_date': self.arrival_date.isoformat(),
    }

    def __repr__(self):
     return f"<Device {self.brand} {self.model}"


# SOLD DEVICE MODEL
class SoldDevice(db.Model):
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
    device = db.relationship('Device', backref='transactions')
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
        
    @property
    def is_fully_paid(self):
      return self.amount_paid >= self.sale_price
  
# NOTIFICATION MODEL
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(50))  # e.g., 'assignment', 'approval', 'reminder'


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
    device = db.relationship('Device', backref='alerts')
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


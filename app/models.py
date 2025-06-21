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
    
    # Relationships
    sales = db.relationship('Sale', backref='seller', lazy='dynamic')
    created_by = db.relationship('User', backref='created_users',  remote_side=[id], uselist=False)
    
    def set_password(self, password):
        """Hash and set user password using bcrypt"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Verify password against hash using bcrypt"""
        return bcrypt.check_password_hash(self.password_hash, password)

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
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
   

    role = db.Column(db.String(20), nullable=False, default='customer')
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship: customer purchases (you must add customer_id in Sale model)
    cart_items = db.relationship('CartItem', back_populates='customer', lazy=True)
    purchases = db.relationship('Sale', backref='customer', cascade='all, delete-orphan', foreign_keys='Sale.customer_id')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_customer(self):
        return self.role == 'customer'

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
            'address': self.address,
            'created_at': self.created_at.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'role': self.role,
            'is_active': self.is_active
        }
    def __repr__(self):
        return f"<Customer {self.full_name} ({self.email})>"
    
        
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
        """Convert device object to dictionary for API responses"""
        return {
            'id': self.id,
            'imei': self.imei,
            'brand': self.brand,
            'model': self.model,
            'ram' : self.ram,
            'rom' : self.rom,
            'purchase_price': str(self.purchase_price),
            'status': self.status,
            'arrival_date': self.arrival_date.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'notes': self.notes
        }
    def __repr__(self):
     return f"<Device {self.brand} {self.model}"

# CARTITEM MODEL FOR DEVICES ONLY
class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)   
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', back_populates='cart_items')
    device = db.relationship('Device', backref='cart_items')

    def __repr__(self):
        return f"<CartItem customer={self.customer_id} device={self.device_id}>"


# PRODUCT MODEL
# This model represents products in the inventory, which can be devices or other items.
class Product(db.Model):
    """Product model for inventory management"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    reorder_level = db.Column(db.Integer, default=0, nullable=False)  # Minimum stock level before reorder
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    inventory_transactions = db.relationship('InventoryTransaction', backref='product', cascade='all, delete-orphan')
    po_items = db.relationship('PurchaseOrderItem', backref='product', cascade='all, delete-orphan')
    sales = db.relationship('Sale', backref='product', cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='product', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert product object to dictionary for API responses"""
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,
            'unit_price': str(self.unit_price),
            'reorder_level': self.reorder_level,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    def __repr__(self):
     return f"<Product {self.name} (SKU: {self.sku})>"


# INVENTORY TRANSACTION MODEL
# This model tracks all inventory transactions for products, including purchases, sales, adjustments, and stock movements.
class InventoryTransaction(db.Model):
    __tablename__ = 'inventory_transactions'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    type = db.Column(db.String(20), nullable=False)  # 'purchase', 'sale', 'adjustment', 'add', 'remove'. 'loss'
    quantity = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    
    def to_dict(self):
        """Convert inventory transaction object to dictionary for API responses"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'staff_id': self.staff_id,
            'type': self.type,
            'quantity': self.quantity,
            'timestamp': self.timestamp.isoformat()
        }
    def __repr__(self):
     return f"<InventoryTransaction {self.type} - Product ID: {self.product_id}, Qty: {self.quantity}>"

    
# PURCHASE ORDER MODEL
# This model represents purchase orders made to suppliers for products.
# It tracks the supplier, order date, status, and items in the order.
class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    id = db.Column(db.Integer, primary_key=True)
    supplier = db.Column(db.String(150), nullable=False)
    order_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False) #
    'pending','received','cancelled'
    created_by = db.Column(db.Integer, db.ForeignKey('users.id',
    ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
    default=datetime.utcnow)
    items = db.relationship('PurchaseOrderItem',
    backref='purchase_order', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'supplier': self.supplier_name,
            'order_date': self.order_date.isoformat(),
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'items': self.items_to_dict()
        }
    def __repr__(self):
     return f"<PurchaseOrder {self.id} - Supplier: {self.supplier}, Status: {self.status}>"

   
    # PURCHASE ORDER ITEM MODEL
# This model represents items in purchase orders, linking products to purchase orders.
class  PurchaseOrderItem(db.Model):
    """Purchase Order Item model for tracking items in purchase orders"""
    __tablename__ = 'purchase_order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False) 
    
    def to_dict(self):
        """Convert purchase order item object to dictionary for API responses"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'purchase_order_id': self.purchase_order_id,
            'quantity': self.quantity,
            'unit_cost': str(self.unit_cost)
        }
    def __repr__(self):
     return f"<PurchaseOrderItem Product ID: {self.product_id}, Qty: {self.quantity}>"


# SALE MODEL FOR DEVICES ONLY
# This model tracks sales of devices, linking them to the device and seller.
class Sale(db.Model):
    """Sale model for tracking device sales"""
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    sale_price = db.Column(db.Numeric(10, 2), nullable=False)
    payment_type = db.Column(db.String(20), nullable=False)  # cash, credit
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Foreign Keys
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), unique=True, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)


    @property
    def profit(self):
        """Calculate profit from sale"""
        return float(self.sale_price) - float(self.device.purchase_price)

    @property
    def balance_due(self):
        """Calculate remaining balance for credit sales"""
        return float(self.sale_price) - float(self.amount_paid)

    @property
    def is_fully_paid(self):
        """Check if sale is fully paid"""
        return self.balance_due <= 0
    
    def to_dict(self):
        """Convert sale object to dictionary for API responses"""
        return {
            'id': self.id,
            'device': self.device.to_dict(),
            'seller': self.seller.to_dict(),
            'sale_price': str(self.sale_price),
            'payment_type': self.payment_type,
            'amount_paid': str(self.amount_paid),
            'balance_due': str(self.balance_due),
            'profit': str(self.profit),
            'is_fully_paid': self.is_fully_paid,
            'sale_date': self.sale_date.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'notes': self.notes
        }
    def __repr__(self):
     return f"<Sale ID: {self.id} - Device ID: {self.device_id} - Seller ID: {self.seller_id}>"

        
# SALE ITEM MODEL 
# meant for product-based (non-IMEI) sales
class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    sold_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    
    def to_dict(self):
        """Convert sale item object to dictionary for API responses"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'seller_id': self.seller_id,
            'quantity': self.quantity,
            'unit_price': str(self.unit_price),
            'sold_at': self.sold_at.isoformat()
        }
    def __repr__(self):
     return f"<SaleItem Product ID: {self.product_id}, Qty: {self.quantity}>"
 
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
    notes = db.Column(db.Text)

# relationships
    customer = db.relationship('Customer', backref='orders')
    items = db.relationship('CustomerOrderItem', backref='order', cascade='all, delete-orphan')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])

    def is_pending(self):
        return self.status == 'pending'

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'approved_by': self.approved_by.to_dict() if self.approved_by else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'items': [item.to_dict() for item in self.items],
            'notes': self.notes
        }

    def __repr__(self):
        return f"<CustomerOrder ID: {self.id} - Status: {self.status}>"

    
# CUSTOMER ORDER ITEM MODEL
# This model represents items in customer orders, linking products to customer orders.
class CustomerOrderItem(db.Model):
    __tablename__ = 'customer_order_items'

    id = db.Column(db.Integer, primary_key=True)
    customer_order_id = db.Column(db.Integer, db.ForeignKey('customer_orders.id', ondelete='CASCADE'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)

    # Relationship to device
    device = db.relationship("Device", backref="order_items")

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.customer_order_id,
            'device_id': self.device_id,
            'unit_price': str(self.unit_price)
        }

    def __repr__(self):
        return f"<CustomerOrderItem Device ID: {self.device_id}, Price: {self.unit_price}>"


        
# ALERT MODEL
# This model tracks alerts for products, such as low stock or new product arrivals.
class Alert(db.Model):
    """Alert model for tracking product alerts"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(30), nullable=False)  # e.g., 'low_stock', 'new_product'
    triggered_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)  # active, resolved, dismissed, unread, sent
    
    def to_dict(self):
        """Convert alert object to dictionary for API responses"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'type': self.type,
            'triggered_at': self.triggered_at.isoformat(),
            'status': self.status           
        }
        
    def __repr__(self):
         return f"<Alert Product ID: {self.product_id}, Type: {self.type}, Status: {self.status}>" 

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback for multiple user types"""
    if user_id.startswith("user-"):
        return User.query.get(int(user_id.replace("user-", "")))
    elif user_id.startswith("customer-"):
        return Customer.query.get(int(user_id.replace("customer-", "")))
    return None


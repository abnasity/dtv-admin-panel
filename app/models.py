from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db 
from app import bcrypt, login_manager

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

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback"""
    return User.query.get(int(user_id))


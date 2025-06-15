from app import create_app, db
from app.models import User, Device


def seed_database():
    """Seed the database with initial data"""
    app = create_app()
    with app.app_context():
        # Create admin user if doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("✅ Created admin user")
        
        # Create test staff user if doesn't exist
        staff = User.query.filter_by(username='staff').first()
        if not staff:
            staff = User(
                username='staff',
                email='staff@example.com',
                role='staff',
                is_active=True
            )
            staff.set_password('staff123')
            db.session.add(staff)
            print("✅ Created staff user")
        
        # Sample device data
        devices_data = [
            {
                'imei': '123456789012345',
                'brand': 'Samsung',
                'model': 'Galaxy S21',
                'ram': '8GB',
                'rom': '256GB',
                'purchase_price': 95500.00
            },
            {
                'imei': '987654321098765',
                'brand': 'Apple',
                'model': 'iPhone 13',
                'ram': '8GB',
                'rom': '512GB',
                'purchase_price': 80700.00
            },
            {
                'imei': '456789012345678',
                'brand': 'Google',
                'model': 'Pixel 6',
                'ram': '8GB',
                'rom': '128GB',
                'purchase_price': 25450.00
            }
        ]
        
        # Create sample devices if they don't exist
        for device_data in devices_data:
            device = Device.query.filter_by(imei=device_data['imei']).first()
            if not device:
                device = Device(
                    imei=device_data['imei'],
                    brand=device_data['brand'],
                    model=device_data['model'],
                    ram=device_data['ram'],
                    rom=device_data['rom'],
                    purchase_price=device_data['purchase_price'],
                    status='available'  # or is_available=True depending on your model
                )
                db.session.add(device)
                print(f"✅ Created device: {device_data['brand']} {device_data['model']}")
            
        try:
            db.session.commit()
            print("Database seeded successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding database: {e}")

if __name__ == '__main__':
    seed_database()

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
       
            
        try:
            db.session.commit()
            print("Database seeded successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding database: {e}")

if __name__ == '__main__':
    seed_database()

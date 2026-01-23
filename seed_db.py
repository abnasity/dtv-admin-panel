from app import create_app, db
from app.models import User

def seed_database():
    app = create_app()
    with app.app_context():

        def create_user(username, email, role, password):
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username,
                    email=email,
                    role=role,
                    is_active=True
                )
                user.set_password(password)
                db.session.add(user)
                print(f"✅ Created {role} user: {username}")

        create_user("admin", "admin@example.com", "admin", "admin123")
        create_user("staff", "staff@example.com", "staff", "staff123")
        create_user("Diamond", "kiptokorir@gmail.com", "admin", "Dtv@2026")

        try:
            db.session.commit()
            print("🎉 Database seeded successfully")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error seeding database: {e}")

if __name__ == "__main__":
    seed_database()

from app import create_app, db
from app.models import User
import sys

def create_admin_user(username, email, password):
    app = create_app()
    with app.app_context():

        user = User.query.filter_by(username=username).first()

        if user:
            user.email = email
            user.role = "admin"
            user.set_password(password)
            print(f"🔄 Updated user '{username}' to admin")
        else:
            user = User(
                username=username,
                email=email,
                role="admin",
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
            print(f"✅ Created admin user '{username}'")

        db.session.commit()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <username> <email> <password>")
        sys.exit(1)

    create_admin_user(sys.argv[1], sys.argv[2], sys.argv[3])

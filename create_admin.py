from app import create_app
from app.extensions import bcrypt, db
from app.models import User
import sys

def create_admin_user(username, email, password):
    """Create a new admin user or update existing user to admin role"""
    app = create_app()
    
    with app.app_context():
        # Check if user already exists
        user = User.query.filter_by(username=username).first()
        if user:
            # Update existing user
            user.email = email
            user.role = 'admin'
            user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
            db.session.commit()
            print(f" User '{username}' has been updated to admin role.")
        else:
            # Create new admin user
            hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
            user = User(
                username=username,
                email=email,
                password_hash=hashed_password,
                role="admin",
                is_active=True
            )
            db.session.add(user)
            db.session.commit()  
            print(f" Admin user '{username}' has been created successfully.")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <username> <email> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    
    create_admin_user(username, email, password)

from app import create_app
from app.extensions import db
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Create app with environment-based config
app = create_app()
with app.app_context():
    db.create_all()
    print("Database created successfully!")

if __name__ == "__main__":
    app.run(debug=True)

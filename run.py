from app import create_app
from app.extensions import db
from dotenv import load_dotenv
import os

load_dotenv()
app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database created successfully!")
    app.run(debug=True)

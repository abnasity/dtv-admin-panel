import os
from app import create_app
from app.extensions import db
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Create app with environment-based config
app = create_app()


# ✅ Create all tables if they don't exist
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    # Use port and debug mode from env if set, otherwise defaults
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    port = int(os.environ.get("PORT", 5000))

    app.run(debug=debug, host="0.0.0.0", port=port)

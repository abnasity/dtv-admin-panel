import os
from app import create_app
from app.extensions import db

# ✅ Only load .env locally (not in production)
if os.environ.get("FLASK_ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()

# Create app
app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug, port=port)

# ✅ DEBUG: Show Cloudinary-related env vars
print("CLOUD_NAME:", os.getenv("CLOUDINARY_CLOUD_NAME"))
print("API_KEY:", os.getenv("CLOUDINARY_API_KEY"))
print("API_SECRET:", os.getenv("CLOUDINARY_API_SECRET"))
print("CLOUDINARY_URL:", os.getenv("CLOUDINARY_URL"))

# Create app
app = create_app()
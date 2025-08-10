# index.py
from app import create_app

# Create your Flask app
app = create_app()

if __name__ == "__main__":
    # This allows you to run it locally
    app.run(host="0.0.0.0", port=5000, debug=True)

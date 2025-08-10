# api/index.py
from run import create_app  # Import your existing app object from run.py

def handler(environ, start_response):
    return app.wsgi_app(environ, start_response)

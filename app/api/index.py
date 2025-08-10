from run import create_app  # Import the factory function

app = create_app()  # Create the Flask app

def handler(environ, start_response):
    return app.wsgi_app(environ, start_response)

# index.py

from app import create_app

# Create the Flask app (used by WSGI servers like Gunicorn or Vercel)
app = create_app()

# AWS Lambda–style handler for environments like API Gateway
def handler(event, context):
    """
    Optional Lambda handler so this same file can run on AWS Lambda.
    Vercel will ignore this and use `app` directly.
    """
    environ = {
        'REQUEST_METHOD': event['httpMethod'],
        'PATH_INFO': event['path'],
        'QUERY_STRING': event.get('queryStringParameters', ''),
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
        'wsgi.input': event.get('body', ''),
        'wsgi.url_scheme': 'https',
        'wsgi.version': (1, 0),
        'wsgi.errors': None,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
    }

    # Add headers
    headers = event.get('headers', {})
    for key, value in headers.items():
        environ[f'HTTP_{key.upper().replace("-", "_")}'] = value

    # Collect response
    response_body = []

    def start_response(status, response_headers, exc_info=None):
        response_body.extend([status, response_headers])
        return lambda data: response_body.append(data)

    # Call Flask WSGI app
    result = app(environ, start_response)

    return {
        'statusCode': int(response_body[0].split()[0]),
        'headers': dict(response_body[1]),
        'body': ''.join(chunk.decode() if isinstance(chunk, bytes) else str(chunk) for chunk in result),
    }

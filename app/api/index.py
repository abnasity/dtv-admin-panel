from app import create_app
from werkzeug.wrappers import Request as WerkzeugRequest

app = create_app()

def handler(event, context):
    # Convert Vercel event to WSGI environ
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

    # Call Flask as WSGI app
    response_body = []
    def start_response(status, response_headers, exc_info=None):
        response_body.extend([status, response_headers])
        return lambda data: response_body.append(data)

    response = app(environ, start_response)
    return {
        'statusCode': 200,
        'headers': dict(response_body[1]),
        'body': ''.join(str(chunk) for chunk in response_body[2:]),
    }
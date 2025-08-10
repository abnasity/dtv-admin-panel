from app import create_app
from vercel.request import Request
from vercel.response import Response

app = create_app()

def handler(request: Request) -> Response:
    with app.app_context():
        return Response(
            app.full_dispatch_request(),
            status=200,
            headers=dict(app.response_class().headers)
        )
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

class ResetTokenMixin:
    def get_reset_token(self, expires_sec=1800):
        """Generate a time-limited reset token."""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'id': self.id})

    @staticmethod
    def verify_reset_token(token, model, expires_sec=1800):
        """Verify token and return user/customer instance from given model."""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = serializer.loads(token, max_age=expires_sec)
        except Exception:
            return None
        return model.query.get(data.get('id'))

import jwt
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from user.models import UserProfileModel


def generate_jwt_token(user):
    """Generate JWT token for a user."""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(seconds=settings.JWT_ACCESS_TOKEN_LIFETIME),
        'iat': datetime.utcnow()
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def decode_jwt_token(token):
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed('Token has expired')
    except jwt.InvalidTokenError:
        raise AuthenticationFailed('Invalid token')


class JWTAuthentication(BaseAuthentication):
    """Custom JWT authentication class for DRF."""

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return None

        try:
            # Expected format: "Bearer <token>"
            prefix, token = auth_header.split()

            if prefix.lower() != 'bearer':
                raise AuthenticationFailed('Invalid authentication scheme')

            payload = decode_jwt_token(token)
            user_id = payload.get('user_id')

            if not user_id:
                raise AuthenticationFailed('Token payload invalid')

            try:
                user = UserProfileModel.objects.get(id=user_id)
            except UserProfileModel.DoesNotExist:
                raise AuthenticationFailed('User not found')

            if not user.is_active:
                raise AuthenticationFailed('User is inactive')

            return (user, token)

        except ValueError:
            raise AuthenticationFailed('Invalid authorization header format')

    def authenticate_header(self, request):
        return 'Bearer'

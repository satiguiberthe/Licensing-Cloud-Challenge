from rest_framework import authentication, exceptions
from django.utils import timezone
from django.conf import settings
from licenses.models import License, LicenseToken
from user.models import UserProfileModel
from authentication.jwt_utils import decode_jwt_token
import jwt
import logging

logger = logging.getLogger(__name__)


class HybridJWTAuthentication(authentication.BaseAuthentication):
    """
    Hybrid JWT authentication that supports both user tokens and license tokens.
    Tries user authentication first, then license authentication.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user/license, token).
        """
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return None
        
        try:
            # Extract token from header
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
            else:
                token = auth_header
            
            if not token:
                return None
            
            # Decode token to check its type
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM]
                )
            except jwt.ExpiredSignatureError:
                raise exceptions.AuthenticationFailed('Token has expired')
            except jwt.InvalidTokenError as e:
                logger.error(f"Invalid token error: {e}")
                raise exceptions.AuthenticationFailed('Invalid token')
            
            # Check if it's a user token (has user_id)
            if 'user_id' in payload:
                return self.authenticate_user(token, payload)
            
            # Check if it's a license token (has tenant_id)
            elif 'tenant_id' in payload:
                return self.authenticate_license(token, payload)
            
            else:
                raise exceptions.AuthenticationFailed('Token payload invalid: missing user_id or tenant_id')
                
        except exceptions.AuthenticationFailed:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise exceptions.AuthenticationFailed('Authentication failed')
    
    def authenticate_user(self, token, payload):
        """Authenticate using user token."""
        user_id = payload.get('user_id')
        
        if not user_id:
            raise exceptions.AuthenticationFailed('Token payload invalid')
        
        try:
            user = UserProfileModel.objects.get(id=user_id)
        except UserProfileModel.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')
        
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User is inactive')
        
        return (user, token)
    
    def authenticate_license(self, token, payload):
        """Authenticate using license token."""
        tenant_id = payload.get('tenant_id')
        
        if not tenant_id:
            raise exceptions.AuthenticationFailed('Invalid token payload')
        
        try:
            license = License.objects.get(tenant_id=tenant_id)
        except License.DoesNotExist:
            raise exceptions.AuthenticationFailed('License not found')
        
        # Validate license
        now = timezone.now()
        
        if license.status != 'ACTIVE':
            raise exceptions.AuthenticationFailed(f'License is {license.status.lower()}')
        
        if now < license.valid_from:
            raise exceptions.AuthenticationFailed('License not yet valid')
        
        if now > license.valid_to:
            raise exceptions.AuthenticationFailed('License has expired')
        
        # Update token usage
        try:
            token_obj = LicenseToken.objects.get(
                token=token,
                license=license,
                is_active=True
            )
            token_obj.last_used_at = timezone.now()
            token_obj.save(update_fields=['last_used_at'])
        except LicenseToken.DoesNotExist:
            # Token not tracked in database, which is okay for stateless JWT
            pass
        
        return (license, token)
    
    def authenticate_header(self, request):
        """Return the authentication header value."""
        return 'Bearer'


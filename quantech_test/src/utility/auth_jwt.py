from rest_framework import authentication
from rest_framework import exceptions
from django.utils import timezone
from django.conf import settings
from licenses.models import License, LicenseToken
import jwt
import logging

logger = logging.getLogger(__name__)


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT authentication for license tokens.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (license, token).
        """
        auth_header = self.get_authorization_header(request)
        if not auth_header:
            return None
        
        try:
            token = self.get_token_from_header(auth_header)
            if not token:
                return None
            
            # Decode and verify the token
            payload = self.verify_token(token)
            
            # Get the license from the payload
            license = self.get_license_from_payload(payload)
            
            # Validate the license
            self.validate_license(license)
            
            # Update token last used timestamp
            self.update_token_usage(token, license)
            
            return (license, token)
            
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token error: {e}")
            raise exceptions.AuthenticationFailed('Invalid token')
        except License.DoesNotExist:
            raise exceptions.AuthenticationFailed('License not found')
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise exceptions.AuthenticationFailed('Authentication failed')
    
    def get_authorization_header(self, request):
        """
        Extract the Authorization header from the request.
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header:
            # Also check for X-License-Token header as an alternative
            return request.META.get('HTTP_X_LICENSE_TOKEN', '')
        return auth_header
    
    def get_token_from_header(self, auth_header):
        """
        Extract token from the authorization header.
        Supports both "Bearer <token>" and direct token formats.
        """
        if not auth_header:
            return None
        
        # Remove 'Bearer ' prefix if present
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        return auth_header
    
    def verify_token(self, token):
        """
        Verify and decode the JWT token.
        """
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
    
    def get_license_from_payload(self, payload):
        """
        Get the license instance from the token payload.
        """
        tenant_id = payload.get('tenant_id')
        if not tenant_id:
            raise exceptions.AuthenticationFailed('Invalid token payload')
        
        return License.objects.get(tenant_id=tenant_id)
    
    def validate_license(self, license):
        """
        Validate that the license is active and within validity period.
        """
        now = timezone.now()
        
        # Check if license is active
        if license.status != 'ACTIVE':
            raise exceptions.AuthenticationFailed(f'License is {license.status.lower()}')
        
        # Check validity period
        if now < license.valid_from:
            raise exceptions.AuthenticationFailed('License not yet valid')
        
        if now > license.valid_to:
            raise exceptions.AuthenticationFailed('License has expired')
    
    def update_token_usage(self, token, license):
        """
        Update the last used timestamp for the token.
        """
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
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return 'Bearer'
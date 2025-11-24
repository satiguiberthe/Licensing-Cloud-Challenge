from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from licenses.models import License, LicenseToken, LicenseHistory, LicenseUpgrade
from licenses.serializers import (
    LicenseSerializer, LicenseCreateSerializer, LicenseUpdateSerializer,
    LicenseTokenSerializer, LicenseHistorySerializer, LicenseUpgradeSerializer,
    TokenGenerateSerializer, QuotaStatusSerializer
)
from utility.quotas import quota_service
from utility.hybrid_auth import HybridJWTAuthentication
import logging

logger = logging.getLogger(__name__)


class LicenseListCreateAPIView(APIView):
    """
    List all licenses or create a new one.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all licenses with filtering."""
        licenses = License.objects.all()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            licenses = licenses.filter(status=status_filter)
        
        # Filter by tenant_id
        tenant_filter = request.query_params.get('tenant_id')
        if tenant_filter:
            licenses = licenses.filter(tenant_id__icontains=tenant_filter)
        
        # Filter by validity
        valid_only = request.query_params.get('valid_only')
        if valid_only == 'true':
            now = timezone.now()
            licenses = licenses.filter(
                status='ACTIVE',
                valid_from__lte=now,
                valid_to__gte=now
            )
        
        serializer = LicenseSerializer(licenses, many=True)
        return Response(serializer.data)
    
    @transaction.atomic
    def post(self, request):
        """Create a new license."""
        serializer = LicenseCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            license = serializer.save()
            
            # Initialize app count in cache
            quota_service.update_app_count(license.tenant_id, 0)
            
            # Log the creation
            LicenseHistory.objects.create(
                license=license,
                action='CREATE',
                details={'initial_data': request.data},
                performed_by=request.META.get('REMOTE_ADDR', 'system')
            )
            
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LicenseDetailAPIView(APIView):
    """
    Retrieve, update or delete a license.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        return get_object_or_404(License, pk=pk)
    
    def get(self, request, pk):
        """Get license details."""
        license = self.get_object(pk)
        serializer = LicenseSerializer(license)
        return Response(serializer.data)
    
    @transaction.atomic
    def put(self, request, pk):
        """Update a license."""
        license = self.get_object(pk)
        serializer = LicenseUpdateSerializer(
            license,
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def delete(self, request, pk):
        """Revoke a license."""
        license = self.get_object(pk)
        license.revoke()
        
        # Log the revocation
        LicenseHistory.objects.create(
            license=license,
            action='REVOKE',
            details={'reason': request.data.get('reason', 'No reason provided')},
            performed_by=request.META.get('REMOTE_ADDR', 'system')
        )
        
        # Clear cached data
        quota_service.reset_tenant_data(license.tenant_id)
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class LicenseSuspendAPIView(APIView):
    """
    Suspend or reactivate a license.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request, pk):
        """Suspend a license."""
        license = get_object_or_404(License, pk=pk)
        license.suspend()
        
        # Log the suspension
        LicenseHistory.objects.create(
            license=license,
            action='SUSPEND',
            details={'reason': request.data.get('reason', 'No reason provided')},
            performed_by=request.META.get('REMOTE_ADDR', 'system')
        )
        
        serializer = LicenseSerializer(license)
        return Response(serializer.data)
    
    @transaction.atomic
    def delete(self, request, pk):
        """Reactivate a license."""
        license = get_object_or_404(License, pk=pk)
        
        if license.reactivate():
            # Log the reactivation
            LicenseHistory.objects.create(
                license=license,
                action='REACTIVATE',
                details={'reason': request.data.get('reason', 'No reason provided')},
                performed_by=request.META.get('REMOTE_ADDR', 'system')
            )
            
            serializer = LicenseSerializer(license)
            return Response(serializer.data)
        
        return Response(
            {'error': 'Cannot reactivate expired license'},
            status=status.HTTP_400_BAD_REQUEST
        )


class LicenseUpgradeAPIView(APIView):
    """
    Upgrade or downgrade a license.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request, pk):
        """Upgrade/downgrade a license."""
        license = get_object_or_404(License, pk=pk)
        
        # Store previous values
        previous_max_apps = license.max_apps
        previous_max_executions = license.max_executions_per_24h
        previous_valid_to = license.valid_to
        
        # Update license
        new_max_apps = request.data.get('max_apps', license.max_apps)
        new_max_executions = request.data.get('max_executions_per_24h', license.max_executions_per_24h)
        new_valid_to = request.data.get('valid_to', license.valid_to)
        
        license.max_apps = new_max_apps
        license.max_executions_per_24h = new_max_executions
        if isinstance(new_valid_to, str):
            from dateutil import parser
            new_valid_to = parser.parse(new_valid_to)
        license.valid_to = new_valid_to
        license.save()
        
        # Create upgrade record
        upgrade = LicenseUpgrade.objects.create(
            license=license,
            previous_max_apps=previous_max_apps,
            previous_max_executions=previous_max_executions,
            previous_valid_to=previous_valid_to,
            new_max_apps=new_max_apps,
            new_max_executions=new_max_executions,
            new_valid_to=new_valid_to,
            reason=request.data.get('reason', ''),
            approved_by=request.META.get('REMOTE_ADDR', 'system')
        )
        
        # Log the upgrade
        LicenseHistory.objects.create(
            license=license,
            action='UPGRADE',
            details={
                'upgrade_id': str(upgrade.id),
                'changes': {
                    'max_apps': f'{previous_max_apps} -> {new_max_apps}',
                    'max_executions': f'{previous_max_executions} -> {new_max_executions}',
                    'valid_to': f'{previous_valid_to} -> {new_valid_to}'
                }
            },
            performed_by=request.META.get('REMOTE_ADDR', 'system')
        )
        
        serializer = LicenseSerializer(license)
        return Response(serializer.data)


class LicenseHistoryAPIView(APIView):
    """
    Get license history.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get history for a specific license."""
        license = get_object_or_404(License, pk=pk)
        history = license.history.all()
        serializer = LicenseHistorySerializer(history, many=True)
        return Response(serializer.data)


class TokenGenerateAPIView(APIView):
    """
    Generate a new token for a license.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Generate a new JWT token."""
        serializer = TokenGenerateSerializer(data=request.data)
        
        if serializer.is_valid():
            tenant_id = serializer.validated_data['tenant_id']
            expires_in_hours = serializer.validated_data['expires_in_hours']
            
            license = License.objects.get(tenant_id=tenant_id)
            
            # Check if license is valid
            if not license.is_valid():
                return Response(
                    {'error': 'License is not valid'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate token
            from datetime import timedelta
            import jwt
            from django.conf import settings
            
            expires_at = timezone.now() + timedelta(hours=expires_in_hours)
            
            payload = {
                'tenant_id': license.tenant_id,
                'tenant_name': license.tenant_name,
                'license_id': str(license.id),
                'max_apps': license.max_apps,
                'max_executions_per_24h': license.max_executions_per_24h,
                'valid_from': license.valid_from.isoformat(),
                'valid_to': license.valid_to.isoformat(),
                'status': license.status,
                'iat': timezone.now(),
                'exp': expires_at
            }
            
            token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
            
            # Store token
            token_obj = LicenseToken.objects.create(
                license=license,
                token=token,
                expires_at=expires_at
            )
            
            return Response({
                'token': token,
                'expires_at': expires_at,
                'tenant_id': tenant_id
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuotaStatusAPIView(APIView):
    """
    Get quota status for a license.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current quota status."""
        from licenses.models import License
        from user.models import UserProfileModel
        
        # Get license from request.user (can be User or License)
        if isinstance(request.user, License):
            license = request.user
        elif isinstance(request.user, UserProfileModel):
            # Get or create default license for user
            tenant_id = f"user_{request.user.username}"
            try:
                license = License.objects.get(tenant_id=tenant_id)
            except License.DoesNotExist:
                return Response(
                    {'error': 'No license found for user'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {'error': 'Invalid authentication'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        status_data = quota_service.get_quota_status(
            license.tenant_id,
            license.max_executions_per_24h,
            license.max_apps
        )
        
        serializer = QuotaStatusSerializer(data=status_data)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.data)
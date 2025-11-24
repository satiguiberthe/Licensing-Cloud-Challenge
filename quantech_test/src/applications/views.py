from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum, Avg
from applications.models import Application, ApplicationMetrics
from applications.serializers import (
    ApplicationSerializer, ApplicationCreateSerializer,
    ApplicationUpdateSerializer, ApplicationMetricsSerializer,
    ApplicationRegisterSerializer
)
from utility.quotas import quota_service
from utility.hybrid_auth import HybridJWTAuthentication
from licenses.models import License, LicenseStatus
from user.models import UserProfileModel
import logging

logger = logging.getLogger(__name__)


def get_license_from_request(request):
    """
    Get license from request.user.
    If request.user is a User, get or create a default license.
    If request.user is a License, return it directly.
    """
    user_or_license = request.user
    
    # If it's already a License, return it
    if isinstance(user_or_license, License):
        return user_or_license
    
    # If it's a User, get or create a default license
    if isinstance(user_or_license, UserProfileModel):
        # Try to get existing license for this user
        # Use username as tenant_id for simplicity
        tenant_id = f"user_{user_or_license.username}"
        
        try:
            license = License.objects.get(tenant_id=tenant_id)
        except License.DoesNotExist:
            # Create a default license for the user
            from django.utils import timezone
            from datetime import timedelta
            
            license = License.objects.create(
                tenant_id=tenant_id,
                tenant_name=user_or_license.username,
                max_apps=10,  # Default limit
                max_executions_per_24h=1000,  # Default limit
                valid_from=timezone.now(),
                valid_to=timezone.now() + timedelta(days=365),  # 1 year default
                status=LicenseStatus.ACTIVE,
                created_by=user_or_license.username,
                contact_email=user_or_license.email or '',
                contact_name=user_or_license.get_full_name() or user_or_license.username
            )
            logger.info(f"Created default license for user {user_or_license.username}")
        
        return license
    
    # Fallback: raise error
    raise ValueError(f"Unexpected user type: {type(user_or_license)}")


class ApplicationRegisterAPIView(APIView):
    """
    Public endpoint to register a new application.
    Requires JWT authentication.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        """Register a new application for the authenticated tenant."""
        license = get_license_from_request(request)  # The license is set as user by our auth backend

        # Validate input first
        serializer = ApplicationRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Check for duplicate name
        if Application.objects.filter(
            license=license,
            name=serializer.validated_data['name']
        ).exists():
            return Response(
                {'error': 'Application with this name already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Atomically check and increment app count (prevents race conditions)
        success, current_count, error_msg = quota_service.check_and_increment_app_count_atomic(
            license.tenant_id,
            license.max_apps
        )

        if not success:
            return Response(
                {
                    'error': 'Maximum number of applications reached',
                    'max_apps': license.max_apps,
                    'current_count': current_count,
                    'message': error_msg or f'You have reached the maximum of {license.max_apps} applications'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Create the application
            create_serializer = ApplicationCreateSerializer(
                data=serializer.validated_data,
                context={'license': license}
            )
            create_serializer.is_valid(raise_exception=True)
            application = create_serializer.save()

            logger.info(f"Application {application.id} registered for tenant {license.tenant_id}. Apps: {current_count}/{license.max_apps}")

            # Return the created application
            response_serializer = ApplicationSerializer(application)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            # Rollback the counter increment if application creation fails
            quota_service.decrement_app_count(license.tenant_id)
            logger.error(f"Error creating application, rolled back counter: {e}")
            raise


class ApplicationListAPIView(APIView):
    """
    List applications for authenticated tenant.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all applications for the authenticated tenant."""
        license = get_license_from_request(request)
        applications = Application.objects.filter(license=license)
        
        # Filter by active status
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            applications = applications.filter(is_active=is_active.lower() == 'true')
        
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class ApplicationDetailAPIView(APIView):
    """
    Manage a specific application.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, license):
        return get_object_or_404(Application, pk=pk, license=license)
    
    def get(self, request, pk):
        """Get application details."""
        application = self.get_object(pk, request.user)
        serializer = ApplicationSerializer(application)
        return Response(serializer.data)
    
    @transaction.atomic
    def put(self, request, pk):
        """Update an application."""
        application = self.get_object(pk, request.user)
        serializer = ApplicationUpdateSerializer(
            application,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def delete(self, request, pk):
        """Deactivate an application."""
        application = self.get_object(pk, request.user)
        
        if application.is_active:
            application.deactivate()
            # Update cache
            quota_service.decrement_app_count(request.user.tenant_id)
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationMetricsAPIView(APIView):
    """
    Get metrics for applications.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk=None):
        """Get metrics for a specific application or all applications."""
        license = get_license_from_request(request)
        
        if pk:
            # Metrics for specific application
            application = get_object_or_404(Application, pk=pk, license=license)
            metrics = ApplicationMetrics.objects.filter(application=application)
            
            # Filter by date range
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if start_date:
                metrics = metrics.filter(date__gte=start_date)
            if end_date:
                metrics = metrics.filter(date__lte=end_date)
            
            serializer = ApplicationMetricsSerializer(metrics, many=True)
            return Response(serializer.data)
        
        else:
            # Aggregate metrics for all applications
            applications = Application.objects.filter(license=license)
            
            metrics = ApplicationMetrics.objects.filter(
                application__in=applications
            ).aggregate(
                total_jobs=Sum('total_jobs'),
                successful_jobs=Sum('successful_jobs'),
                failed_jobs=Sum('failed_jobs'),
                avg_execution_time=Avg('avg_execution_time')
            )
            
            # Add counts
            metrics['total_applications'] = applications.count()
            metrics['active_applications'] = applications.filter(is_active=True).count()
            metrics['inactive_applications'] = applications.filter(is_active=False).count()
            
            # Calculate success rate
            if metrics['total_jobs']:
                metrics['avg_success_rate'] = (
                    metrics['successful_jobs'] / metrics['total_jobs'] * 100
                )
            else:
                metrics['avg_success_rate'] = 0
            
            return Response(metrics)


class ApplicationActivateAPIView(APIView):
    """
    Activate or deactivate an application.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request, pk):
        """Activate an application."""
        license = get_license_from_request(request)
        application = get_object_or_404(Application, pk=pk, license=license)
        
        if not application.is_active:
            # Check if we can activate another app
            current_count = license.applications.filter(is_active=True).count()
            if current_count >= license.max_apps:
                return Response(
                    {
                        'error': 'Maximum number of active applications reached',
                        'max_apps': license.max_apps,
                        'current_count': current_count
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            application.activate()
            quota_service.increment_app_count(license.tenant_id)
        
        serializer = ApplicationSerializer(application)
        return Response(serializer.data)
    
    @transaction.atomic
    def delete(self, request, pk):
        """Deactivate an application."""
        license = get_license_from_request(request)
        application = get_object_or_404(Application, pk=pk, license=license)
        
        if application.is_active:
            application.deactivate()
            quota_service.decrement_app_count(license.tenant_id)
        
        serializer = ApplicationSerializer(application)
        return Response(serializer.data)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
import uuid
from jobs.models import Job, JobExecution, JobStatus
from jobs.serializers import (
    JobSerializer, JobStartSerializer, JobFinishSerializer,
    JobStatisticsSerializer, ExecutionWindowSerializer
)
from applications.models import ApplicationMetrics
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


class JobStartAPIView(APIView):
    """
    Start a new job execution.
    Requires JWT authentication.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        """Start a new job for the authenticated tenant."""
        license = get_license_from_request(request)

        # Validate input
        serializer = JobStartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get the application
        application = serializer.context['application']

        # Verify application belongs to this license
        if application.license != license:
            return Response(
                {'error': 'Application does not belong to this license'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if application is active
        if not application.is_active:
            return Response(
                {'error': 'Application is not active'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create a temporary job ID for atomic check
        temp_job_id = str(uuid.uuid4())

        # Atomically check quota and record execution (prevents race conditions)
        success, current_count, error_msg = quota_service.check_and_record_execution_atomic(
            license.tenant_id,
            temp_job_id,
            license.max_executions_per_24h
        )

        if not success:
            return Response(
                {
                    'error': 'Execution quota exceeded',
                    'max_executions_per_24h': license.max_executions_per_24h,
                    'current_count': current_count,
                    'message': error_msg or f'You have reached the maximum of {license.max_executions_per_24h} executions in the last 24 hours'
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Create the job with the same ID used in quota check
        job = Job.objects.create(
            id=temp_job_id,
            application=application,
            license=license,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            metadata=serializer.validated_data.get('metadata', {}),
            status=JobStatus.RUNNING
        )

        # Create execution record
        JobExecution.objects.create(
            license=license,
            job=job,
            tenant_id=license.tenant_id
        )

        # Update application last activity
        application.last_activity = timezone.now()
        application.save(update_fields=['last_activity'])

        logger.info(f"Job {job.id} started for tenant {license.tenant_id}. Executions: {current_count}/{license.max_executions_per_24h}")

        # Return the created job
        job_serializer = JobSerializer(job)
        return Response(
            job_serializer.data,
            status=status.HTTP_201_CREATED
        )


class JobFinishAPIView(APIView):
    """
    Finish a running job.
    Requires JWT authentication.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        """Finish a running job."""
        license = get_license_from_request(request)
        
        # Validate input
        serializer = JobFinishSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the job
        job = serializer.context['job']
        
        # Verify job belongs to this license
        if job.license != license:
            return Response(
                {'error': 'Job does not belong to this license'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update job status and details
        job.status = serializer.validated_data['status']
        job.finished_at = timezone.now()
        job.result = serializer.validated_data.get('result', {})
        job.error_message = serializer.validated_data.get('error_message', '')
        
        # Set performance metrics if provided
        if 'cpu_usage' in serializer.validated_data:
            job.cpu_usage = serializer.validated_data['cpu_usage']
        if 'memory_usage' in serializer.validated_data:
            job.memory_usage = serializer.validated_data['memory_usage']
        
        # Calculate execution time
        job.calculate_execution_time()
        job.save()
        
        # Update application metrics
        self._update_application_metrics(job)
        
        # Return the updated job
        job_serializer = JobSerializer(job)
        return Response(job_serializer.data)
    
    def _update_application_metrics(self, job):
        """Update application metrics based on job completion."""
        from django.db.models import F

        today = timezone.now().date()
        metrics, _ = ApplicationMetrics.objects.get_or_create(
            application=job.application,
            date=today,
            defaults={
                'total_jobs': 0,
                'successful_jobs': 0,
                'failed_jobs': 0,
                'avg_execution_time': 0,
                'max_execution_time': 0,
                'min_execution_time': 0
            }
        )
        
        # Update counts
        metrics.total_jobs = F('total_jobs') + 1
        if job.status == JobStatus.COMPLETED:
            metrics.successful_jobs = F('successful_jobs') + 1
        elif job.status == JobStatus.FAILED:
            metrics.failed_jobs = F('failed_jobs') + 1
        
        # Update execution times
        if job.execution_time:
            if metrics.max_execution_time < job.execution_time:
                metrics.max_execution_time = job.execution_time
            if metrics.min_execution_time == 0 or metrics.min_execution_time > job.execution_time:
                metrics.min_execution_time = job.execution_time
            
            # Recalculate average
            total_time = metrics.avg_execution_time * (metrics.total_jobs - 1) + job.execution_time
            metrics.avg_execution_time = total_time / metrics.total_jobs
        
        metrics.save()


class JobListAPIView(APIView):
    """
    List jobs for authenticated tenant.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all jobs for the authenticated tenant."""
        license = get_license_from_request(request)
        jobs = Job.objects.filter(license=license)
        
        # Filter by application
        app_id = request.query_params.get('application_id')
        if app_id:
            jobs = jobs.filter(application_id=app_id)
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            jobs = jobs.filter(status=status_filter)
        
        # Filter by date range
        start_date = request.query_params.get('start_date')
        if start_date:
            jobs = jobs.filter(started_at__gte=start_date)
        
        end_date = request.query_params.get('end_date')
        if end_date:
            jobs = jobs.filter(started_at__lte=end_date)
        
        # Order by started_at descending by default
        jobs = jobs.order_by('-started_at')
        
        # Limit results
        limit = request.query_params.get('limit', 100)
        try:
            limit = min(int(limit), 1000)  # Max 1000 results
        except ValueError:
            limit = 100
        
        jobs = jobs[:limit]
        
        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data)


class JobDetailAPIView(APIView):
    """
    Get details of a specific job.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get job details."""
        license = get_license_from_request(request)
        job = get_object_or_404(Job, pk=pk, license=license)
        serializer = JobSerializer(job)
        return Response(serializer.data)


class JobStatisticsAPIView(APIView):
    """
    Get job statistics for the tenant.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get job statistics."""
        license = get_license_from_request(request)
        jobs = Job.objects.filter(license=license)
        
        # Calculate statistics
        total_jobs = jobs.count()
        
        status_counts = jobs.values('status').annotate(count=Count('status'))
        status_dict = {item['status']: item['count'] for item in status_counts}
        
        running_jobs = status_dict.get(JobStatus.RUNNING, 0)
        completed_jobs = status_dict.get(JobStatus.COMPLETED, 0)
        failed_jobs = status_dict.get(JobStatus.FAILED, 0)
        cancelled_jobs = status_dict.get(JobStatus.CANCELLED, 0)
        
        # Calculate average execution time
        avg_execution = jobs.filter(
            execution_time__isnull=False
        ).aggregate(avg=Avg('execution_time'))
        avg_execution_time = avg_execution['avg'] or 0
        
        # Calculate success rate
        finished_jobs = completed_jobs + failed_jobs
        success_rate = (completed_jobs / finished_jobs * 100) if finished_jobs > 0 else 0
        
        # Calculate time-based statistics
        now = timezone.now()
        jobs_last_hour = jobs.filter(started_at__gte=now - timedelta(hours=1)).count()
        jobs_last_24h = jobs.filter(started_at__gte=now - timedelta(hours=24)).count()
        jobs_last_7d = jobs.filter(started_at__gte=now - timedelta(days=7)).count()
        
        statistics = {
            'total_jobs': total_jobs,
            'running_jobs': running_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'cancelled_jobs': cancelled_jobs,
            'avg_execution_time': avg_execution_time,
            'success_rate': success_rate,
            'jobs_last_hour': jobs_last_hour,
            'jobs_last_24h': jobs_last_24h,
            'jobs_last_7d': jobs_last_7d
        }
        
        serializer = JobStatisticsSerializer(data=statistics)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.data)


class ExecutionWindowAPIView(APIView):
    """
    Get execution window information.
    """
    authentication_classes = [HybridJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get execution window details for the tenant."""
        license = get_license_from_request(request)
        window_hours = int(request.query_params.get('hours', 24))
        
        # Get execution history from quota service
        executions = quota_service.get_execution_history(
            license.tenant_id,
            window_hours
        )
        
        # Calculate summary
        total_count = len(executions)
        oldest = executions[0]['datetime'] if executions else None
        newest = executions[-1]['datetime'] if executions else None
        
        data = {
            'tenant_id': license.tenant_id,
            'window_hours': window_hours,
            'executions': executions,
            'total_count': total_count,
            'oldest_execution': oldest,
            'newest_execution': newest
        }
        
        serializer = ExecutionWindowSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.data)
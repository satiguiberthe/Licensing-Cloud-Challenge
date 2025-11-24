from rest_framework import serializers
from jobs.models import Job, JobExecution, JobQueue, JobStatus
from applications.models import Application
from django.utils import timezone


class JobSerializer(serializers.ModelSerializer):
    """Serializer for Job model."""
    
    application_name = serializers.CharField(source='application.name', read_only=True)
    license_tenant = serializers.CharField(source='license.tenant_id', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'application', 'application_name', 'license', 'license_tenant',
            'name', 'description', 'status', 'started_at', 'finished_at',
            'execution_time', 'duration', 'error_message', 'result',
            'cpu_usage', 'memory_usage', 'metadata'
        ]
        read_only_fields = [
            'id', 'started_at', 'finished_at', 'execution_time'
        ]
    
    def get_duration(self, obj):
        """Get human-readable duration."""
        if obj.execution_time:
            return f"{obj.execution_time:.2f} seconds"
        elif obj.started_at and obj.finished_at:
            delta = obj.finished_at - obj.started_at
            return f"{delta.total_seconds():.2f} seconds"
        return None


class JobStartSerializer(serializers.Serializer):
    """Serializer for starting a new job."""
    
    application_id = serializers.UUIDField(required=True)
    name = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate_application_id(self, value):
        """Validate that the application exists and is active."""
        try:
            app = Application.objects.get(id=value)
            if not app.is_active:
                raise serializers.ValidationError("Application is not active.")
            self.context['application'] = app
        except Application.DoesNotExist:
            raise serializers.ValidationError("Application not found.")
        return value


class JobFinishSerializer(serializers.Serializer):
    """Serializer for finishing a job."""
    
    job_id = serializers.UUIDField(required=True)
    status = serializers.ChoiceField(
        choices=[JobStatus.COMPLETED, JobStatus.FAILED],
        default=JobStatus.COMPLETED
    )
    result = serializers.JSONField(required=False, default=dict)
    error_message = serializers.CharField(required=False, allow_blank=True)
    cpu_usage = serializers.FloatField(required=False, min_value=0, max_value=100)
    memory_usage = serializers.FloatField(required=False, min_value=0)
    
    def validate_job_id(self, value):
        """Validate that the job exists and is running."""
        try:
            job = Job.objects.get(id=value)
            if job.status != JobStatus.RUNNING:
                raise serializers.ValidationError(f"Job is not running. Current status: {job.status}")
            self.context['job'] = job
        except Job.DoesNotExist:
            raise serializers.ValidationError("Job not found.")
        return value


class JobExecutionSerializer(serializers.ModelSerializer):
    """Serializer for JobExecution model."""
    
    job_name = serializers.CharField(source='job.name', read_only=True)
    
    class Meta:
        model = JobExecution
        fields = ['id', 'license', 'job', 'job_name', 'executed_at', 'tenant_id']
        read_only_fields = ['id', 'executed_at']


class JobQueueSerializer(serializers.ModelSerializer):
    """Serializer for JobQueue model."""
    
    job_info = JobSerializer(source='job', read_only=True)
    
    class Meta:
        model = JobQueue
        fields = [
            'id', 'job', 'job_info', 'priority', 'scheduled_at',
            'is_processing', 'attempts', 'max_attempts',
            'created_at', 'last_attempt_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_attempt_at']


class JobStatisticsSerializer(serializers.Serializer):
    """Serializer for job statistics."""
    
    total_jobs = serializers.IntegerField()
    running_jobs = serializers.IntegerField()
    completed_jobs = serializers.IntegerField()
    failed_jobs = serializers.IntegerField()
    cancelled_jobs = serializers.IntegerField()
    avg_execution_time = serializers.FloatField()
    success_rate = serializers.FloatField()
    
    jobs_last_hour = serializers.IntegerField()
    jobs_last_24h = serializers.IntegerField()
    jobs_last_7d = serializers.IntegerField()


class ExecutionWindowSerializer(serializers.Serializer):
    """Serializer for execution window information."""
    
    tenant_id = serializers.CharField()
    window_hours = serializers.IntegerField()
    executions = serializers.ListField(
        child=serializers.DictField()
    )
    total_count = serializers.IntegerField()
    oldest_execution = serializers.DateTimeField(allow_null=True)
    newest_execution = serializers.DateTimeField(allow_null=True)
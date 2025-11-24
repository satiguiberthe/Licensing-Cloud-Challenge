from django.db import models
from applications.models import Application
from licenses.models import License
import uuid


class JobStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Job(models.Model):
    """
    Job execution tracking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='jobs')
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='jobs')
    
    # Job details
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.PENDING
    )
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    # Execution details
    execution_time = models.FloatField(null=True, blank=True)  # in seconds
    error_message = models.TextField(blank=True)
    result = models.JSONField(default=dict, blank=True)
    
    # Resource tracking
    cpu_usage = models.FloatField(null=True, blank=True)  # percentage
    memory_usage = models.FloatField(null=True, blank=True)  # in MB
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'jobs'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['application', 'status']),
            models.Index(fields=['license', 'started_at']),
            models.Index(fields=['started_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.status}"
    
    def is_running(self):
        """Check if job is currently running."""
        return self.status == JobStatus.RUNNING
    
    def is_finished(self):
        """Check if job has finished (completed or failed)."""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
    
    def calculate_execution_time(self):
        """Calculate execution time if job is finished."""
        if self.finished_at and self.started_at:
            delta = self.finished_at - self.started_at
            self.execution_time = delta.total_seconds()
            self.save()
            return self.execution_time
        return None


class JobExecution(models.Model):
    """
    Track job executions for rate limiting (24h sliding window).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='executions')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='execution_record')
    
    # Execution timestamp
    executed_at = models.DateTimeField(auto_now_add=True)
    
    # Quick reference fields for optimization
    tenant_id = models.CharField(max_length=255, db_index=True)
    
    class Meta:
        db_table = 'job_executions'
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['license', 'executed_at']),
            models.Index(fields=['tenant_id', 'executed_at']),
            models.Index(fields=['executed_at']),
        ]
    
    def __str__(self):
        return f"Execution for {self.tenant_id} at {self.executed_at}"


class JobQueue(models.Model):
    """
    Queue for managing job scheduling.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='queue_entry')
    
    # Priority and scheduling
    priority = models.IntegerField(default=0)  # Higher number = higher priority
    scheduled_at = models.DateTimeField(null=True, blank=True)
    
    # Queue status
    is_processing = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'job_queue'
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['is_processing', 'priority']),
            models.Index(fields=['scheduled_at']),
        ]
    
    def __str__(self):
        return f"Queue entry for {self.job.name}"
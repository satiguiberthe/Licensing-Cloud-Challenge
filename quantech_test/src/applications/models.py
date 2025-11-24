from django.db import models
from licenses.models import License
import uuid


class Application(models.Model):
    """
    Application registered by a tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='applications')
    
    # Application details
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, default='1.0.0')
    
    # Technical details
    api_key = models.CharField(max_length=255, unique=True)
    webhook_url = models.URLField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    # Additional configuration
    config = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'applications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['license', 'is_active']),
            models.Index(fields=['api_key']),
        ]
        unique_together = [['license', 'name']]
    
    def __str__(self):
        return f"{self.name} ({self.license.tenant_id})"
    
    def deactivate(self):
        """Deactivate the application."""
        self.is_active = False
        self.save()
    
    def activate(self):
        """Activate the application."""
        self.is_active = True
        self.save()


class ApplicationMetrics(models.Model):
    """
    Track application usage metrics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='metrics')
    
    # Metrics
    total_jobs = models.IntegerField(default=0)
    successful_jobs = models.IntegerField(default=0)
    failed_jobs = models.IntegerField(default=0)
    
    # Time-based metrics
    date = models.DateField()
    hour = models.IntegerField(null=True, blank=True)  # For hourly metrics
    
    # Performance metrics
    avg_execution_time = models.FloatField(default=0)  # in seconds
    max_execution_time = models.FloatField(default=0)  # in seconds
    min_execution_time = models.FloatField(default=0)  # in seconds
    
    class Meta:
        db_table = 'application_metrics'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['application', 'date']),
        ]
        unique_together = [['application', 'date', 'hour']]
    
    def __str__(self):
        return f"Metrics for {self.application.name} on {self.date}"
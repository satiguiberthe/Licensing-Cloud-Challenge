from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
import uuid
import json


class LicenseStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    EXPIRED = 'EXPIRED', 'Expired'
    REVOKED = 'REVOKED', 'Revoked'


class License(models.Model):
    """
    Main license model for tenant licensing management.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=255, unique=True, db_index=True)
    tenant_name = models.CharField(max_length=255)
    
    # License limits
    max_apps = models.IntegerField(validators=[MinValueValidator(0)])
    max_executions_per_24h = models.IntegerField(validators=[MinValueValidator(0)])
    
    # Validity period
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=LicenseStatus.choices,
        default=LicenseStatus.ACTIVE
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True)
    
    # Additional features (JSON field for extensibility)
    features = models.JSONField(default=dict, blank=True)
    
    # Contact information
    contact_email = models.EmailField(blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'licenses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['valid_from', 'valid_to']),
        ]
    
    def __str__(self):
        return f"{self.tenant_name} ({self.tenant_id})"

    @property
    def is_authenticated(self):
        """
        Always return True for compatibility with Django REST Framework permissions.
        The actual authentication is done by the JWT backend.
        """
        return True

    def is_valid(self):
        """Check if license is currently valid."""
        now = timezone.now()
        return (
            self.status == LicenseStatus.ACTIVE and
            self.valid_from <= now <= self.valid_to
        )
    
    def is_expired(self):
        """Check if license has expired."""
        return timezone.now() > self.valid_to
    
    def get_remaining_days(self):
        """Get remaining days until expiration."""
        if self.is_expired():
            return 0
        delta = self.valid_to - timezone.now()
        return delta.days
    
    def suspend(self):
        """Suspend the license."""
        self.status = LicenseStatus.SUSPENDED
        self.save()
    
    def reactivate(self):
        """Reactivate the license if not expired."""
        if not self.is_expired():
            self.status = LicenseStatus.ACTIVE
            self.save()
            return True
        return False
    
    def revoke(self):
        """Permanently revoke the license."""
        self.status = LicenseStatus.REVOKED
        self.save()


class LicenseToken(models.Model):
    """
    JWT tokens associated with licenses for authentication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='tokens')
    token = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'license_tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['license', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Token for {self.license.tenant_id}"
    
    def is_valid(self):
        """Check if token is still valid."""
        return self.is_active and timezone.now() < self.expires_at


class LicenseHistory(models.Model):
    """
    Track license changes and audit trail.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=50)
    details = models.JSONField(default=dict)
    performed_by = models.CharField(max_length=255)
    performed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'license_history'
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['license', 'performed_at']),
        ]
    
    def __str__(self):
        return f"{self.action} on {self.license.tenant_id} at {self.performed_at}"


class LicenseUpgrade(models.Model):
    """
    Track license upgrades and downgrades.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='upgrades')
    
    # Previous values
    previous_max_apps = models.IntegerField()
    previous_max_executions = models.IntegerField()
    previous_valid_to = models.DateTimeField()
    
    # New values
    new_max_apps = models.IntegerField()
    new_max_executions = models.IntegerField()
    new_valid_to = models.DateTimeField()
    
    # Metadata
    reason = models.TextField(blank=True)
    approved_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'license_upgrades'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Upgrade for {self.license.tenant_id} on {self.created_at}"
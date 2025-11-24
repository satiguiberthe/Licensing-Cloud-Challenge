from rest_framework import serializers
from applications.models import Application, ApplicationMetrics
from licenses.models import License
import secrets
import string


class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Application model."""
    
    license_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = [
            'id', 'license', 'license_info', 'name', 'description', 'version',
            'api_key', 'webhook_url', 'is_active', 'created_at', 'updated_at',
            'last_activity', 'config'
        ]
        read_only_fields = ['id', 'api_key', 'created_at', 'updated_at', 'last_activity']
    
    def get_license_info(self, obj):
        """Get basic license information."""
        return {
            'tenant_id': obj.license.tenant_id,
            'tenant_name': obj.license.tenant_name,
            'status': obj.license.status
        }


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new application."""
    
    class Meta:
        model = Application
        fields = ['name', 'description', 'version', 'webhook_url', 'config']
    
    def create(self, validated_data):
        """Create a new application with auto-generated API key."""
        # Get license from context (set by the view)
        license = self.context.get('license')
        if not license:
            raise serializers.ValidationError("License is required to create an application.")
        
        # Generate unique API key
        api_key = self.generate_api_key()
        
        # Create application
        application = Application.objects.create(
            license=license,
            api_key=api_key,
            **validated_data
        )
        
        return application
    
    def generate_api_key(self):
        """Generate a secure API key."""
        alphabet = string.ascii_letters + string.digits
        api_key = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        # Ensure uniqueness
        while Application.objects.filter(api_key=api_key).exists():
            api_key = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        return f"app_{api_key}"


class ApplicationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an application."""
    
    class Meta:
        model = Application
        fields = ['name', 'description', 'version', 'webhook_url', 'is_active', 'config']
    
    def validate_name(self, value):
        """Ensure name is unique within the license."""
        instance = self.instance
        if instance and Application.objects.filter(
            license=instance.license,
            name=value
        ).exclude(id=instance.id).exists():
            raise serializers.ValidationError(
                "An application with this name already exists for this license."
            )
        return value


class ApplicationMetricsSerializer(serializers.ModelSerializer):
    """Serializer for Application Metrics."""
    
    application_name = serializers.CharField(source='application.name', read_only=True)
    
    class Meta:
        model = ApplicationMetrics
        fields = [
            'id', 'application', 'application_name', 'total_jobs', 'successful_jobs',
            'failed_jobs', 'date', 'hour', 'avg_execution_time', 'max_execution_time',
            'min_execution_time'
        ]
        read_only_fields = ['id']


class ApplicationSummarySerializer(serializers.Serializer):
    """Serializer for application summary statistics."""
    
    total_applications = serializers.IntegerField()
    active_applications = serializers.IntegerField()
    inactive_applications = serializers.IntegerField()
    total_jobs_executed = serializers.IntegerField()
    avg_success_rate = serializers.FloatField()
    
    
class ApplicationRegisterSerializer(serializers.Serializer):
    """Serializer for the public application registration endpoint."""
    
    name = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    version = serializers.CharField(max_length=50, default='1.0.0')
    webhook_url = serializers.URLField(required=False, allow_blank=True)
    config = serializers.JSONField(required=False, default=dict)
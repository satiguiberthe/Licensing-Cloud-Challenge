from rest_framework import serializers
from licenses.models import License, LicenseToken, LicenseHistory, LicenseUpgrade
from django.utils import timezone
import jwt
from django.conf import settings
from datetime import timedelta


class LicenseSerializer(serializers.ModelSerializer):
    """Serializer for License model."""
    
    remaining_days = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = License
        fields = [
            'id', 'tenant_id', 'tenant_name', 'max_apps', 'max_executions_per_24h',
            'valid_from', 'valid_to', 'status', 'features', 'contact_email',
            'contact_name', 'created_at', 'updated_at', 'remaining_days', 'is_valid'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_remaining_days(self, obj):
        """Get remaining days until expiration."""
        return obj.get_remaining_days()
    
    def get_is_valid(self, obj):
        """Check if license is currently valid."""
        return obj.is_valid()
    
    def validate_valid_to(self, value):
        """Ensure valid_to is in the future."""
        if value <= timezone.now():
            raise serializers.ValidationError("Valid to date must be in the future.")
        return value
    
    def validate(self, data):
        """Validate the license data."""
        valid_from = data.get('valid_from', getattr(self.instance, 'valid_from', None))
        valid_to = data.get('valid_to', getattr(self.instance, 'valid_to', None))
        
        if valid_from and valid_to and valid_from >= valid_to:
            raise serializers.ValidationError("Valid from date must be before valid to date.")
        
        return data


class LicenseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new license."""
    
    generate_token = serializers.BooleanField(default=True, write_only=True)
    token = serializers.CharField(read_only=True)
    
    class Meta:
        model = License
        fields = [
            'tenant_id', 'tenant_name', 'max_apps', 'max_executions_per_24h',
            'valid_from', 'valid_to', 'status', 'features', 'contact_email',
            'contact_name', 'created_by', 'generate_token', 'token'
        ]
    
    def create(self, validated_data):
        """Create a new license and optionally generate a token."""
        generate_token = validated_data.pop('generate_token', True)
        license = License.objects.create(**validated_data)
        
        if generate_token:
            token = self.generate_jwt_token(license)
            self.context['token'] = token
            
            # Store token in database
            LicenseToken.objects.create(
                license=license,
                token=token,
                expires_at=timezone.now() + timedelta(seconds=settings.JWT_ACCESS_TOKEN_LIFETIME)
            )
        
        return license
    
    def generate_jwt_token(self, license):
        """Generate a JWT token for the license."""
        from datetime import timedelta

        now = timezone.now()
        payload = {
            'tenant_id': license.tenant_id,
            'tenant_name': license.tenant_name,
            'license_id': str(license.id),
            'max_apps': license.max_apps,
            'max_executions_per_24h': license.max_executions_per_24h,
            'valid_from': license.valid_from.isoformat(),
            'valid_to': license.valid_to.isoformat(),
            'status': license.status,
            'iat': now,
            'exp': now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_LIFETIME)
        }

        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    def to_representation(self, instance):
        """Add token to the response if generated."""
        data = super().to_representation(instance)
        if 'token' in self.context:
            data['token'] = self.context['token']
        return data


class LicenseUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a license."""
    
    class Meta:
        model = License
        fields = [
            'tenant_name', 'max_apps', 'max_executions_per_24h',
            'valid_to', 'status', 'features', 'contact_email', 'contact_name'
        ]
    
    def update(self, instance, validated_data):
        """Update license and track changes in history."""
        # Track changes
        changes = {}
        for field, value in validated_data.items():
            old_value = getattr(instance, field)
            if old_value != value:
                changes[field] = {
                    'old': str(old_value),
                    'new': str(value)
                }
        
        # Update instance
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        
        # Create history record
        if changes:
            LicenseHistory.objects.create(
                license=instance,
                action='UPDATE',
                details=changes,
                performed_by=self.context['request'].META.get('REMOTE_ADDR', 'system')
            )
        
        return instance


class LicenseTokenSerializer(serializers.ModelSerializer):
    """Serializer for License Token."""
    
    license_info = LicenseSerializer(source='license', read_only=True)
    
    class Meta:
        model = LicenseToken
        fields = ['id', 'license', 'license_info', 'token', 'is_active', 
                 'created_at', 'expires_at', 'last_used_at']
        read_only_fields = ['id', 'token', 'created_at']


class LicenseHistorySerializer(serializers.ModelSerializer):
    """Serializer for License History."""
    
    class Meta:
        model = LicenseHistory
        fields = ['id', 'license', 'action', 'details', 'performed_by', 'performed_at']
        read_only_fields = ['id', 'performed_at']


class LicenseUpgradeSerializer(serializers.ModelSerializer):
    """Serializer for License Upgrade."""
    
    class Meta:
        model = LicenseUpgrade
        fields = [
            'id', 'license', 'previous_max_apps', 'previous_max_executions',
            'previous_valid_to', 'new_max_apps', 'new_max_executions',
            'new_valid_to', 'reason', 'approved_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TokenGenerateSerializer(serializers.Serializer):
    """Serializer for generating a new token."""
    
    tenant_id = serializers.CharField(required=True)
    expires_in_hours = serializers.IntegerField(default=24, min_value=1, max_value=8760)  # Max 1 year
    
    def validate_tenant_id(self, value):
        """Check if the tenant exists."""
        try:
            License.objects.get(tenant_id=value)
        except License.DoesNotExist:
            raise serializers.ValidationError("License with this tenant ID does not exist.")
        return value


class QuotaStatusSerializer(serializers.Serializer):
    """Serializer for quota status response."""
    
    tenant_id = serializers.CharField()
    executions = serializers.DictField()
    applications = serializers.DictField()
    timestamp = serializers.DateTimeField()
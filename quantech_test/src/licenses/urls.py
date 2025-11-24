from django.urls import path
from licenses.views import (
    LicenseListCreateAPIView,
    LicenseDetailAPIView,
    LicenseSuspendAPIView,
    LicenseUpgradeAPIView,
    LicenseHistoryAPIView,
    TokenGenerateAPIView,
    QuotaStatusAPIView
)

app_name = 'licenses'

urlpatterns = [
    # License management
    path('licenses/', LicenseListCreateAPIView.as_view(), name='license-list-create'),
    path('licenses/<uuid:pk>/', LicenseDetailAPIView.as_view(), name='license-detail'),
    path('licenses/<uuid:pk>/suspend/', LicenseSuspendAPIView.as_view(), name='license-suspend'),
    path('licenses/<uuid:pk>/upgrade/', LicenseUpgradeAPIView.as_view(), name='license-upgrade'),
    path('licenses/<uuid:pk>/history/', LicenseHistoryAPIView.as_view(), name='license-history'),
    
    # Token management
    path('tokens/generate/', TokenGenerateAPIView.as_view(), name='token-generate'),
    
    # Quota status
    path('quota/status/', QuotaStatusAPIView.as_view(), name='quota-status'),
]
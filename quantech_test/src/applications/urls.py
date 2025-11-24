from django.urls import path
from applications.views import (
    ApplicationListAPIView,
    ApplicationDetailAPIView,
    ApplicationMetricsAPIView,
    ApplicationActivateAPIView,
    ApplicationRegisterAPIView
)

app_name = 'applications'

urlpatterns = [
    # Public API endpoint (as per challenge requirements)
    path('apps/register', ApplicationRegisterAPIView.as_view(), name='apps-register'),

    # Application management (internal API)
    path('applications/', ApplicationListAPIView.as_view(), name='application-list'),
    path('applications/<uuid:pk>/', ApplicationDetailAPIView.as_view(), name='application-detail'),
    path('applications/<uuid:pk>/activate/', ApplicationActivateAPIView.as_view(), name='application-activate'),
    path('applications/<uuid:pk>/metrics/', ApplicationMetricsAPIView.as_view(), name='application-metrics-detail'),
    path('applications/metrics/', ApplicationMetricsAPIView.as_view(), name='application-metrics'),
]
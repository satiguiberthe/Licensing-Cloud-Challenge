from django.urls import path
from applications.views import ApplicationRegisterAPIView

app_name = 'applications_public'

urlpatterns = [
    # Public endpoint for registering applications (as required by challenge)
    path('register/', ApplicationRegisterAPIView.as_view(), name='register'),
]
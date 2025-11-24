from django.urls import path
from jobs.views import JobStartAPIView, JobFinishAPIView

app_name = 'jobs_public'

urlpatterns = [
    # Public endpoints for job management (as required by challenge)
    path('start/', JobStartAPIView.as_view(), name='start'),
    path('finish/', JobFinishAPIView.as_view(), name='finish'),
]
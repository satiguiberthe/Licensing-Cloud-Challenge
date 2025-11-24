from django.urls import path
from jobs.views import (
    JobListAPIView,
    JobDetailAPIView,
    JobStatisticsAPIView,
    ExecutionWindowAPIView,
    JobStartAPIView,
    JobFinishAPIView
)

app_name = 'jobs'

urlpatterns = [
    # Public API endpoints (as per challenge requirements)
    path('jobs/start', JobStartAPIView.as_view(), name='jobs-start'),
    path('jobs/finish', JobFinishAPIView.as_view(), name='jobs-finish'),

    # Job management (internal API)
    path('jobs/', JobListAPIView.as_view(), name='job-list'),
    path('jobs/<uuid:pk>/', JobDetailAPIView.as_view(), name='job-detail'),
    path('jobs/statistics/', JobStatisticsAPIView.as_view(), name='job-statistics'),
    path('executions/window/', ExecutionWindowAPIView.as_view(), name='execution-window'),
]
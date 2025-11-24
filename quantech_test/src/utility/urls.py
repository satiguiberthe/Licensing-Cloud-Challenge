from django.urls import path
from . import views

app_name = 'utility'

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
]

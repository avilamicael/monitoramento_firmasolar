from django.urls import path
from .views import metricas_view

urlpatterns = [
    path('', metricas_view, name='metricas'),
]

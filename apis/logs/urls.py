from apis.logs.api import LogEntryViewSet
from django.urls import path
from rest_framework.routers import DefaultRouter

routers = DefaultRouter()

# Registrar la API de logs
routers.register(r'auditlogs', LogEntryViewSet, basename='auditlog')

urlpatterns = routers.urls
app_name = "logs"
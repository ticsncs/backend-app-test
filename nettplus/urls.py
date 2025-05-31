from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.urls import re_path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Nettplus Docs API",
        default_version='v1',
        description="Test description",
        terms_of_service="https://www.nettplus.net/",
        contact=openapi.Contact(email="nettplus@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
urlpatterns = [
                  path("docs/",
                       schema_view.with_ui("swagger", cache_timeout=0),
                       name='schema-swagger-ui'),
                  path("redocs/",
                       schema_view.with_ui("redoc", cache_timeout=0),
                       name='schema-redoc'),
                  path("admin/", admin.site.urls),
                  path("api/", include("apis.urls")),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.urls import path

from apis.appsettings.views import DynamicContentAPIView

urlpatterns = [
    path('dynamic-content/', DynamicContentAPIView.as_view(),
         name='app_dynamic_content_api'),
]

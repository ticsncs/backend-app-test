from django.urls import path
from rest_framework.routers import DefaultRouter

from apis.notifications.views import CustomDeviceCreateView, \
    UserNotificationsView, NotificationDetailView, FirebaseNotificationView, LogoutView

app_name = 'notifications'

routers = DefaultRouter()

urlpatterns = [

    path('fcm-device/', CustomDeviceCreateView.as_view(),
         name='fcm_device'),
    path('<int:user_id>/', UserNotificationsView.as_view(),
         name='notifications'),
    path('mark-read/<int:user_id>/',
         NotificationDetailView.as_view(), name='detail-notifications'),
    path('logout/', LogoutView.as_view(), name='logout'),

]
routers.register(r"firebase", FirebaseNotificationView,
                 basename="masive-notification")
urlpatterns += routers.urls

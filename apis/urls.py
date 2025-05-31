"""URLs api rest"""
from django.urls import include, path

from apis.clients.api import ContractUserView, PasswordRecoveryView, \
    ChangePasswordView, ChangePasswordNettplusView

urlpatterns = [
    path("clients/", include("apis.clients.urls")),
    path("store/", include("apis.store.urls")),
    path("chat/", include("apis.chat.urls")),
    path("logs/", include("apis.logs.urls")),
    path("contracts/<str:contract_id>/users/", ContractUserView.as_view(),
         name="contract-users"),
    path("contracts/<str:contract_id>/users/<int:user_id>/",
         ContractUserView.as_view(), name="delete-user"),
    path("contracts/<str:contract_id>/users/<int:user_id>/edit/",
         ContractUserView.as_view(), name="edit-user-profile"),
    path("changepassword/", ChangePasswordView.as_view(),
         name="change-password"),
    path("changepassword/nettplus/", ChangePasswordNettplusView.as_view(), name="change-password-nettplus"),
    path("recoverypassword/", PasswordRecoveryView.as_view(),
         name="recovery-password"),
    path("appsettings/", include("apis.appsettings.urls")),
    path('notifications/', include('apis.notifications.urls')),

]

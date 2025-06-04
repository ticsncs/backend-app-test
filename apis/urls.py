"""URLs api rest"""
from django.urls import include, path

from apis.clients.api import ContractUserView, PasswordRecoveryView, \
     ChangePasswordView, ChangePasswordNettplusView,AllUsersContracts, \
     GetFatherUserByContract

urlpatterns = [
    path("clients/", include("apis.clients.urls")),
    path("store/", include("apis.store.urls")),
    path("chat/", include("apis.chat.urls")),
    path("logs/", include("apis.logs.urls")),
    path('contracts/<str:contract_id>/father/', GetFatherUserByContract.as_view(), name='get-father-user'),

    path("contracts/v2/<str:email>/", AllUsersContracts.as_view(), name="all-contracts"),
    path("contracts/<str:contract_id>/users/", ContractUserView.as_view()),
    #Crear hijo de la tienda
    path("contracts/users/", ContractUserView.as_view(),
         name="contract-users"),
     #Obtener usuarios de un contrato
     path("contracts/<str:contract_id>/users/",
           ContractUserView.as_view(), name="get-users"),
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

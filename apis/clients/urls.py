from django.urls import path
from rest_framework.routers import DefaultRouter

from apis.clients.api import (
    UserGroupViewSet,
    WifiPointViewSet,
    ServiceViewSet,
    ReferralViewSet,
    AuthenticateViewSet,
    AuthenticateViewSetToken,
    SpeedHistoryViewSet,
    TransactionViewSet,
    HotspotAccountViewSet,
    ContractViewSet,
    SliderHomeViewSet,
    SliderSecondViewSet,
    PaymentMethodViewSet,
    UserProfileViewSet,
    SupportViewSet,
    PuntosGanadosViewSet,
    RegisterTicketViewSet,
    InvoiceViewSet,
    TicketSearchViewSet,
    SlideActionAPIView,
    SupportRatingViewSet,
    TransactionRollbackAPIView,
    ContractStatusViewSet,
    DeleteAccountViewSet,
    PaymentPromiseApiView,
    AuthenticateNettplusViewSet,
    TransferPointsViewSet,
    WifiConnectionLogViewSet,
    MassPointsLoadView,
    SimpleAuthenticateView,
    GetPlanInternetForId,
    WifiAccountsByContractView

)
from apps.clients.views import blank_page

routers = DefaultRouter()
# ODOO URLS
urlpatterns = [
    path("ticket", RegisterTicketViewSet.as_view(), name="ticket"),
    path("tickets_search", TicketSearchViewSet.as_view(), name="tickets_search"),
    path("contract_status", ContractStatusViewSet.as_view(), name="contract_status"),
    path("invoice", InvoiceViewSet.as_view(), name="invoice"),
    path("slide-action/", SlideActionAPIView.as_view(), name="slide_action_api"),
    path(
        "transactions/rollback/",
        TransactionRollbackAPIView.as_view(),
        name="transaction-rollback",
    ),
    # path('changestatususer/', DeleteAccountViewSet.as_view(),
    #      name='changestatususer'),
    #
    path("payment-promise/", PaymentPromiseApiView.as_view(), name="payment-promise"),
    path("testiframe/", blank_page, name="blank_page"),
    path("masspointsload/", MassPointsLoadView.as_view(), name="mass_points_load"),
    path('contract/<str:contract_id>/wifi-accounts/',WifiAccountsByContractView.as_view({'get': 'list'}),
        name='wifi-accounts-by-contract'
    ),
]
# END ODOO URLS
routers.register(r"auth", SimpleAuthenticateView, basename="auth")
routers.register(
    r"auth/nettplus", AuthenticateNettplusViewSet, basename="auth-nettplus"
)
routers.register(r"auth/v2", AuthenticateViewSetToken, basename="auth-v2")


##Planes Internet
routers.register(r'plan-internet', GetPlanInternetForId, basename='plan-internet')


##URL DE CORREO
#routers.register(r"sentemail", SendMailRegisteredUserViewSet, basename="sent-email")
routers.register(r"wifipoints", WifiPointViewSet, basename="wifipoint")
routers.register(r"sliderhome", SliderHomeViewSet, basename="sliderhome")
routers.register(r"slidersecond", SliderSecondViewSet, basename="slidersecond")
routers.register(r"service", ServiceViewSet, basename="service")
routers.register(r"payment", PaymentMethodViewSet)
routers.register(r"transferpoints", TransferPointsViewSet, basename="transfer-points")
routers.register(r"desactivateuser", DeleteAccountViewSet, basename="desactivateuser")

routers.register(r"referrals", ReferralViewSet, basename="referral")
routers.register(r"speedhistory", SpeedHistoryViewSet, basename="speedhistory")

routers.register(r"transactions", TransactionViewSet, basename="transaction")
routers.register(r"hospot", HotspotAccountViewSet, basename="hotspotaccount")
routers.register(r"support", SupportViewSet, basename="support")
routers.register(r"puntosganados", PuntosGanadosViewSet, basename="puntos-ganados")

routers.register(r"contract", ContractViewSet, basename="contract")
routers.register(r"users", UserProfileViewSet, basename="user")
routers.register(r"support-ratings", SupportRatingViewSet, basename="support-ratings")
routers.register(
    r"wificonnectionlog", WifiConnectionLogViewSet, basename="wifi-connection-log"
)
routers.register(
    r"groups", UserGroupViewSet, basename="group"
)  # Registrar el nuevo ViewSet
urlpatterns += routers.urls
app_name = "clients"

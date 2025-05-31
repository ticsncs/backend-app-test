from os.path import basename

from django.urls import path
from rest_framework.routers import DefaultRouter

from apis.store.api import StoreViewSet, PromotionViewSet, ProductViewSet, RegisterProductView, StoreUsersByStoreView, \
    HistoricalClaimPromotionHistoryViewSet, UserClaimHistoryViewSet, HistoricalClaimProductHistoryViewSet

routers = DefaultRouter()


routers.register(r"promotions", PromotionViewSet, basename="promotion")
routers.register(r"products", ProductViewSet, basename="product")
routers.register(r"storesedit", StoreViewSet, basename="store")
routers.register(r"registerproduct", RegisterProductView,
                 basename="register-product"),
routers.register(r"userstores", StoreUsersByStoreView, basename="user-stores")
routers.register(r'userclaimhistory', UserClaimHistoryViewSet, basename='user-claim-history')
routers.register(r'historypromotionclaims', HistoricalClaimPromotionHistoryViewSet, basename='historical-promotion-claims')
routers.register(r'historyproductclaims', HistoricalClaimProductHistoryViewSet, basename='historical-product-claims')


urlpatterns = routers.urls
app_name = "store"

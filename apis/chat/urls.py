from django.urls import path
from rest_framework.routers import DefaultRouter

# from apis.chat.api import ChatbotAPIView

routers = DefaultRouter()
# routers.register(r"chat", ChatbotAPIView.as_view(), basename="chat")

# urlpatterns = routers.urls
urlpatterns = [
    # path('chatbot/', ChatbotAPIView.as_view(), name='chatbot'),
]
app_name = "chat"

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apis.appsettings.serializers import DynamicContentSerializer
from apps.appsettings.models import DynamicContent


class DynamicContentAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        key = request.query_params.get('key')
        if key:
            content = DynamicContent.objects.filter(key=key).first()
            if content:
                serializer = DynamicContentSerializer(content)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({"error": "Content not found"},
                            status=status.HTTP_404_NOT_FOUND)

        content = DynamicContent.objects.all()
        serializer = DynamicContentSerializer(content, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

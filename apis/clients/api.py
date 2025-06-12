import random
import string
from datetime import datetime
from django.db.models import Q
import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from fcm_django.models import FCMDevice
from rest_framework import status
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_200_OK
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet, ModelViewSet
from django.db import transaction as db_transaction
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from apps.clients.utils import enviar_correo_bienvenida

from apps.appsettings.models import DynamicContent
from apps.notifications.services import (
    FirebaseNotificationService,
    UserNotificationService,
)

User = get_user_model()

from apis.clients.serialize import (AuthTokenSerializer, ContractSerializer,
    ContractStatusSerializer, DeleteAccountSerializers, FatherUserSerializer,
    HotspotAccountSerializer, InvoiceSerializer, MassPointsLoadSerializer, PaymentMethodSerializer,
    PaymentPromiseSerializer, PuntosGanadosSerializer, RatingQuestionSerializer,
    ReferralSerializer, RegisterTicketSerializer, SendMailRegisteredUserSerializer,
    ServiceSerializer, SimpleContractSerializer, SlideActionSerializer, SliderSecondSerializer,
    SliderSerializer, SpeedHistorySerializer, SupportRatingRequestSerializer, SupportSerializer,
    TicketSearchSerializer, TransactionRollbackSerializer, TransactionSerializer,
    TransferPointsSerializer, UserGroupSerializer, UserProfileSerializer,
    UserProfileSerializerLite, WifiConnectionLogSerializer, WifiPointSerializer,
    WifiPointSerializerAll, SimpleUserProfileSerializer)
from apps.clients.models import (
    WifiPoint,
    Service,
    Referral,
    SpeedHistory,
    Transaction,
    HotspotAccount,
    Contract,
    UserProfile,
    SliderHome,
    SliderSecond,
    PaymentMethod,
    Support,
    PuntosGanados,
    SlideAction,
    RatingQuestion,
    TicketRating,
    WifiConnectionLog,
    MassPointsLoad,
    PointsByPlanCategory,
    PointsCategory,
)
from auditlog.models import LogEntry
from apis.clients.api import User

# ODOO CLASSES
class ContractStatusViewSet(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ContractStatusSerializer(data=request.data)
        if serializer.is_valid():
            url_search_state = "https://erp.nettplus.net/app/search_state"
            url_search = "https://erp.nettplus.net/app/search"
            search_data = {
                "name_contract": serializer.data["contract"],
                "valor_busqueda": serializer.data["contract_id"],
            }
            state_data = {"contract": serializer.data["contract_id"]}
            result = []
            try:
                response_state = requests.post(url_search_state, json=state_data)
                response_search = requests.post(url_search, json=search_data)
                if (
                    response_state.status_code == 200
                    and response_search.status_code == 200
                ):
                    result = {**response_state.json()[0], **response_search.json()[0]}
            except requests.exceptions.RequestException as e:
                return Response(result, status=status.HTTP_404_NOT_FOUND)

            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterTicketViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = RegisterTicketSerializer(data=request.data)

        if serializer.is_valid():

            url = "https://erp.nettplus.net/app/register_websites_ticket"
            result = []
            try:
                response = requests.post(url, json=serializer.data)
                if response.status_code == 200:
                    result = response.json()
                    try:
                        Support.objects.create(
                            support_id=result[0].get("numeroTicket"),
                            comment=serializer.data.get("comment"),
                        )
                    except Exception as e:
                        pass
                elif response.status_code == 500:
                    result = response.json()
                    return Response(
                        {"error": "No se pudo crear el Ticket"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except requests.exceptions.RequestException as e:
                return Response(result, status=status.HTTP_404_NOT_FOUND)

            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvoiceViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = InvoiceSerializer(data=request.data)
        if serializer.is_valid():
            url = "https://erp.nettplus.net/app/invoices_search"
            result = []
            try:
                response = requests.post(url, json=serializer.data)
                if response.status_code == 200:
                    result = response.json()
            except requests.exceptions.RequestException as e:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TicketSearchViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = TicketSearchSerializer(data=request.data)
        if serializer.is_valid():
            url = "https://erp.nettplus.net/app/tickets_search"
            result = []

            try:
                response = requests.post(url, json=serializer.data)
                if response.status_code == 200:
                    result = response.json()
            except requests.exceptions.RequestException as e:
                return Response(
                    {"error": "Error al comunicarse con el servicio externo"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SliderHomeViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = SliderHome.objects.all()
    serializer_class = SliderSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class SliderSecondViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = SliderSecond.objects.all()
    serializer_class = SliderSecondSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 300


class WifiPointViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = WifiPointSerializer
    queryset = WifiPoint.objects.all()
    pagination_class = None

    def get_serializer_class(self):
        if self.request.query_params.get("all"):
            return WifiPointSerializerAll
        return WifiPointSerializer

    def get_queryset(self):
        queryset = WifiPoint.objects.all()

        queryset = queryset.exclude(
            Q(latitude__in=["0", "0.0"]) | Q(longitude__in=["0", "0.0"])
        )

        type_param = self.request.query_params.get("type")
        if type_param:
            queryset = queryset.filter(type=type_param)

        return queryset

    def list(self, request, *args, **kwargs):
        """Retorna todos los registros sin paginación"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class WifiConnectionLogViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = WifiConnectionLogSerializer(data=request.data)
        if serializer.is_valid():
            WifiConnectionLog.objects.create(
                user=request.user,
                contract_code=serializer.validated_data["contract_code"],
                wifi_point=serializer.validated_data["wifi_point"],
            )
            return Response(
                {"message": "Conexión registrada correctamente"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ContractViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    lookup_field = "contract_id"

    def create(self, request, *args, **kwargs):
        create_response = super().create(request, *args, **kwargs)

        response_data = create_response.data
        response_data["state_service"] = self.get_odoo_active_status(
            create_response.data
        )

        return Response(response_data, status=create_response.status_code)

    def retrieve(self, request, *args, **kwargs):
        """Handle GET request for a single object."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Add the custom field to the serialized data
        response_data = serializer.data
        response_data["state_service"] = self.get_odoo_active_status(response_data)

        return Response(response_data)

    def get_odoo_active_status(self, contract_data):
        try:
            url = "https://erp.nettplus.net/app/search_state"
            data = {"contract": contract_data["odoo_id_contract"]}
            response = requests.post(url, json=data)
            if response.status_code == 200:
                return response.json()[0]["state"]
        except requests.exceptions.RequestException:
            return ""


class ServiceViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer


class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["referred_phone", "referred_email", "user__contract__contract_id"]

    def get_queryset(self):
        user = self.request.user
        queryset = Referral.objects.all()

        # Si no es superusuario se filtra solo las referencias creadas por el usuario
        if not user.is_superuser:
            queryset = queryset.filter(user=user)

        # Aplicar filtros desde los parámetros de consulta
        phone = self.request.query_params.get("phone")
        email = self.request.query_params.get("email")
        contract_id = self.request.query_params.get("contract_id")

        if phone:
            queryset = queryset.filter(referred_phone__icontains=phone)
        if email:
            queryset = queryset.filter(referred_email__icontains=email)
        if contract_id:
            queryset = queryset.filter(user__contract__contract_id=contract_id)

        return queryset

    @action(detail=True, methods=["patch"], url_path="changestatus")
    def change_status(self, request, pk=None):
        """
        Cambiar el estado de una referencia.
        """
        try:
            referral = self.get_object()
        except Referral.DoesNotExist:
            return Response(
                {"error": "La referencia no existe."}, status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get("status_reference")
        points = request.data.get("points", 1000)

        if new_status not in ["Pending", "Accepted", "Rejected"]:
            return Response(
                {"error": "El estado debe ser 'Pending', 'Accepted' o 'Rejected'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Si el nuevo estado es "Accepted" se otorga puntos al usuario que refirió
        if new_status == "Accepted":
            referring_user = referral.user

            with transaction.atomic():
                # Sumar los puntos al usuario
                referring_user.points += points
                referring_user.save()

                # Crear una transacción de tipo "Internal" para registrar los puntos otorgados
                Transaction.objects.create(
                    user=referring_user,
                    tipo="Internal",
                    amount=points,
                    saldo=referring_user.points,
                    transaction_status="Completed",
                    descripcion=f"Puntos otorgados por referencia aceptada: {referral.referred_name}",
                )

                # Crear una notificación local en la base de datos
                UserNotificationService.create_notification(
                    referring_user,
                    "¡Has recibido puntos!",
                    f"Se te han agregado {points} puntos por haber sido aprobada la referencia del nuevo usuario {referral.referred_name}.",
                )

                # Buscar dispositivo FCM del usuario que refirió
                referring_device = FCMDevice.objects.filter(user=referring_user).first()

                if referring_device and referring_device.registration_id:
                    # Enviar notificación push con Firebase
                    FirebaseNotificationService.send_firebase_notification(
                        referring_device.registration_id,
                        "¡Has recibido puntos!",
                        f"Se te han agregado {points} puntos por haber sido aprobada la referencia del nuevo usuario {referral.referred_name}.",
                        data=None,
                    )

        # Actualizar el estado
        referral.status_reference = new_status
        referral.save()

        return Response(
            {
                "message": f"Estado de la referencia actualizado a {new_status}.",
                "referral": ReferralSerializer(referral).data,
            },
            status=status.HTTP_200_OK,
        )

    def list(self, request, *args, **kwargs):
        """
        GET: Listar todas las referencias existentes.
        """
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Serializar y devolver los datos
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="filterbyrange")
    def filter_by_range(self, request):
        """
        Filtrar referencias por un rango de fechas basado en 'created_at'.
        """
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # Validar que las fechas se hayan proporcionado
        if not start_date or not end_date:
            return Response(
                {"error": "Los parámetros 'start_date' y 'end_date' son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar el formato de las fechas
        try:
            start_date = datetime.strptime(start_date, "%d-%m-%Y").date()
            end_date = datetime.strptime(end_date, "%d-%m-%Y").date()
        except ValueError:
            return Response(
                {"error": "El formato de las fechas debe ser 'DD-MM-YYYY'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar el rango de fechas
        if start_date > end_date:
            return Response(
                {"error": "La fecha 'start_date' no puede ser mayor que 'end_date'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Filtrar referencias por rango de fechas
        queryset = self.get_queryset().filter(
            created_at__date__gte=start_date, created_at__date__lte=end_date
        )

        # Serializar y devolver los datos
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="search")
    def search_references(self, request):
        """
        Buscar referencias por usuario que refiere, correo o teléfono del referido.
        """
        user_query = request.query_params.get("user")
        email_query = request.query_params.get("email")
        phone_query = request.query_params.get("phone")

        # Obtener el conjunto de datos base
        queryset = self.get_queryset()

        # Aplicar filtros condicionales
        if user_query:
            queryset = queryset.filter(user__username__icontains=user_query)
        if email_query:
            queryset = queryset.filter(referred_email__icontains=email_query)
        if phone_query:
            queryset = queryset.filter(referred_phone__icontains=phone_query)

        # Serializar y devolver los resultados
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SpeedHistoryViewSet(viewsets.ModelViewSet):
    queryset = SpeedHistory.objects.all()
    serializer_class = SpeedHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if self.request.user.is_superuser:
            return super().get_queryset()
        else:
            return super().get_queryset().filter(user=user)


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["tipo"]
    search_fields = ["user__username", "date"]

    @action(detail=False, methods=["get"], url_path="search")
    def search_transactions(self, request):
        """
        Endpoint personalizado para buscar transacciones por tipo y coincidencias.
        """
        tipo = request.query_params.get("tipo")
        search = request.query_params.get("search")

        # Filtrar por tipo si se proporciona
        queryset = self.get_queryset()
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        # Filtrar por búsqueda general (usuario o fecha)
        if search:
            queryset = queryset.filter(
                user__username__icontains=search
            ) | queryset.filter(date__icontains=search)

        # Serializar y devolver los resultados
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="filterbyrange")
    def filter_by_range(self, request):
        """
        Filtro por tipo y rango de fechas.
        """
        tipo = request.query_params.get("tipo")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # Validar que se hayan proporcionado los parámetros necesarios
        if not tipo:
            return Response(
                {"error": "El parámetro 'tipo' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not start_date or not end_date:
            return Response(
                {"error": "Los parámetros 'start_date' y 'end_date' son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar el formato de las fechas
        try:
            start_date = datetime.strptime(start_date, "%d-%m-%Y").date()
            end_date = datetime.strptime(end_date, "%d-%m-%Y").date()
        except ValueError:
            return Response(
                {"error": "El formato de las fechas debe ser 'DD-MM-YYYY'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar el rango de fechas
        if start_date > end_date:
            return Response(
                {"error": "La fecha 'start_date' no puede ser mayor que 'end_date'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Filtrar las transacciones
        queryset = self.get_queryset().filter(
            tipo=tipo, date__date__gte=start_date, date__date__lte=end_date
        )

        # Serializar y devolver los datos
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        user = self.request.user
        if self.request.user.is_superuser:
            return super().get_queryset()
        else:
            return super().get_queryset().filter(user=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Transacción registrada exitosamente.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=["get"], url_path="searchbyid")
    def search_by_id(self, request, pk=None):
        try:
            transaction = self.get_object()
            serializer = self.get_serializer(transaction)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Transaction.DoesNotExist:
            return Response(
                {"error": "Transacción no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["patch"], url_path="changestatus")
    def change_status(self, request, pk=None):
        try:
            transaction = self.get_object()
            new_status = request.data.get("transaction_status")

            if new_status not in ["Pending", "Completed", "Cancelled"]:
                return Response(
                    {"error": "Estado no válido."}, status=status.HTTP_400_BAD_REQUEST
                )

            if transaction.transaction_status == "Cancelled":
                return Response(
                    {
                        "error": "No se puede cambiar el estado de una transacción anulada."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            transaction.transaction_status = new_status
            transaction.save()
            return Response(
                {"message": "Estado actualizado correctamente."},
                status=status.HTTP_200_OK,
            )
        except Transaction.DoesNotExist:
            return Response(
                {"error": "Transacción no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )


class HotspotAccountViewSet(viewsets.ModelViewSet):
    queryset = HotspotAccount.objects.all()
    serializer_class = HotspotAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if self.request.user.is_superuser:
            return super().get_queryset()
        else:
            return super().get_queryset().filter(user=user)

    @action(detail=True, methods=["patch"], url_path="changestatus")
    def change_status(self, request, pk=None):
        try:
            account = self.get_object()
        except HotspotAccount.DoesNotExist:
            return Response(
                {"error": "Cuenta no encontrada."}, status=status.HTTP_404_NOT_FOUND
            )

        # Obtener el nuevo estado de la cuenta
        is_enabled = request.data.get("is_enabled")
        if is_enabled is None:
            return Response(
                {"error": "El parámetro 'is_enabled' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar que el valor proporcionado sea un booleano
        if not isinstance(is_enabled, bool):
            return Response(
                {
                    "error": "El parámetro 'is_enabled' debe ser un valor booleano (true o false)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Actualizar el estado de la cuenta
        account.is_enabled = is_enabled

        # Si es un cliente y se desactiva, cambiar el váucher a "Inactive"
        if not is_enabled and account.tipo == "Client":
            account.vaucher = "Inactive"
        elif is_enabled and account.tipo == "Client":
            account.vaucher = "Unlimited"

        account.save()

        return Response(
            {
                "message": f"Cuenta {'activada' if is_enabled else 'desactivada'} exitosamente.",
                "data": HotspotAccountSerializer(account).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="filterbytype")
    def filter_by_type(self, request):
        tipo = request.query_params.get("tipo")

        # Validar el tipo proporcionado
        if tipo not in ["Client", "NonClient"]:
            return Response(
                {"error": "El parámetro 'tipo' debe ser 'Client' o 'NonClient'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Filtrar las cuentas por tipo
        queryset = self.get_queryset().filter(tipo=tipo)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        data = request.data

        # Validar si el campo 'password_hotspot' está presente, sino se autogenera
        if not data.get("password_hotspot"):
            data["password_hotspot"] = HotspotAccount.generate_password()

        # Validar si el tipo es 'NonClient' y contract no debe estar presente
        if data.get("tipo") == "NonClient" and data.get("contract"):
            return Response(
                {
                    "error": "El campo 'contract' debe ser null si el tipo es 'NonClient'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Serializar y validar datos
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Cuenta Hotspot registrada exitosamente.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )


class AuthenticateViewSet(ViewSet):
    permission_classes = [AllowAny]
    serializer_class = AuthTokenSerializer

    def create(self, request):
        serializer = AuthTokenSerializer(
            data=request.data, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        current_registration_id = serializer.data.pop("registration_id", None)
        user = serializer.validated_data["user"]
        close_existing = request.data.get("close_existing", False)
        token, created = Token.objects.get_or_create(user=user)

        # First-time login
        if created:
            user_data = UserProfileSerializer(user, context={"request": request}).data
            odoo_data = self.login_into_erp(user_data)
            user_data = self.enrich_contracts_with_odoo_data(user_data, odoo_data)
            print(user)
            return Response(
                {
                    "token": token.key,
                    "unread_notifications": user.get_unread_notifications(),
                    "user": user_data,
                },
                status=HTTP_201_CREATED,
            )

        # Close existing session and create new token
        if not created and close_existing:
            # enviar notificacion al dispisitivo an terior
            user_fcm = FCMDevice.objects.filter(user=user)
            register_ = user_fcm.filter(registration_id=current_registration_id).first()
            old_id = user_fcm.exclude(registration_id=current_registration_id).first()
            if not register_ and old_id:
                FirebaseNotificationService.send_firebase_notification(
                    old_id.registration_id,
                    title="🚨Has cerrado sesión 🚨",
                    body="Hemos detectado un cierre de sesión en tu cuenta. Si no fuiste tú, por favor revisa tu configuración de seguridad.",
                    data=None,
                )
                old_id.delete()

            token.delete()
            new_token = Token.objects.create(user=user)
            user_data = UserProfileSerializer(user, context={"request": request}).data
            odoo_data = self.login_into_erp(user_data)
            user_data = self.enrich_contracts_with_odoo_data(user_data, odoo_data)

            return Response(
                {
                    "token": new_token.key,
                    "unread_notifications": user.get_unread_notifications(),
                    "user": user_data,
                },
                status=HTTP_201_CREATED,
            )

    def login_into_erp(self, user_data):
        try:
            contract = Contract.objects.filter(
                userprofile__username=user_data["username"]
            )
            url = "https://erp.nettplus.net/app/login"
            if contract.exists():
                data = {
                    "password": contract.first().identification,
                    "username": contract.first().email,
                }
                response = requests.post(url, json=data)
                if response.status_code == 200:
                    return response.json()
            return {}
        except requests.exceptions.RequestException:
            return {}

    def enrich_contracts_with_odoo_data(self, user_data, odoo_data):
        contracts = user_data.get("contracts", [])
        odoo_contracts = []

        # Flatten Odoo contracts
        for odoo_item in odoo_data:
            odoo_contracts.extend(odoo_item.get("contratos", []))

        # Create a lookup dictionary for Odoo contracts by name
        odoo_contracts_dict = {
            contract["name"]: contract for contract in odoo_contracts
        }

        # Enrich each contract in user_data with corresponding Odoo details
        for contract in contracts:
            contract_id = contract.get("contract_id")
            contract["odoo_details"] = odoo_contracts_dict.get(contract_id, None)

        user_data["contracts"] = contracts
        return user_data

class AuthenticateViewSetToken(ViewSet):
    permission_classes = [AllowAny]
    serializer_class = AuthTokenSerializer

    def create(self, request):
        serializer = AuthTokenSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # No sobreescribir token si ya existe, de esta forma se evita que se cierre la sesión
        # de otros dispositivos al iniciar sesión desde uno nuevo.
        token, created = Token.objects.get_or_create(user=user)

        user_data = UserProfileSerializer(user, context={"request": request}).data

        return Response(
            {
                "token": token.key,
                "unread_notifications": user.get_unread_notifications(),
                "user": user_data,
            },
            status=HTTP_201_CREATED if created else HTTP_200_OK,
        )


class SimpleAuthenticateView(ViewSet):
    print("Metodo simple")
    permission_classes = [AllowAny]
    serializer_class = AuthTokenSerializer

    def create(self, request):
        serializer = AuthTokenSerializer(
            data=request.data, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        current_registration_id = serializer.data.pop("registration_id", None)
        user = serializer.validated_data["user"]
        close_existing = request.data.get("close_existing", False)
        token, created = Token.objects.get_or_create(user=user)

        # First-time login
        if created:
            user_data = SimpleUserProfileSerializer(user, context={"request": request}).data
            odoo_data = self.login_into_erp(user_data)
            user_data = self.enrich_contracts_with_odoo_data(user_data, odoo_data)
            print(user)
            return Response(
                {
                    "token": token.key,
                    "unread_notifications": user.get_unread_notifications(),
                    "user": user_data,
                },
                status=HTTP_201_CREATED,
            )

        # Close existing session and create new token
        if not created and close_existing:
            # enviar notificacion al dispisitivo an terior
            user_fcm = FCMDevice.objects.filter(user=user)
            register_ = user_fcm.filter(registration_id=current_registration_id).first()
            old_id = user_fcm.exclude(registration_id=current_registration_id).first()
            if not register_ and old_id:
                FirebaseNotificationService.send_firebase_notification(
                    old_id.registration_id,
                    title="🚨Has cerrado sesión 🚨",
                    body="Hemos detectado un cierre de sesión en tu cuenta. Si no fuiste tú, por favor revisa tu configuración de seguridad.",
                    data=None,
                )
                old_id.delete()

            token.delete()
            new_token = Token.objects.create(user=user)
            user_data = SimpleUserProfileSerializer(user, context={"request": request}).data
            odoo_data = self.login_into_erp(user_data)
            user_data = self.enrich_contracts_with_odoo_data(user_data, odoo_data)

            return Response(
                {
                    "token": new_token.key,
                    "unread_notifications": user.get_unread_notifications(),
                    "user": user_data,
                },
                status=HTTP_201_CREATED,
            )

    def login_into_erp(self, user_data):
        try:
            contract = Contract.objects.filter(
                userprofile__username=user_data["username"]
            )
            url = "https://erp.nettplus.net/app/login"
            if contract.exists():
                data = {
                    "password": contract.first().identification,
                    "username": contract.first().email,
                }
                response = requests.post(url, json=data)
                if response.status_code == 200:
                    return response.json()
            return {}
        except requests.exceptions.RequestException:
            return {}

    def enrich_contracts_with_odoo_data(self, user_data, odoo_data):
        contracts = user_data.get("contracts", [])
        odoo_contracts = []

        # Obtener todos los contratos desde Odoo
        for odoo_item in odoo_data:
            odoo_contracts.extend(odoo_item.get("contratos", []))

        # Diccionario para hacer lookup por contract_id
        odoo_contracts_dict = {contract["name"]: contract for contract in odoo_contracts}

        # Enriquecer contratos existentes sin reemplazar estructura
        for contract in contracts:
            contract_id = contract.get("contract_id")
            contract["odoo_details"] = odoo_contracts_dict.get(contract_id)

        return user_data
    
class AuthenticateNettplusViewSet(ViewSet):
    permission_classes = [AllowAny]
    serializer_class = AuthTokenSerializer

    def create(self, request):
        serializer = AuthTokenSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        #  Validar que el usuario tenga un correo @nettplus.net
        if not user.email.endswith("@nettplus.net"):
            return Response(
                {
                    "error": "Acceso restringido. Solo usuarios con correo @nettplus.net pueden ingresar."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Generar token de autenticación
        token, created = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": UserProfileSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    Endpoint para que los usuarios puedan cambiar su contraseña.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not user.check_password(old_password):
            return Response(
                {"error": "La contraseña actual es incorrecta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar que la nueva contraseña cumpla con ciertos criterios
        if len(new_password) < 8:
            return Response(
                {"error": "La nueva contraseña debe tener al menos 8 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.username.lower() in new_password.lower():
            return Response(
                {
                    "error": "La nueva contraseña no puede asemejarse a tu nombre de usuario."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password in ["12345678", "password", "admin", "qwerty"]:
            return Response(
                {
                    "error": "La nueva contraseña no puede ser una clave comúnmente utilizada."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password.isdigit():
            return Response(
                {"error": "La nueva contraseña no puede ser completamente numérica."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cambiar la contraseña
        user.set_password(new_password)
        user.save()

        # Enviar notificación por correo electrónico
        send_mail(
            subject="Cambio de Contraseña",
            message=(
                f"Hola {user.username},\n\n"
                "Tu contraseña ha sido actualizada con éxito. Si no realizaste este cambio, "
                "te recomendamos contactar inmediatamente a nuestro equipo de soporte para garantizar la seguridad de tu cuenta.\n\n"
                "Gracias por confiar en nosotros.\n"
                "Atentamente,\n"
                "El equipo de soporte."
            ),
            from_email="ticsncs@nettplus.net",
            recipient_list=[user.email],
        )

        return Response(
            {"message": "Contraseña cambiada exitosamente."}, status=status.HTTP_200_OK
        )


class ChangePasswordNettplusView(APIView):
    """
    Endpoint para cambiar la contraseña SOLO para usuarios con correos @nettplus.net.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        #  Validar que el usuario tenga un correo @nettplus.net
        if not user.email.endswith("@nettplus.net"):
            return Response(
                {
                    "error": "Acceso restringido. Solo usuarios con correo @nettplus.net pueden cambiar su contraseña."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validar la contraseña anterior
        if not user.check_password(old_password):
            return Response(
                {"error": "La contraseña actual es incorrecta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar requisitos de seguridad de la nueva contraseña
        if len(new_password) < 8:
            return Response(
                {"error": "La nueva contraseña debe tener al menos 8 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.username.lower() in new_password.lower():
            return Response(
                {
                    "error": "La nueva contraseña no puede contener tu nombre de usuario."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password in ["12345678", "password", "admin", "qwerty"]:
            return Response(
                {"error": "La nueva contraseña no puede ser demasiado común."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password.isdigit():
            return Response(
                {"error": "La nueva contraseña no puede ser solo numérica."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cambiar la contraseña
        user.set_password(new_password)
        user.save()

        send_mail(
            subject="Cambio de Contraseña",
            message=(
                f"Hola {user.username},\n\n"
                "Tu contraseña ha sido actualizada con éxito. Si no realizaste este cambio, "
                "te recomendamos contactar inmediatamente a nuestro equipo de soporte para garantizar la seguridad de tu cuenta.\n\n"
                "Gracias por confiar en nosotros.\n"
                "Atentamente,\n"
                "El equipo de soporte."
            ),
            from_email="ticsncs@nettplus.net",
            recipient_list=[user.email],
        )

        return Response(
            {"message": "Contraseña actualizada correctamente."},
            status=status.HTTP_200_OK,
        )


class PasswordRecoveryView(APIView):
    """
    Endpoint para recuperación de contraseña.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        try:
            # Verificar si el correo existe en la base de datos
            user = User.objects.get(email=email)

            # Generar una contraseña temporal
            temporary_password = "".join(
                random.choices(string.ascii_letters + string.digits, k=8)
            )

            # Cambiar la contraseña del usuario
            user.set_password(temporary_password)
            user.save()

            # Enviar correo con la contraseña temporal
            send_mail(
                subject="Recuperación de Contraseña",
                message=(
                    f"Hola {user.username},\n\n"
                    f"Hemos recibido tu solicitud para restablecer la contraseña. "
                    f"A continuación, encontrarás tu nueva contraseña temporal:\n\n"
                    f"Contraseña temporal: {temporary_password}\n\n"
                    f"Te recomendamos que cambies esta contraseña por una personalizada "
                    f"inmediatamente después de iniciar sesión en la sección de editar perfil.\n\n"
                    f"Si no realizaste esta solicitud, por favor contacta con nuestro equipo de soporte.\n\n"
                    f"Atentamente,\n"
                    f"El equipo de soporte de Nettplus."
                ),
                from_email="ticsncs@nettplus.net",
                recipient_list=[email],
            )

            return Response(
                {"message": "Se ha enviado una contraseña temporal a tu correo."},
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "No se encontró un usuario con este correo electrónico."},
                status=status.HTTP_404_NOT_FOUND,
            )


class UserProfileViewSet(ModelViewSet):
    """
    ViewSet para gestionar usuarios.
    """

    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [AllowAny]

    def perform_update(self, serializer):
        instance = serializer.save()

        from auditlog.models import LogEntry

        LogEntry.objects.filter(
            object_id=instance.id, action=LogEntry.Action.UPDATE
        ).update(actor=self.request.user)

    def update(self, request, *args, **kwargs):
        """
        PUT: Actualización completa del usuario.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_serializer_class(self):
        if self.request.query_params.get("lite"):
            return UserProfileSerializerLite
        return UserProfileSerializer

    @action(detail=False, methods=["get"], url_path="search")
    def search_user(self, request):
        identification = request.query_params.get("identification", None)
        email = request.query_params.get("email", None)
        cellphone = request.query_params.get("cellphone", None)

        if not identification and not email and not cellphone:
            return Response(
                {
                    "error": "Debe proporcionar al menos un parámetro de búsqueda (identification, email o cellphone)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar el contrato que coincida con los datos proporcionados
        contracts = Contract.objects.filter(
            Q(identification=identification) | Q(email=email) | Q(cellphone=cellphone)
        )

        if not contracts.exists():
            return Response(
                {
                    "error": "No se encontró ningún contrato con los datos proporcionados."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        user_fathers = UserProfile.objects.filter(
            usercontract__in=contracts, father=True
        )

        contract_data = ContractSerializer(contracts, many=True).data

        for i, contract in enumerate(contract_data):
            user_father = user_fathers.filter(usercontract=contracts[i]).first()
            if user_father:
                contract["parent_user_username"] = user_father.username
                contract["parent_user_points"] = user_father.points
                contract["parent_user_found"] = True
            else:
                contract["parent_user_username"] = None
                contract["parent_user_points"] = 0
                contract["parent_user_found"] = False

        return Response(contract_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="privacyterms")
    def update_privacy_terms(self, request, pk=None):
        user = self.get_object()
        privacityandterms = request.data.get("privacityandterms")

        if privacityandterms is None:
            return Response(
                {"error": "The 'privacityandterms' field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.privacityandterms = privacityandterms
        user.save()

        if privacityandterms:
            bienvenida_category = PointsCategory.objects.filter(
                name="BIENVENIDA APP CLIENTES", enabled=True
            ).first()

            if bienvenida_category:

                if bienvenida_category.only_with_fathers and not user.father:
                    pass
                else:
                    if user.father:
                        user_contract = user.usercontract.first()
                    else:
                        user_contract = user.contract
                    point_config = PointsByPlanCategory.objects.filter(
                        category=bienvenida_category,
                        plan=user_contract.planInternet,
                    ).first()

                    if point_config:
                        points_to_assign = point_config.points
                        user.points += points_to_assign
                        user.save()

                        # Crear la transacción de puntos por bienvenida
                        Transaction.objects.create(
                            user=user,
                            amount=points_to_assign,
                            status=0,
                            tipo="Internal",
                            transaction_status="Completed",
                            saldo=user.points,
                            descripcion=f"Puntos asignados por bienvenida: {bienvenida_category.name}",
                        )

                        # Crear notificación para el usuario
                        UserNotificationService.create_notification(
                            user,
                            "Puntos acreditados por bienvenida",
                            f"Se te han asignado {points_to_assign} puntos por completar la aceptación de términos y condiciones de la aplicación.",
                        )

                        # Enviar notificación push si el usuario tiene un dispositivo FCM registrado
                        claimant_device = FCMDevice.objects.filter(user=user).first()
                        if claimant_device and claimant_device.registration_id:
                            FirebaseNotificationService.send_firebase_notification(
                                claimant_device.registration_id,
                                "Puntos acreditados por bienvenida",
                                f"Se te han asignado {points_to_assign} puntos por completar la aceptación de términos y condiciones.",
                                data=None,
                            )

        return Response(
            {
                "message": "Privacy and terms updated successfully!",
                "user_id": user.id,
                "privacityandterms": user.privacityandterms,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="privacyterms")
    def get_privacy_terms(self, request):
        user = request.user
        return Response(
            {"user_id": user.id, "privacityandterms": user.privacityandterms},
            status=status.HTTP_200_OK,
        )

class AllUsersContracts(APIView):
    """
    Endpoint para obtener todos los contratos de un usuario por su correo electrónico.
    """

    permission_classes = [IsAuthenticated]
    def get(self, request, email):
        """
        Obtiene todos los contratos asociados al correo electrónico proporcionado.
        """
        try:
            user = User.objects.get(email=email)
            contracts = Contract.objects.filter(userprofile__username=user)

            if not contracts.exists():
                return Response(
                    {"error": "No se encontraron contratos para este usuario."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = SimpleContractSerializer(contracts, many=True)
            # Agregar datos de usuario al resultado
            user_data = UserProfileSerializer(user, context={"request": request}).data

            #saco todos los son_number de user_data y los sumo
            total_son_avaible = sum(
                contract.son_number for contract in contracts
            )

            #saco todos los son_number de user_data y los sumo
            total_son_limit = sum(
                contract.user_limit for contract in contracts
            )

            #total de puntos de los usuarios hijos y que esten activos
            total_points = sum(
                user.points for user in UserProfile.objects.filter(
                    contract__in=contracts, is_active=True, father=False
                )
            ) + user.points


            return Response(
                {
                    "username": user_data.get("email"),
                    "total_son_limit": total_son_limit,
                    "total_son_avaible": total_son_avaible,
                    "total_points_family": total_points,
                    "contracts": serializer.data,
           
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )


class GetFatherUserByContract(APIView):
    permission_classes = [IsAuthenticated]  # Opcional: usa AllowAny si es pública

    def get(self, request, contract_id):
        try:
            # Buscar contrato
            contract = Contract.objects.get(contract_id=contract_id)
            
        except Contract.DoesNotExist:
            return Response(
                {"error": "Contrato no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )        

        return Response(contract.userprofile.email, status=status.HTTP_200_OK)


class ContractUserView(APIView):

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        instance = serializer.save()


        LogEntry.objects.filter(
            object_id=instance.id, action=LogEntry.Action.UPDATE
        ).update(actor=self.request.user)

    def get(self, request, contract_id):
        print("Ingrese al get de contrato")
        try:
            # Obtener el contrato
            contract = Contract.objects.get(contract_id=contract_id)

            # Obtener el parámetro de filtro (si está presente)
            father_filter = request.query_params.get("father", None)

            # Filtrar usuarios según el parámetro 'father'
            users = UserProfile.objects.filter(contract=contract, is_active=True)
            if father_filter is not None:
                users = users.filter(
                    father=father_filter.lower() in ["true", "1", "yes"]
                )

            # Contar y serializar los usuarios
            user_count = users.count()
            user_data = UserProfileSerializer(
                users, many=True, context={"request": request}
            ).data
            print("DATA", user_data)
            return Response(
                {
                    "contract_id": contract.contract_id,
                    "user_count": user_count,
                    "user_limit": contract.user_limit,
                    "son_number": contract.son_number,
                    "users": user_data,
                },
                status=status.HTTP_200_OK,
            )
        except Contract.DoesNotExist:
            return Response(
                {"error": "Contrato no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

    def post(self, request):
        try:
            email = request.data.get("email")
            contract_id = request.data.get("contract_id")

            if not email or not contract_id:
                return Response(
                    {"error": "Se requiere 'email' y 'contract_id' en el cuerpo de la solicitud."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Buscar contrato
            contract = Contract.objects.get(contract_id=contract_id)

            # Verificar límite de usuarios activos
            active_users_count = UserProfile.objects.filter(
                contract=contract, is_active=True, father=False
            ).count()

            if active_users_count >= contract.user_limit:
                return Response(
                    {
                        "error": "El límite de usuarios para este contrato ha sido alcanzado. Te sugerimos contratar un plan superior para añadir más usuarios."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verificar si el email ya está registrado
            if User.objects.filter(email=email).exists():
                return Response(
                    {"email": "El correo electrónico ya está registrado. Por favor, use otro."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Generar contraseña segura
            generated_password = get_random_string(length=10)

            # Preparar datos para el serializer
            data = {
                "email": email,
                "username": email,
                "password": generated_password,
                "contract": contract.id
            }

            serializer = UserProfileSerializer(data=data)
            if serializer.is_valid():
                user = serializer.save()
                user.set_password(generated_password)
                user.save()

                # ✅ SOLO ENVIAR EMAIL DESPUÉS DE GUARDAR EXITOSAMENTE
                enviar_correo_bienvenida(user, email, generated_password)
                print(f"Correo enviado a {email} con la contraseña generada ahora.")

                # Notificar al usuario padre
                parent_user = UserProfile.objects.filter(contract=contract, father=True).first()
                if parent_user:
                    UserNotificationService.create_notification(
                        parent_user,
                        "Nuevo usuario hijo registrado",
                        f"El usuario {user.username} se ha registrado exitosamente bajo el contrato {contract.contract_id}.",
                    )

                    parent_device = FCMDevice.objects.filter(user=parent_user).first()
                    if parent_device and parent_device.registration_id:
                        FirebaseNotificationService.send_firebase_notification(
                            parent_device.registration_id,
                            "Nuevo usuario hijo registrado",
                            f"El usuario {user.username} se ha registrado exitosamente bajo el contrato {contract.contract_id}.",
                            data=None,
                        )

                return Response(
                    {"message": "Usuario hijo agregado correctamente."},
                    status=status.HTTP_201_CREATED,
                )

            # Si el serializer no es válido, NO se envía correo
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Contract.DoesNotExist:
            return Response({"error": "Contrato no encontrado."}, status=status.HTTP_404_NOT_FOUND)


        def delete(self, request, contract_id, user_id):
            try:
                contract = Contract.objects.get(contract_id=contract_id)
                user = UserProfile.objects.get(id=user_id, contract=contract)

                # Verificar si es un usuario hijo (no padre)
                if user.father:
                    return Response(
                        {"error": "No se puede eliminar al usuario padre."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Verificar si el usuario está activo antes de eliminarlo
                if not user.is_active:
                    return Response(
                        {"error": "El usuario ya está inactivo."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Eliminar el usuario de la base de datos completamente
                user.delete()

                # Actualizar el número de usuarios hijos en el contrato
                contract.son_number = UserProfile.objects.filter(
                    contract=contract, father=False
                ).count()
                contract.save(update_fields=["son_number"])

                return Response(
                    {"message": "Usuario eliminado correctamente."},
                    status=status.HTTP_200_OK,
                )

            except Contract.DoesNotExist:
                return Response(
                    {"error": "Contrato no encontrado."}, status=status.HTTP_404_NOT_FOUND
                )
            except UserProfile.DoesNotExist:
                return Response(
                    {"error": "Usuario no encontrado o no pertenece a este contrato."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        def patch(self, request, contract_id):
            try:
                contract = Contract.objects.get(contract_id=contract_id)
                serializer = ContractSerializer(
                    contract, data=request.data, partial=True, context={"request": request}
                )
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Contract.DoesNotExist:
                return Response(
                    {"error": "Contrato no encontrado."}, status=status.HTTP_404_NOT_FOUND
                )

        def put(self, request, contract_id, user_id):
            """
            Actualizar completamente los campos del perfil de usuario
            """
            try:
                # Verificar que el contrato existe
                contract = Contract.objects.get(contract_id=contract_id)

                # Verificar que el usuario pertenece al contrato
                user = UserProfile.objects.get(id=user_id, contract=contract)

                # Serializador para validar y actualizar completamente los datos
                serializer = UserProfileSerializer(
                    user, data=request.data
                )  # Sin partial=True para forzar actualización completa
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Contract.DoesNotExist:
                return Response(
                    {"error": "Contrato no encontrado."}, status=status.HTTP_404_NOT_FOUND
                )
            except UserProfile.DoesNotExist:
                return Response(
                    {"error": "Usuario no encontrado o no pertenece a este contrato."},
                    status=status.HTTP_404_NOT_FOUND,
                )


class PuntosGanadosViewSet(ModelViewSet):
    queryset = PuntosGanados.objects.all()
    serializer_class = PuntosGanadosSerializer


class UserGroupViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserGroupSerializer
    permission_classes = [IsAuthenticated]


class SupportViewSet(viewsets.ModelViewSet):
    queryset = Support.objects.all()
    serializer_class = SupportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        support_id = self.request.query_params.get("support_id")
        if support_id:
            queryset = queryset.filter(support_id=support_id)
        return queryset


class SlideActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        slide_count = request.data.get("slide_count")

        if not user_id or not slide_count:
            return Response(
                {"error": "Campos obligatorios"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        slide_action, created = SlideAction.objects.get_or_create(
            user=user, defaults={"slide_count": slide_count}
        )
        if not created:
            slide_action.slide_count += slide_count
            slide_action.save()

        serializer = SlideActionSerializer(slide_action)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TransferPointsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="transfer")
    def transfer_points(self, request):
        serializer = TransferPointsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        sender = UserProfile.objects.get(pk=data["sender_id"])
        receiver = UserProfile.objects.get(pk=data["receiver_id"])
        points = data["points"]
        contract_id = data["contract_id"]

        if sender.father:
            sender_contract = Contract.objects.filter(userprofile=sender).first()
        else:
            sender_contract = Contract.objects.filter(id=sender.contract_id).first()

        if not sender_contract:
            return Response(
                {"error": "El usuario padre no tiene este contrato asignado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Determinar la descripción de la transacción
        if sender.father:
            description = f"Transferencia de puntos usuario {sender.username} (padre) a usuario {receiver.username} (hijo) bajo el contrato {contract_id}"
        else:
            description = f"Transferencia de puntos usuario {sender.username} (hijo) a usuario {receiver.username} (padre) bajo el contrato {contract_id}"

        with db_transaction.atomic():
            sender.points -= points
            receiver.points += points
            sender.save()
            receiver.save()

            # Crear transacciones
            Transaction.objects.create(
                user=sender,
                amount=points,
                status=1,  # Egreso
                tipo="Internal",
                transaction_status="Completed",
                descripcion=description,
            )

            Transaction.objects.create(
                user=receiver,
                amount=points,
                status=0,  # Ingreso
                tipo="Internal",
                transaction_status="Completed",
                descripcion=description,
            )

            notification_title = "Transferencia de puntos recibida"
            notification_body = f"El usuario {sender.username} te acaba de transferir {points} puntos exitosamente."

            # Crear notificación local en la base de datos
            UserNotificationService.create_notification(
                receiver, notification_title, notification_body
            )

            # Buscar dispositivo FCM del receptor y enviar notificación push
            device = receiver.fcmdevice_set.first()
            if device and device.registration_id:
                FirebaseNotificationService.send_firebase_notification(
                    device.registration_id,
                    notification_title,
                    notification_body,
                    data=None,
                )

            # Notificación para el remitente
            sender_notification_title = "Transferencia de puntos realizada exitosamente"
            sender_notification_body = f"Su transferencia de {points} puntos al usuario {receiver.username} ha sido realizada exitosamente."

            UserNotificationService.create_notification(
                sender, sender_notification_title, sender_notification_body
            )

            device_sender = sender.fcmdevice_set.first()
            if device_sender and device_sender.registration_id:
                FirebaseNotificationService.send_firebase_notification(
                    device_sender.registration_id,
                    sender_notification_title,
                    sender_notification_body,
                    data=None,
                )

        return Response(
            {"message": "Transferencia realizada exitosamente."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="availableusers")
    def get_available_users(self, request):
        user = request.user
        contract_id = request.query_params.get("contract_id")

        if user.father:
            if not contract_id:
                first_contract = (
                    Contract.objects.filter(userprofile=user)
                    .values_list("id", flat=True)
                    .first()
                )
                if not first_contract:
                    return Response(
                        {"error": "El usuario padre no tiene contratos asignados."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                contract_id = first_contract
            else:
                contract = (
                    Contract.objects.filter(userprofile=user, contract_id=contract_id)
                    .values_list("id", flat=True)
                    .first()
                )
                if not contract:
                    return Response(
                        {"error": "El usuario padre no tiene este contrato asignado."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                contract_id = contract

            users = UserProfile.objects.filter(
                contract_id=contract_id, father=False, is_active=True
            )

        else:
            contract = Contract.objects.filter(contract_id=contract_id).first()
            if not contract:
                return Response(
                    {
                        "error": "No se encontró un contrato asignado al padre para este usuario hijo."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            contract_id = contract.id
            print(
                "El contract_id asignado en el bloque user.father=False es:",
                contract_id,
            )

            users = UserProfile.objects.filter(
                id=contract.userprofile_id, father=True, is_active=True
            )

        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="enableusers")
    def get_enable_users(self, request):
        user = request.user
        contract_id = request.query_params.get("contract_id")

        if user.father:
            if not contract_id:
                first_contract = (
                    Contract.objects.filter(userprofile=user)
                    .values_list("id", flat=True)
                    .first()
                )
                if not first_contract:
                    return Response(
                        {"error": "El usuario padre no tiene contratos asignados."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                contract_id = first_contract
            else:
                contract = (
                    Contract.objects.filter(userprofile=user, contract_id=contract_id)
                    .values_list("id", flat=True)
                    .first()
                )
                if not contract:
                    return Response(
                        {"error": "El usuario padre no tiene este contrato asignado."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                contract_id = contract

            users = UserProfile.objects.filter(
                contract_id=contract_id, father=False, is_active=True
            )

        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="disableusers")
    def get_disenable_users(self, request):
        user = request.user
        contract_id = request.query_params.get("contract_id")

        if user.father:
            if not contract_id:
                first_contract = (
                    Contract.objects.filter(userprofile=user)
                    .values_list("id", flat=True)
                    .first()
                )
                if not first_contract:
                    return Response(
                        {"error": "El usuario padre no tiene contratos asignados."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                contract_id = first_contract
            else:
                contract = (
                    Contract.objects.filter(userprofile=user, contract_id=contract_id)
                    .values_list("id", flat=True)
                    .first()
                )
                if not contract:
                    return Response(
                        {"error": "El usuario padre no tiene este contrato asignado."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                contract_id = contract

            users = UserProfile.objects.filter(
                contract_id=contract_id, father=False, is_active=False
            )

        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SupportRatingViewSet(viewsets.ViewSet):
    @action(detail=True, methods=["get"], url_path="questions")
    def get_rating_questions(self, request, pk=None):
        support = get_object_or_404(Support, support_id=pk)
        if support.is_rated:
            questions = RatingQuestion.objects.filter(is_active=True)
            questions_data = []

            for question in questions:
                rating = TicketRating.objects.filter(
                    ticket=support, question=question
                ).first()

                question_data = {
                    "id": question.id,
                    "question": question.question,
                    "order": question.order,
                    "rating": rating.rating if rating else None,
                }
                questions_data.append(question_data)

            return Response(
                {
                    "is_rated": True,
                    "final_comment": support.final_comment or "",
                    "questions": questions_data,
                }
            )

        questions = RatingQuestion.objects.filter(is_active=True)
        serializer = RatingQuestionSerializer(questions, many=True)
        return Response({"is_rated": False, "questions": serializer.data})

    @action(detail=True, methods=["post"], url_path="submit-ratings")
    def submit_ratings(self, request, pk=None):
        support = get_object_or_404(Support, support_id=pk)
        if support.is_rated:
            return Response(
                {"error": "Este soporte ya ha sido calificado"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SupportRatingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            for rating_data in serializer.validated_data["ratings"]:
                TicketRating.objects.create(
                    ticket=support,
                    question=rating_data["question"],
                    rating=rating_data["rating"],
                )
            if "final_comment" in serializer.validated_data:
                support.final_comment = serializer.validated_data["final_comment"]
            support.is_rated = True
            support.save()

            return Response(
                {"message": "Calificaciones guardadas exitosamente"},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": "Error al guardar las calificaciones", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class TransactionRollbackAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = TransactionRollbackSerializer(data=request.data)
        if serializer.is_valid():
            reverse_transaction = serializer.rollback()
            return Response(
                {
                    "message": "Rollback realizado con éxito.",
                    "original_transaction": serializer.data,
                    "reverse_transaction": TransactionSerializer(
                        reverse_transaction
                    ).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteAccountViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = DeleteAccountSerializers(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data.get("id")
            try:
                user = UserProfile.objects.get(id=user_id)
                user.is_active = False
                user.save()
                return Response(
                    {"message": "Usuario desactivado correctamente"},
                    status=status.HTTP_200_OK,
                )
            except (UserProfile.DoesNotExist, ValidationError):
                return Response(
                    {"error": "El usuario no existe o el ID no es válido"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="enable")
    def enable_user(self, request):
        serializer = DeleteAccountSerializers(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data.get("id")
            try:
                user = UserProfile.objects.get(id=user_id)

                # Validar si el usuario tiene un contrato asignado
                if not user.contract:
                    return Response(
                        {"error": "El usuario no tiene un contrato asignado."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                contract = user.contract

                # Contar el número de usuarios activos en este contrato
                active_users_count = UserProfile.objects.filter(
                    contract=contract, is_active=True, father=False
                ).count()

                # Verificar si el contrato ya alcanzó el límite
                if active_users_count >= contract.user_limit:
                    return Response(
                        {
                            "error": "Se ha alcanzado el límite de usuarios habilitados, te sugerimos contratar un plan superior para añadir más usuarios."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                user.is_active = True
                user.save()
                return Response(
                    {"message": "Usuario activado correctamente"},
                    status=status.HTTP_200_OK,
                )
            except (UserProfile.DoesNotExist, ValidationError):
                return Response(
                    {"error": "El usuario no existe o el ID no es válido"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["delete"], url_path="delete")
    def delete_user(self, request):
        serializer = DeleteAccountSerializers(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data.get("id")
            try:
                user = UserProfile.objects.get(id=user_id)
                user.delete()
                return Response(
                    {"message": "Usuario eliminado permanentemente"},
                    status=status.HTTP_200_OK,
                )
            except (UserProfile.DoesNotExist, ValidationError):
                return Response(
                    {"error": "El usuario no existe o el ID no es válido"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentPromiseApiView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = PaymentPromiseSerializer(data=request.data)
        if serializer.is_valid():
            odoo_url = DynamicContent.objects.filter(
                key="odoo_url_create_payment_promise"
            ).first()
            if not odoo_url:
                return Response(
                    {"error": "URL de Odoo no encontrada"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            result = []
            # Formatear la fecha de yyyy-mm-dd a dd-mm-yyyy
            end_date = serializer.data["end_date"]
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            end_date = end_date.strftime("%d/%m/%Y")
            data = {
                "contract": serializer.data["contract"],
                "end_date": end_date,
            }
            try:
                response = requests.post(odoo_url.text, json=data)
                if response.status_code == 200:
                    result = response.json()
                if response.status_code == 400:
                    result = response.json()
            except requests.exceptions.RequestException as e:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MassPointsLoadView(APIView):
    def post(self, request):
        serializer = MassPointsLoadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mass_points_load = serializer.save()

        cat_name = mass_points_load.category.name

        if cat_name == "ANTIGUEDAD":
            mass_points_load.process_antiquity_points()
        elif cat_name == "COMPRA DE PRODUCTOS":
            mass_points_load.process_buy_products()
        else:
            mass_points_load.process_points()

        return Response(
            {"message": "Registro creado y procesado correctamente!"},
            status=status.HTTP_201_CREATED,
        )


#Clases extra
class SendMailRegisteredUserViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'], url_path='send_email')
    def send_email(self, request):
        serializer = SendMailRegisteredUserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.send_email()
            return Response({"message": "Email enviado correctamente!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
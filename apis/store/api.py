from django.utils import timezone
from fcm_django.models import FCMDevice
from rest_framework import viewsets, status
from apis.store.serialize import (
    StoreSerializer,
    ProductSerializer,
    AdminPromotionSerializer,
    StorePromotionSerializer,
    StoreUserSerializer,
    HistoricalClaimPromotionHistorySerializer,
    UserClaimHistorySerializer,
    HistoricalClaimProductHistorySerializer,
)
from apps.clients.models import (
    Transaction,
    UserProfile,
    PointsCategory,
    PointsByPlanCategory,
)
from apps.notifications.services import (
    UserNotificationService,
    FirebaseNotificationService,
)
from apps.store.models import (
    Store,
    Promotion,
    Product,
    UserClaimHistory,
    StoreUser,
    HistoricalClaimPromotionHistory,
    HistoricalClaimProductHistory,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import BasePermission
from datetime import datetime
from django.utils.dateparse import parse_date
from django.db.models import Count
from django.db.utils import IntegrityError
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.test import APIRequestFactory
from django.db import transaction as db_transaction
from django.contrib.auth.models import Group
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import now, make_aware, localtime
from auditlog.models import LogEntry


class IsStoreUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name="Tiendas").exists()

    def has_object_permission(self, request, view, obj):
        # Permitir acceso solo a promociones de la tienda del usuario
        store_user = request.user.store_users.first()
        return obj.store == store_user.store


class StoreUsersByStoreView(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StoreUserSerializer
    queryset = Store.objects.all()

    def perform_update(self, serializer):
        instance = serializer.save()

        from auditlog.models import LogEntry

        LogEntry.objects.filter(
            object_id=instance.id, action=LogEntry.Action.UPDATE
        ).update(actor=self.request.user)

    @action(detail=True, methods=["delete"], url_path="deleteusers")
    def delete_users_by_store(self, request, pk=None):
        user_ids = request.data.get("user_ids", [])
        if not user_ids:
            return Response(
                {"error": "Debe proporcionar una lista de IDs de usuarios a eliminar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar la tienda
        store = get_object_or_404(Store, pk=pk)

        # Filtrar los usuarios que pertenecen a la tienda y están en la lista de IDs proporcionada
        users_to_delete = StoreUser.objects.filter(store=store, user_id__in=user_ids)

        if not users_to_delete.exists():
            return Response(
                {
                    "error": "No se encontraron usuarios en la tienda con los IDs proporcionados."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Obtener los IDs de los usuarios a eliminar
        user_ids_to_delete = list(users_to_delete.values_list("user_id", flat=True))

        # Eliminar las relaciones de StoreUser
        deleted_count, _ = users_to_delete.delete()

        # Verificar si los usuarios ya no están en otras tiendas
        remaining_users = StoreUser.objects.filter(
            user_id__in=user_ids_to_delete
        ).values_list("user_id", flat=True)

        # Identificar los usuarios que ya no están asociados a ninguna tienda
        users_to_remove = set(user_ids_to_delete) - set(remaining_users)

        # Eliminar de UserProfile solo aquellos que ya no pertenecen a ninguna tienda
        UserProfile.objects.filter(id__in=users_to_remove).delete()

        return Response(
            {
                "message": f"Se eliminaron {deleted_count} usuarios de la tienda y {len(users_to_remove)} usuarios del sistema."
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="activechildusers")
    def get_active_non_father_users_by_store(self, request, pk=None):
        """
        Obtener usuarios de una tienda que no son usuarios principales (fatherstore=False) y están activados.
        """
        try:
            store_users = StoreUser.objects.filter(
                store_id=pk, user__fatherstore=False, user__is_active=True
            )
            if not store_users.exists():
                return Response(
                    {"error": "La tienda asociada no tiene usuarios hijos activos."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = StoreUserSerializer(store_users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="inactivechildusers")
    def get_inactive_non_father_users_by_store(self, request, pk=None):
        """
        Obtener usuarios de una tienda que no son usuarios principales (fatherstore=False) y están desactivados.
        """
        try:
            store_users = StoreUser.objects.filter(
                store_id=pk, user__fatherstore=False, user__is_active=False
            )
            if not store_users.exists():
                return Response(
                    {
                        "error": "La tienda asociada no tiene usuarios hijos desactivados."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = StoreUserSerializer(store_users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="users")
    def get_users_by_store(self, request, pk=None):
        try:
            fatherstore_param = request.query_params.get("fatherstore", None)

            filters = {"store_id": pk}

            if fatherstore_param is not None:
                if fatherstore_param.lower() in ["true", "1"]:
                    filters["user__fatherstore"] = True
                elif fatherstore_param.lower() in ["false", "0"]:
                    filters["user__fatherstore"] = False
                else:
                    return Response(
                        {
                            "error": "El parámetro 'fatherstore' debe ser 'true' o 'false'."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Aplicar el filtro
            store_users = StoreUser.objects.filter(**filters)

            if not store_users.exists():
                return Response(
                    {"error": "No se encontraron usuarios asociados a esta tienda."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Serializar los datos
            serializer = StoreUserSerializer(store_users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="countsonusers")
    def count_users_by_store(self, request, pk=None):
        try:
            # Contar los usuarios que tienen fatherstore=False en la tienda especificada
            user_count = StoreUser.objects.filter(
                store_id=pk, user__fatherstore=False
            ).count()

            # Devolver el contador en la respuesta
            return Response({"user_count": user_count}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="store")
    def get_user_store(self, request):
        try:
            # Obtener el StoreUser relacionado con el usuario autenticado
            store_user = (
                StoreUser.objects.filter(user=request.user)
                .select_related("store")
                .first()
            )
            if not store_user:
                return Response(
                    {"error": "El usuario no tiene una tienda asociada."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Serializar la tienda
            serializer = StoreSerializer(store_user.store)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False,
        methods=["post"],
        url_path="register",
        permission_classes=[AllowAny],
    )
    def register_user_to_store(self, request):
        store_id = request.data.get("store_id")
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not store_id or not username or not email or not password:
            return Response(
                {"error": "store_id, username, email y password son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Verificar que la tienda existe
            store = Store.objects.get(pk=store_id)

            with db_transaction.atomic():
                # Verificar si es el primer usuario asociado a la tienda
                is_father = not StoreUser.objects.filter(store=store).exists()

                # Crear el usuario
                user = UserProfile.objects.create_user(
                    username=username.lower(),
                    email=email.lower(),
                    password=password,
                    father=is_father,
                    is_staff=True,
                )

                # Asociar el usuario al grupo "Tiendas"
                group, created = Group.objects.get_or_create(name="Tiendas")
                user.groups.add(group)

                # Asociar el usuario a la tienda
                StoreUser.objects.create(user=user, store=store)

                return Response(
                    {
                        "message": "Usuario registrado exitosamente.",
                        "is_father": is_father,
                        "is_staff": user.is_staff,
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Store.DoesNotExist:
            return Response(
                {"error": "La tienda especificada no existe."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="registerchild",
        permission_classes=[AllowAny],
    )
    def register_child_user_to_store(self, request, pk=None):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not email or not password:
            return Response(
                {"error": "username, email y password son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Obtener la tienda desde la URL (pk = store_id)
            store = Store.objects.get(pk=pk)

            with db_transaction.atomic():
                # Verificar si hay al menos un usuario padre en la tienda antes de permitir hijos
                parent_users = StoreUser.objects.filter(
                    store=store, user__fatherstore=True
                )

                if not parent_users.exists():
                    return Response(
                        {
                            "error": "Debe haber al menos un usuario padre en la tienda antes de registrar usuarios hijos."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Crear el usuario hijo con is_staff=True y fatherstore=False
                user = UserProfile.objects.create_user(
                    username=username.lower(),
                    email=email.lower(),
                    password=password,
                    fatherstore=False,
                    is_staff=True,
                )

                # Asociar el usuario al grupo "Tiendas"
                group, created = Group.objects.get_or_create(name="Tiendas")
                user.groups.add(group)

                # Asociar el usuario a la tienda automáticamente
                StoreUser.objects.create(user=user, store=store)

                # Enviar notificación a los usuarios padre de la tienda
                for parent_user in parent_users:
                    # Crear una notificación local en la base de datos
                    UserNotificationService.create_notification(
                        parent_user.user,
                        "Nuevo usuario hijo registrado",
                        f"El usuario {user.first_name or user.username} se ha registrado exitosamente en la tienda {store.name}.",
                    )

                    # Buscar dispositivo FCM del usuario padre
                    parent_device = FCMDevice.objects.filter(
                        user=parent_user.user
                    ).first()

                    if parent_device and parent_device.registration_id:
                        # Enviar notificación push con Firebase
                        FirebaseNotificationService.send_firebase_notification(
                            parent_device.registration_id,
                            "Nuevo usuario hijo registrado",
                            f"El usuario {user.first_name or user.username} se ha registrado exitosamente en la tienda {store.name}.",
                            data=None,
                        )

                return Response(
                    {
                        "message": "Usuario hijo registrado exitosamente en la tienda.",
                        "store_id": store.id,
                        "store_name": store.name,
                        "is_father": user.fatherstore,
                        "is_staff": user.is_staff,
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Store.DoesNotExist:
            return Response(
                {"error": "La tienda especificada no existe."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except IntegrityError as e:
            error_message = str(e)
            if "clients_userprofile_username_key" in error_message:
                return Response(
                    {
                        "error": "El nombre de usuario ya está en uso. Por favor, elige otro."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif "clients_userprofile_email" in error_message:
                return Response(
                    {
                        "error": "El correo electrónico ya está en uso. Por favor, usa otro."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                return Response(
                    {"error": "Ocurrió un error inesperado al registrar el usuario."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error inesperado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["patch"], url_path="enableuser")
    def activate_user(self, request):
        """
        Activa un usuario de la tienda (is_active=True).
        """
        user_id = request.data.get("user_id")
        user = get_object_or_404(UserProfile, pk=user_id)
        if user.is_active:
            return Response(
                {"message": "El usuario ya está activo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save()
        return Response(
            {"message": "Usuario activado correctamente."}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["patch"], url_path="disableuser")
    def deactivate_user(self, request):
        """
        Desactiva un usuario de la tienda (is_active=False).
        """
        user_id = request.data.get("user_id")
        user = get_object_or_404(UserProfile, pk=user_id)
        if not user.is_active:
            return Response(
                {"message": "El usuario ya está desactivado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.save()
        return Response(
            {"message": "Usuario desactivado correctamente."}, status=status.HTTP_200_OK
        )


class UserClaimHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserClaimHistorySerializer

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        if user_id:
            return UserClaimHistory.objects.filter(user_id=user_id)
        return UserClaimHistory.objects.none()


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class PromotionViewSet(ModelViewSet):
    queryset = Promotion.objects.filter(
        is_enabled=True,
        start_datetime__lte=timezone.now(),
        end_datetime__gte=timezone.now(),
    )
    permission_classes = [IsAuthenticated]
    serializer_class = StorePromotionSerializer
    pagination_class = CustomPagination

    def perform_update(self, serializer):
        instance = serializer.save()

        from auditlog.models import LogEntry

        LogEntry.objects.filter(
            object_id=instance.id, action=LogEntry.Action.UPDATE
        ).update(actor=self.request.user)

    def get_queryset(self):
        """
        Filtra las promociones y carga el nombre de la tienda correctamente.
        """
        queryset = Promotion.objects.select_related("store").all()

        # Obtener parámetros de la URL
        store_id = self.request.query_params.get("store_id", None)
        store_name = self.request.query_params.get("store_name", None)
        authorize_promotion = self.request.query_params.get("authorize_promotion", None)
        is_enabled = self.request.query_params.get("is_enabled", None)
        title = self.request.query_params.get("title", None)

        # Aplicar filtros dinámicos
        if store_id:
            queryset = queryset.filter(store__id=store_id)
        if store_name:
            queryset = queryset.filter(store__name__icontains=store_name)
        if authorize_promotion:
            queryset = queryset.filter(authorize_promotion=authorize_promotion)
        if is_enabled is not None:
            queryset = queryset.filter(is_enabled=is_enabled.lower() in ["true", "1"])
        if title:
            queryset = queryset.filter(title__icontains=title)

        return queryset

    def get_serializer_class(self):
        if self.request.user.is_superuser:
            return AdminPromotionSerializer
        return StorePromotionSerializer

    from django.db import transaction as db_transaction

    @action(detail=True, methods=["post"], url_path="claim")
    def claim_promotion(self, request, pk=None):
        promotion = self.get_object()
        user = request.user

        if not promotion.is_enabled:
            return Response({"error": "Promoción no habilitada."}, status=400)

        if promotion.start_datetime and promotion.start_datetime > now():
            return Response({"error": "Promoción aún no disponible."}, status=400)

        if promotion.end_datetime and promotion.end_datetime < now():
            return Response({"error": "Promoción expirada."}, status=400)

        # Validar stock de la promoción (excepto ilimitadas)
        if promotion.vouchers_promotion == 0:
            return Response({"error": "No hay vouchers disponibles."}, status=400)

        claim_history, created = UserClaimHistory.objects.get_or_create(
            user=user, promotion=promotion
        )

        if (
            promotion.max_claims_per_user is not None
            and claim_history.claims_count is not None
        ):
            if (
                promotion.max_claims_per_user != -1
                and claim_history.claims_count >= promotion.max_claims_per_user
            ):
                return Response(
                    {
                        "error": "Ya has alcanzado el límite de reclamos para esta promoción."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with db_transaction.atomic():
            if promotion.points_required > user.points:
                return Response(
                    {
                        "error": "El usuario no tiene suficientes puntos para esta transacción."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            transaction = Transaction.objects.create(
                user=user,
                amount=promotion.points_required,
                status=1,
                tipo="Promotion",
                transaction_status="Pending",
                codigo_promocion=promotion,
                descripcion=f"Reclamo de promoción: {promotion.title}",
            )

            claim_history.claims_count += 1
            claim_history.save()
            # obtener la tienda de promocion
            store = promotion.store
            # obtener los usuarios de la tienda
            store_users = StoreUser.objects.filter(store=store)
            # crear las notifiacicacion locales
            for store_user in store_users:
                user_device = FCMDevice.objects.filter(user=store_user.user).first()
                UserNotificationService.create_notification(
                    store_user.user,
                    "Promoción reclamada",
                    f"El usuario {user.first_name or user.username} reclamó la promoción {promotion.title}",
                )
                if user_device and user_device.registration_id:
                    FirebaseNotificationService.send_firebase_notification(
                        user_device.registration_id,
                        "Promoción reclamada",
                        f"El usuario {user.first_name or user.username} reclamó la promoción {promotion.title}",
                        data=None,
                    )
        return Response(
            {
                "message": "Promoción reclamada exitosamente.",
                "transaction": transaction.pk,
                "claim_code": transaction.claim_code,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="countpromotions")
    def count_store_promotions(self, request):
        """
        Devuelve el número total de promociones creadas por la tienda del usuario autenticado.
        """
        try:
            # Obtener la tienda del usuario
            store_user = StoreUser.objects.filter(user=request.user).first()

            if not store_user:
                return Response(
                    {"error": "El usuario no tiene una tienda asociada."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Contar las promociones de la tienda
            promotion_count = Promotion.objects.filter(store=store_user.store).count()

            return Response(
                {"promotion_count": promotion_count}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["patch"], url_path="validateclaim")
    def validate_claim(self, request):
        new_status = request.data.get("status")
        claim_code = request.data.get("claim_code")

        if not claim_code:
            return Response(
                {"error": "El campo 'claim_code' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status not in ["approved", "disapproved"]:
            return Response(
                {"error": "El campo 'status' debe ser 'approved' o 'disapproved'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction = Transaction.objects.get(claim_code=claim_code)
            claimant_user = transaction.user
            promotion = transaction.codigo_promocion
            store = promotion.store if promotion else None
        except Transaction.DoesNotExist:
            return Response(
                {"error": "Código de reclamo no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with db_transaction.atomic():
            try:
                user = request.user

                if new_status == "approved":
                    transaction.transaction_status = "Completed"
                    transaction.validated_by = user
                    transaction.save(is_validation=True)

                    promotion_name = (
                        promotion.title if promotion else "Promoción desconocida"
                    )
                    store_name = store.name if store else "Tienda desconocida"

                    # Crear una notificación local
                    UserNotificationService.create_notification(
                        claimant_user,
                        "¡Tu reclamo ha sido aprobado!",
                        f"Tu reclamo de la promoción {promotion_name} de {store_name} ha sido aprobado.",
                    )

                    # Enviar notificación push con Firebase si el usuario tiene un dispositivo FCM registrado
                    claimant_device = FCMDevice.objects.filter(
                        user=claimant_user
                    ).first()
                    if claimant_device and claimant_device.registration_id:
                        FirebaseNotificationService.send_firebase_notification(
                            claimant_device.registration_id,
                            "¡Tu reclamo ha sido aprobado!",
                            f"Tu reclamo de la promoción {promotion_name} de {store_name} ha sido aprobado.",
                            data=None,
                        )
                    promotion_category = PointsCategory.objects.filter(
                        name="USO DE PROMOCIONES ASOCIADOS", enabled=True
                    ).first()

                    if promotion_category:
                        if claimant_user.father:
                            user_contract = claimant_user.usercontract.first()
                        else:
                            user_contract = claimant_user.contract
                        if user_contract and user_contract.planInternet:

                            point_config = PointsByPlanCategory.objects.filter(
                                category=promotion_category,
                                plan=user_contract.planInternet,
                            ).first()

                        if point_config:
                            # Asignar los puntos encontrados en la configuración
                            points_to_assign = point_config.points

                            # Asignar los puntos
                            claimant_user.points += points_to_assign
                            claimant_user.save()

                            # Crear la transacción de puntos por promoción
                            Transaction.objects.create(
                                user=claimant_user,
                                amount=points_to_assign,
                                status=0,
                                tipo="Internal",
                                transaction_status="Completed",
                                saldo=claimant_user.points,
                                descripcion=f"Puntos asignados por promoción: {promotion_name}",
                            )

                            # Crear notificación para el usuario
                            UserNotificationService.create_notification(
                                claimant_user,
                                "Puntos acreditados por promoción",
                                f"Se te han asignado {points_to_assign} puntos por promoción: {promotion_name}.",
                            )

                            # Enviar notificación push si tiene un dispositivo FCM registrado
                            claimant_device = FCMDevice.objects.filter(
                                user=claimant_user
                            ).first()
                            if claimant_device and claimant_device.registration_id:
                                FirebaseNotificationService.send_firebase_notification(
                                    claimant_device.registration_id,
                                    "Puntos acreditados por promoción",
                                    f"Se te han asignado {points_to_assign} puntos por promoción: {promotion_name}.",
                                    data=None,
                                )

                        else:
                            print(
                                f"⚠️ No se encontró configuración de puntos para el plan {user_contract.planInternet.name}."
                            )
                            return Response(
                                {
                                    "error": "No se encontró configuración de puntos para el plan de Internet."
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                    return Response(
                        {
                            "message": "Reclamo de promoción aprobado exitosamente.",
                            "claim_code": transaction.claim_code,
                            "transaction_status": transaction.transaction_status,
                        },
                        status=status.HTTP_200_OK,
                    )

                elif new_status == "disapproved":
                    transaction.transaction_status = "Cancelled"
                    transaction.validated_by = user
                    transaction.save(is_validation=True)

                    promotion_name = (
                        promotion.title if promotion else "Promoción desconocida"
                    )
                    store_name = store.name if store else "Tienda desconocida"

                    # Crear una notificación local
                    UserNotificationService.create_notification(
                        claimant_user,
                        "Tu reclamo ha sido rechazado",
                        f"Lamentamos informarte que tu reclamo de la promoción {promotion_name} de {store_name} ha sido rechazado.",
                    )

                    # Enviar notificación push con Firebase si el usuario tiene un dispositivo FCM registrado
                    claimant_device = FCMDevice.objects.filter(
                        user=claimant_user
                    ).first()
                    if claimant_device and claimant_device.registration_id:
                        FirebaseNotificationService.send_firebase_notification(
                            claimant_device.registration_id,
                            "Tu reclamo ha sido rechazado",
                            f"Lamentamos informarte que tu reclamo de la promoción {promotion_name} de {store_name} ha sido rechazado.",
                            data=None,
                        )

                    return Response(
                        {
                            "message": "Reclamo de promoción rechazado exitosamente.",
                            "claim_code": transaction.claim_code,
                            "transaction_status": transaction.transaction_status,
                        },
                        status=status.HTTP_200_OK,
                    )

            except Exception as e:
                return Response(
                    {"error": f"Error procesando el reclamo: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    @action(detail=False, methods=["get"], url_path="claimdetails")
    def get_claim_details(self, request):
        claim_code = request.query_params.get("claim_code", "").strip()

        if not claim_code:
            return Response(
                {"error": "Debe proporcionar un 'claim_code'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar transacciones que contengan el código ingresado y limitarlo a 5 resultados
        transactions = (
            Transaction.objects.filter(claim_code__icontains=claim_code)
            .select_related("user", "codigo_promocion", "validated_by")
            .order_by("-date")[:5]
        )

        if not transactions.exists():
            return Response(
                {"error": "Código de reclamo no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        results = []
        for transaction in transactions:
            usuario = transaction.user
            promocion = transaction.codigo_promocion
            validador = transaction.validated_by

            usuario_data = {
                "id": usuario.id,
                "nombre_usuario": usuario.username,
                "nombre_completo": usuario.get_full_name(),
                "email": usuario.email,
                "celular": usuario.cellphone,
                "puntos": usuario.points,
                "imagen_perfil": (
                    request.build_absolute_uri(usuario.image_field.url)
                    if usuario.image_field
                    else None
                ),
            }

            promocion_data = {
                "titulo": promocion.title if promocion else "Promoción no encontrada",
                "codigo_promocion": promocion.id if promocion else None,
                "imagen": (
                    request.build_absolute_uri(promocion.image_field.url)
                    if promocion and promocion.image_field
                    else None
                ),
            }

            results.append(
                {
                    "usuario": usuario_data,
                    "promocion": promocion_data,
                    "claim_code": transaction.claim_code,
                    "fecha_reclamo": transaction.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "estado": transaction.transaction_status,
                    "puntos_usados": transaction.amount,
                    "validated_by": validador.username if validador else "-",
                }
            )

        return Response(results, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="allstorepromotions")
    def list_all_store_promotions(self, request):
        """
        API para listar TODAS las promociones de la tienda del usuario autenticado.
        """
        user = request.user

        store_user = StoreUser.objects.filter(user=user).first()
        if not store_user:
            return Response(
                {"error": "El usuario no tiene una tienda asociada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Obtener todas las promociones de la tienda del usuario
        queryset = Promotion.objects.filter(store=store_user.store).order_by(
            "-start_datetime"
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = StorePromotionSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        # Si no hay paginación, devolver todos los datos
        serializer = StorePromotionSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="all")
    def list_all_promotions(self, request):
        promotion_id = request.query_params.get("id")
        store_id = request.query_params.get("store_id")
        date = request.query_params.get("date")

        # Obtener la fecha actual y convertirla a la zona horaria del sistema
        current_time = localtime(now())

        # Si se proporciona un ID de promoción, verificar si está activa
        if promotion_id:
            try:
                promotion = Promotion.objects.get(
                    id=promotion_id,
                    is_enabled=True,
                    authorize_promotion="Authorized",
                    end_datetime__gte=current_time,
                    start_datetime__lte=current_time,
                )
                serializer = StorePromotionSerializer(
                    promotion, context={"request": request}
                )
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Promotion.DoesNotExist:
                return Response(
                    {"error": "Promoción no encontrada o no cumple con los criterios."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Construcción del queryset con filtros
        queryset = Promotion.objects.filter(
            is_enabled=True,
            authorize_promotion="Authorized",
            start_datetime__lte=current_time,
            end_datetime__gte=current_time,
        )

        # Filtrar por tienda si se proporciona `store_id`
        if store_id:
            queryset = queryset.filter(store__id=store_id)

        # Filtrar por fecha si se proporciona `date`
        if date:
            try:
                filter_date = datetime.strptime(date, "%Y-%m-%d")
                queryset = queryset.filter(
                    Q(start_datetime__lte=filter_date)
                    & Q(end_datetime__gte=filter_date)
                )
            except ValueError:
                return Response(
                    {"error": "Formato de fecha incorrecto, usa YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Serializar y devolver el resultado
        serializer = StorePromotionSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        store_user = request.user.store_users.first()
        if not store_user:
            return Response(
                {"error": "El usuario no tiene una tienda asociada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()
        data["store"] = store_user.store.id
        data["authorize_promotion"] = "Pending"
        data["is_enabled"] = False

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="authorizestatus")
    def authorize_status(self, request, pk=None):
        """
        Acción personalizada para autorizar o rechazar promociones.
        """
        promotion = self.get_object()
        new_status = request.data.get("authorize_promotion")

        # Validar el estado
        if new_status not in ["Authorized", "Rejected"]:
            return Response(
                {"error": "El estado debe ser 'Authorized' o 'Rejected'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Actualizar el estado de autorización
        promotion.authorize_promotion = new_status
        promotion.save()

        return Response(
            {
                "message": f"Promoción {new_status.lower()} correctamente.",
                "promotion": {
                    "id": promotion.id,
                    "title": promotion.title,
                    "authorize_promotion": promotion.authorize_promotion,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="listbydate")
    def list_by_date(self, request):
        """
        Listar promociones creadas en una fecha específica (formato DD-MM-YYYY).
        """
        date_param = request.query_params.get("date")
        if not date_param:
            return Response(
                {"error": "El parámetro 'date' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Convertir la fecha proporcionada al formato correcto (DD-MM-YYYY)
            date = datetime.strptime(date_param, "%d-%m-%Y").date()
        except ValueError:
            return Response(
                {"error": "El formato de la fecha debe ser 'DD-MM-YYYY'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Filtrar promociones por la fecha de creación (created_up__date)
        promotions = Promotion.objects.filter(created_up__date=date)

        # Serializar las promociones
        serializer = self.get_serializer(promotions, many=True)
        return Response(serializer.data, status=200)

    @action(detail=False, methods=["get"], url_path="listbyrange")
    def list_by_range(self, request):
        """
        Listar promociones activas para un rango de fechas (formato DD-MM-YYYY).
        """
        start_date_param = request.query_params.get("start_date")
        end_date_param = request.query_params.get("end_date")

        if not start_date_param or not end_date_param:
            return Response(
                {"error": "Los parámetros 'start_date' y 'end_date' son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Convertir las fechas proporcionadas al formato correcto (DD-MM-YYYY)
            start_date = datetime.strptime(start_date_param, "%d-%m-%Y").date()
            end_date = datetime.strptime(end_date_param, "%d-%m-%Y").date()
        except ValueError:
            return Response(
                {"error": "El formato de las fechas debe ser 'DD-MM-YYYY'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if start_date > end_date:
            return Response(
                {"error": "La fecha 'start_date' no puede ser mayor que 'end_date'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Filtrar promociones activas dentro del rango de fechas
        promotions = Promotion.objects.filter(
            start_datetime__date__gte=start_date,
            end_datetime__date__lte=end_date,
            is_enabled=True,
        )

        # Serializar las promociones
        serializer = self.get_serializer(promotions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    from django.db import transaction as db_transaction

    def perform_update(self, serializer):
        instance = serializer.save()

        from auditlog.models import LogEntry

        LogEntry.objects.filter(
            object_id=instance.id, action=LogEntry.Action.UPDATE
        ).update(actor=self.request.user)

    @action(detail=True, methods=["post"], url_path="claim")
    def claim_product(self, request, pk=None):
        product = self.get_object()
        user = request.user

        # Validar si el usuario ya alcanzó el límite de reclamos
        claim_history, created = UserClaimHistory.objects.get_or_create(
            user=user, product=product
        )
        if claim_history.claims_count >= (product.max_claims_per_user or 0):
            return Response(
                {"error": "Ya has alcanzado el límite de reclamos para este producto."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Manejo transaccional para garantizar consistencia
        with db_transaction.atomic():
            if product.points_required > user.points:
                return Response(
                    {
                        "error": "El usuario no tiene suficientes puntos para esta transacción."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            transaction = Transaction.objects.create(
                user=user,
                amount=product.points_required,
                status=1,
                tipo="Product",
                transaction_status="Pending",
                codigo_producto=product,
                descripcion=f"Reclamo de producto: {product.title}",
            )

            claim_history.claims_count += 1
            claim_history.save()

        # Responder con éxito
        return Response(
            {
                "message": "Producto reclamado exitosamente.",
                "transaction": transaction.pk,
                "claim_code": transaction.claim_code,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], url_path="validateclaim")
    def validate_claim(self, request):
        new_status = request.data.get("status")
        claim_code = request.data.get("claim_code")

        if not claim_code:
            return Response(
                {"error": "El campo 'claim_code' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status not in ["approved", "disapproved"]:
            return Response(
                {"error": "El campo 'status' debe ser 'approved' o 'disapproved'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction = Transaction.objects.get(claim_code=claim_code)
            claimant_user = transaction.user
            producto = transaction.codigo_producto
        except Transaction.DoesNotExist:
            return Response(
                {"error": "Código de reclamo no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with db_transaction.atomic():
            try:
                user = request.user
                product_name = producto.title if producto else "Producto desconocida"
                if new_status == "approved":
                    transaction.transaction_status = "Completed"
                    transaction.validated_by = user
                    transaction.save(is_validation=True)

                    UserNotificationService.create_notification(
                        claimant_user,
                        "¡Tu reclamo ha sido aprobado!",
                        f"Tu reclamo del producto {product_name} ha sido aprobado.",
                    )

                    # Notificación push
                    claimant_device = FCMDevice.objects.filter(
                        user=claimant_user
                    ).first()
                    if claimant_device and claimant_device.registration_id:
                        FirebaseNotificationService.send_firebase_notification(
                            claimant_device.registration_id,
                            "¡Tu reclamo ha sido aprobado!",
                            f"Tu reclamo del producto {product_name} ha sido aprobado.",
                            data=None,
                        )
                    return Response(
                        {
                            "message": "Reclamo de producto aprobado exitosamente.",
                            "claim_code": transaction.claim_code,
                            "transaction_status": transaction.transaction_status,
                        },
                        status=status.HTTP_200_OK,
                    )

                elif new_status == "disapproved":
                    transaction.transaction_status = "Cancelled"
                    transaction.validated_by = user
                    transaction.save(is_validation=True)

                    # Notificación local
                    UserNotificationService.create_notification(
                        claimant_user,
                        "Tu reclamo ha sido rechazado",
                        f"Lamentamos informarte que tu reclamo del producto {product_name} ha sido rechazado.",
                    )

                    # Notificación push
                    claimant_device = FCMDevice.objects.filter(
                        user=claimant_user
                    ).first()
                    if claimant_device and claimant_device.registration_id:
                        FirebaseNotificationService.send_firebase_notification(
                            claimant_device.registration_id,
                            "Tu reclamo ha sido rechazado",
                            f"Lamentamos informarte que tu reclamo del producto {product_name} ha sido rechazado.",
                            data=None,
                        )

                    return Response(
                        {
                            "message": "Reclamo de producto rechazado exitosamente.",
                            "claim_code": transaction.claim_code,
                            "transaction_status": transaction.transaction_status,
                        },
                        status=status.HTTP_200_OK,
                    )

            except Exception as e:
                return Response(
                    {"error": f"Error procesando el reclamo: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    @action(detail=False, methods=["get"], url_path="claimdetails")
    def get_claim_details(self, request):
        claim_code = request.query_params.get("claim_code")
        if not claim_code:
            return Response(
                {"error": "Debe proporcionar un 'claim_code'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction = Transaction.objects.get(claim_code=claim_code)
        except Transaction.DoesNotExist:
            return Response(
                {"error": "Código de reclamo no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Obtener datos completos del usuario
        usuario = transaction.user
        usuario_data = {
            "id": usuario.id,
            "nombre_usuario": usuario.username,
            "nombre_completo": usuario.get_full_name(),
            "email": usuario.email,
            "celular": usuario.cellphone,
            "puntos": usuario.points,
            "imagen_perfil": (
                request.build_absolute_uri(usuario.image_field.url)
                if usuario.image_field
                else None
            ),
            "contrato": usuario.contract.contract_id if usuario.contract else None,
            "direccion": usuario.contract.addressComplete if usuario.contract else None,
        }

        producto = transaction.codigo_producto
        producto_data = {
            "titulo": producto.title if producto else "Producto no encontrado",
            "codigo_producto": producto.id if producto else None,
            "imagen": (
                request.build_absolute_uri(producto.image_field.url)
                if producto and producto.image_field
                else None
            ),
        }

        data = {
            "usuario": usuario_data,
            "producto": producto_data,
            "claim_code": transaction.claim_code,
            "fecha_reclamo": transaction.date.strftime("%Y-%m-%d %H:%M:%S"),
            "estado": transaction.transaction_status,
            "puntos_usados": transaction.amount,
        }

        return Response(data, status=status.HTTP_200_OK)


class Pagination(PageNumberPagination):
    """
    Configuración de la paginación para mostrar 10 resultados por página.
    """

    page_size = 10


class StoreViewSet(ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["name", "telephone", "RUC_number", "email"]
    pagination_class = Pagination

    def create(self, request, *args, **kwargs):
        """
        POST: Registrar tiendas de manera individual o masiva.
        """
        data = request.data

        # Verificar si es una lista (registro masivo) o un objeto (registro individual)
        if isinstance(data, list):
            serializer = self.get_serializer(data=data, many=True)
        else:
            serializer = self.get_serializer(data=data)

        # Validar el serializer y manejar errores explícitamente
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Tiendas registradas exitosamente.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            # Manejar errores de validación y devolver respuesta
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get_queryset(self):
        """
        Permitir filtros adicionales en el listado de tiendas.
        """
        queryset = super().get_queryset()

        # Filtro opcional por estado (is_enabled)
        is_enabled = self.request.query_params.get("is_enabled")
        if is_enabled is not None:
            queryset = queryset.filter(is_enabled=is_enabled.lower() in ["true", "1"])

        return queryset

    def update(self, request, *args, **kwargs):
        """
        PUT: Actualización completa de la tienda.
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        instance = serializer.save()

        from auditlog.models import LogEntry

        LogEntry.objects.filter(
            object_id=instance.id, action=LogEntry.Action.UPDATE
        ).update(actor=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=["patch"], url_path="changestatus")
    def change_status(self, request, pk=None):
        """
        Acción personalizada para cambiar el estado de la tienda.
        """
        try:
            store = self.get_object()
            new_status = request.data.get("is_enabled")

            if new_status is None:
                return Response(
                    {"error": "El campo 'is_enabled' es obligatorio."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            store.is_enabled = bool(new_status)
            store.save()

            return Response(
                {
                    "message": f"Tienda {'habilitada' if store.is_enabled else 'deshabilitada'} correctamente.",
                    "store": {
                        "id": store.id,
                        "name": store.name,
                        "is_enabled": store.is_enabled,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except Store.DoesNotExist:
            return Response(
                {"error": "La tienda no existe."}, status=status.HTTP_404_NOT_FOUND
            )


class RegisterProductView(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ["code_producto", "title", "points_required"]
    pagination_class = Pagination

    def post(self, request):
        """
        POST: Registrar productos de manera individual o masiva.
        """
        data = request.data

        if isinstance(data, list):
            serializer = ProductSerializer(
                data=data, many=True, context={"request": request}
            )
        else:
            serializer = ProductSerializer(data=data, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Productos registrados exitosamente.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    def list(self, request, *args, **kwargs):
        """
        GET: Listar productos con opciones de filtros.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Paginación opcional
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Serializar y devolver los datos
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """
        PUT: Editar todos los datos de un producto existente.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Producto actualizado exitosamente.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    def partial_update(self, request, *args, **kwargs):
        """
        PATCH: Editar parcialmente un producto existente.
        """
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=["patch"], url_path="changestatus")
    def change_status(self, request, pk=None):
        """
        PATCH: Cambiar el estado de habilitación de un producto.
        """
        try:
            product = self.get_object()
            new_status = request.data.get("is_enabled")

            if new_status is None:
                return Response(
                    {"error": "El campo 'is_enabled' es obligatorio."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Cambiar el estado
            product.is_enabled = bool(new_status)
            product.save()

            return Response(
                {
                    "message": f"Producto {'habilitado' if product.is_enabled else 'deshabilitado'} correctamente.",
                    "product": {
                        "id": product.id,
                        "title": product.title,
                        "is_enabled": product.is_enabled,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Product.DoesNotExist:
            return Response(
                {"error": "El producto no existe."}, status=status.HTTP_404_NOT_FOUND
            )


class HistoricalClaimProductHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HistoricalClaimProductHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        product_id = self.request.query_params.get("product_id")
        if product_id:
            return HistoricalClaimProductHistory.objects.filter(
                producto_id=product_id
            ).order_by("-datetime_created")
        return HistoricalClaimProductHistory.objects.none()


class HistoricalClaimPromotionHistoryViewSet(ModelViewSet):
    serializer_class = HistoricalClaimPromotionHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = HistoricalClaimPromotionHistory.objects.all()

        # Filtrar por promoción si se proporciona el parámetro `promotion_id`
        promotion_id = self.request.query_params.get("promotion_id")
        if promotion_id:
            queryset = queryset.filter(promocion_id=promotion_id)

        # Filtrar por estado si se proporciona el parámetro `status`
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Si es superusuario, mostrar todas las promociones
        if self.request.user.is_superuser:
            return queryset

        # Si no es superusuario, filtrar por la tienda del usuario
        store_user = self.request.user.store_users.first()
        if store_user:
            queryset = queryset.filter(store=store_user.store)

        return queryset

    @action(detail=False, methods=["get"], url_path="promotionstatistics")
    def promotion_status_count(self, request):
        """
        Devuelve estadísticas sobre el número de veces que una promoción ha sido reclamada en distintos estados
        dentro de la tienda del usuario autenticado.
        """
        promotion_id = request.query_params.get("promotion_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # Obtener la tienda del usuario autenticado
        store_user = request.user.store_users.first()
        if not store_user:
            return Response(
                {"error": "El usuario no está asociado a ninguna tienda."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Construir el filtro base para la tienda del usuario
        queryset = HistoricalClaimPromotionHistory.objects.filter(
            store=store_user.store
        )

        # Filtrar por promoción si se proporciona un ID
        if promotion_id:
            queryset = queryset.filter(promocion_id=promotion_id)

        # Filtrar por rango de fechas si se proporciona
        if start_date:
            start_date_parsed = parse_date(start_date)
            if not start_date_parsed:
                return Response(
                    {
                        "error": "El formato de 'start_date' es incorrecto. Use YYYY-MM-DD."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(datetime_created__gte=start_date_parsed)

        if end_date:
            end_date_parsed = parse_date(end_date)
            if not end_date_parsed:
                return Response(
                    {
                        "error": "El formato de 'end_date' es incorrecto. Use YYYY-MM-DD."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(datetime_created__lte=end_date_parsed)

        # Contar registros por estado
        status_counts = queryset.values("promocion_id", "status").annotate(
            count=Count("status")
        )

        # Estructurar la respuesta en formato lista
        result = {}
        for entry in status_counts:
            promo_id = entry["promocion_id"]
            if promo_id not in result:
                result[promo_id] = {"promotion_id": promo_id, "stats": []}

            result[promo_id]["stats"].append(
                {"status": entry["status"], "count": entry["count"]}
            )

        # Convertir resultado a lista para compatibilidad con dashboards
        return Response(list(result.values()), status=status.HTTP_200_OK)

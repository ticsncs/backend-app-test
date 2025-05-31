from rest_framework import serializers

from apis.clients.serialize import UserProfileSerializer
from apps.clients.models import UserProfile, Transaction
from apps.store.models import Store, Promotion, Product, UserClaimHistory, StoreUser, HistoricalClaimPromotionHistory, \
    HistoricalClaimProductHistory


class StoreUserSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer()

    class Meta:
        model = StoreUser
        fields = ['id', 'store', 'user']


class UserProfileNoContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'

    def to_representation(self, instance):
        """Sobrescribe la representación para eliminar 'contracts'."""
        data = super().to_representation(instance)
        data.pop('contracts', None)
        return data

class UserClaimHistorySerializer(serializers.ModelSerializer):
    user = UserProfileNoContractSerializer(read_only=True)
    validated_by = serializers.SerializerMethodField()

    class Meta:
        model = UserClaimHistory
        fields = "__all__"

    def get_validated_by(self, obj):
        return obj.transaction.validated_by.username if obj.transaction and obj.transaction.validated_by else "-"


class ProductSerializer(serializers.ModelSerializer):
    image_field = serializers.ImageField(required=False)
    class Meta:
        model = Product
        fields = "__all__"

    def get_image_field(self, obj):
        """ Devuelve la URL absoluta con HTTPS de la imagen del producto """
        request = self.context.get("request")
        if obj.image_field:
            return request.build_absolute_uri(obj.image_field.url).replace("http://", "https://") if request else obj.image_field.url
        return None

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("El stock no puede ser negativo.")
        return value

    def validate(self, data):
        """
        Validar que el usuario no exceda el límite de reclamos permitido.
        """
        user = self.context['request'].user
        product = self.instance

        # Si es una creación, no realizar validaciones relacionadas con reclamos
        if product is None:
            return data

        # Obtener o crear el historial de reclamos para el usuario y el producto
        claim_history, created = UserClaimHistory.objects.get_or_create(
            user=user,
            product=product
        )

        # Verificar si el usuario ya alcanzó el límite de reclamos
        if claim_history.claims_count >= (product.max_claims_per_user or 0):
            raise serializers.ValidationError(
                f"Ya has alcanzado el límite de {product.max_claims_per_user or 0} reclamos para este producto."
            )

        return data

    def validate_code_producto(self, value):
        """
        Validar que el código de producto sea único, excepto si pertenece al producto que se está actualizando.
        """
        if self.instance and self.instance.code_producto == value:
            # Permitir el código actual sin validar unicidad
            return value

        if Product.objects.filter(code_producto=value).exists():
            raise serializers.ValidationError("El código de producto ya está registrado.")

        return value

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = "__all__"

class StorePromotionSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    image_field = serializers.ImageField(required=False)

    class Meta:
        model = Promotion
        fields = "__all__"

    def get_image_field(self, obj):
        """ Devuelve la URL absoluta con HTTPS de la imagen """
        request = self.context.get('request')
        if obj.image_field:
            return request.build_absolute_uri(obj.image_field.url).replace("http://", "https://") if request else obj.image_field.url
        return None

    def validate(self, data):
        """
        Validar que el usuario no exceda el límite de reclamos permitido.
        """
        user = self.context['request'].user
        # Verificar si se está actualizando o creando
        if self.instance:
            promotion = self.instance

            # Obtener o crear el historial de reclamos para el usuario y la promoción
            claim_history, created = UserClaimHistory.objects.get_or_create(
                user=user,
                promotion=promotion
            )

            # Verificar si el usuario ya alcanzó el límite de reclamos
            if claim_history.claims_count >= promotion.max_claims_per_user:
                raise serializers.ValidationError(
                    f"Ya has alcanzado el límite de {promotion.max_claims_per_user} reclamos para esta promoción."
                )

        return data

    def create(self, validated_data):
        """
        Asigna la tienda del usuario automáticamente y configura valores predeterminados.
        """
        user_store = self.context["request"].user.store_users.first()
        if not user_store:
            raise serializers.ValidationError("El usuario no tiene una tienda asociada.")
        validated_data["store"] = user_store.store
        validated_data["authorize_promotion"] = "Pending"
        validated_data["is_enabled"] = False
        return super().create(validated_data)

class AdminPromotionSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = Promotion
        fields = "__all__"

class HistoricalClaimProductHistorySerializer(serializers.ModelSerializer):
    user = UserProfileNoContractSerializer(read_only=True)
    producto = ProductSerializer(read_only=True)

    class Meta:
        model = HistoricalClaimProductHistory
        fields = "__all__"

class HistoricalClaimPromotionHistorySerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    promotion_name = serializers.SerializerMethodField()
    claim_code = serializers.SerializerMethodField()
    validated_by = serializers.SerializerMethodField()

    class Meta:
        model = HistoricalClaimPromotionHistory
        fields = [
            "id", "datetime_created", "idtransaction", "datetime_approved", "datetime_rejected",
            "status", "promocion", "user", "store", "user_name", "promotion_name", "claim_code",
            "validated_by",
        ]

    def get_user_name(self, obj):
        return obj.user.username if obj.user else None

    def get_promotion_name(self, obj):
        return obj.promocion.title if obj.promocion else None

    def get_claim_code(self, obj):
        # Buscar la transacción y devolver el claim_code si existe
        if obj.idtransaction:
            transaction = Transaction.objects.filter(id=obj.idtransaction).first()
            if transaction:
                return transaction.claim_code
        return None

    def get_validated_by(self, obj):
        """ Busca la transacción usando idtransaction y devuelve el usuario validador. """
        if obj.idtransaction:
            transaction = Transaction.objects.filter(id=obj.idtransaction).first()
            if transaction and transaction.validated_by:
                return transaction.validated_by.username
        return "-"

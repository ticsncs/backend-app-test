from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.clients.models import Transaction
from apps.clients.utils import get_adjust_points_flag
from apps.store.models import HistoricalClaimPromotionHistory
from django.utils import timezone


# @receiver(post_save, sender=Transaction)
# def handle_transaction_status_change(sender, instance, **kwargs):
#     if instance.transaction_status == "Cancelled" and get_adjust_points_flag():
#         if instance.saldo:  # Solo revertir si los puntos ya estaban ajustados
#             if instance.status == 1:  # Revertir egreso
#                 instance.user.points += instance.amount
#             elif instance.status == 0:  # Revertir ingreso
#                 instance.user.points -= instance.amount
#             instance.user.save()
#             instance.saldo = None  # Limpiar el saldo después de cancelar
#             instance.save()

@receiver(post_save, sender=Transaction)
def update_idtransaction(sender, instance, created, **kwargs):
    if instance.tipo == "Promotion" and instance.transaction_status == "Pending":
        # Busca el historial relacionado con esta transacción
        historial = HistoricalClaimPromotionHistory.objects.filter(
            promocion=instance.codigo_promocion,
            user=instance.user,
            store=instance.codigo_promocion.store,
            idtransaction=None,
            status="Pending",
        ).first()

        # Si se encuentra el historial, actualiza campos relevantes
        if historial:
            # Actualiza el idtransaction
            historial.idtransaction = instance.pk

            if instance.transaction_status == "Completed":
                historial.status = "Completed"
                historial.datetime_approved = timezone.now()
            elif instance.transaction_status == "Cancelled":
                historial.status = "Cancelled"
                historial.datetime_rejected = timezone.now()

            # Guarda los cambios en el historial
            historial.save()
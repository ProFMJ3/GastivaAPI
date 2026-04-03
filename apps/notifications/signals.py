from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.notifications.models import Notification


# ============================================================
# HELPER — créer une notification rapidement
# ============================================================

def _create_notif(user, notif_type, title, message,
                  priority=Notification.Priority.MEDIUM,
                  related_object=None, data=None):
    """Crée une notification in-app pour un utilisateur."""
    notif = Notification(
        recipient=user,
        notification_type=notif_type,
        title=title,
        message=message,
        priority=priority,
        data=data or {},
    )
    if related_object is not None:
        notif.related_object = related_object
    notif.save()
    return notif


# ============================================================
# SIGNALS ORDER — réagit aux changements de statut
# ============================================================

# Garde l'ancien statut avant la sauvegarde
@receiver(pre_save, sender=Order)
def order_pre_save(sender, instance, **kwargs):
    """Mémorise l'ancien statut avant modification."""
    if instance.pk:
        try:
            instance._old_status = Order.objects.get(pk=instance.pk).status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    """Envoie une notification à chaque changement de statut."""
    client = instance.client
    order_number = instance.order_number
    partner_name = instance.partner.name if instance.partner else 'le partenaire'

    # ── Nouvelle commande créée ──────────────────────────────
    if created:
        _create_notif(
            user=client,
            notif_type=Notification.NotificationType.ORDER_CREATED,
            title='Commande passée !',
            message=f'Votre commande #{order_number} chez {partner_name} '
                    f'est en attente de confirmation.',
            priority=Notification.Priority.MEDIUM,
            related_object=instance,
            data={'order_id': instance.id, 'order_number': order_number},
        )
        return

    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    # Pas de changement de statut → rien à faire
    if old_status == new_status:
        return

    # ── Commande confirmée ───────────────────────────────────
    if new_status == Order.Status.CONFIRMED:
        _create_notif(
            user=client,
            notif_type=Notification.NotificationType.ORDER_CONFIRMED,
            title='Commande confirmée',
            message=f'Super ! {partner_name} a confirmé votre commande '
                    f'#{order_number}. Préparez-vous à récupérer !',
            priority=Notification.Priority.HIGH,
            related_object=instance,
            data={'order_id': instance.id, 'order_number': order_number},
        )

    # ── Commande prête à retirer ─────────────────────────────
    elif new_status == Order.Status.READY:
        pickup_code = instance.pickup_code or ''
        _create_notif(
            user=client,
            notif_type=Notification.NotificationType.ORDER_READY,
            title='Votre commande est prête !',
            message=f'Rendez-vous chez {partner_name} avec le code '
                    f'"{pickup_code}" pour récupérer votre commande #{order_number}.',
            priority=Notification.Priority.URGENT,
            related_object=instance,
            data={
                'order_id': instance.id,
                'order_number': order_number,
                'pickup_code': pickup_code,
            },
        )

    # ── Commande retirée ─────────────────────────────────────
    elif new_status == Order.Status.PICKED_UP:
        _create_notif(
            user=client,
            notif_type=Notification.NotificationType.ORDER_PICKED_UP,
            title='Bon appétit !',
            message=f'Vous avez récupéré votre commande #{order_number}. '
                    f'Merci de contribuer à réduire le gaspillage alimentaire !',
            priority=Notification.Priority.LOW,
            related_object=instance,
            data={'order_id': instance.id, 'order_number': order_number},
        )

    # ── Commande annulée ─────────────────────────────────────
    elif new_status == Order.Status.CANCELLED:
        reason = instance.cancellation_reason or 'Aucune raison fournie'
        _create_notif(
            user=client,
            notif_type=Notification.NotificationType.ORDER_CANCELLED,
            title='Commande annulée',
            message=f'Votre commande #{order_number} chez {partner_name} '
                    f'a été annulée. Raison : {reason}',
            priority=Notification.Priority.HIGH,
            related_object=instance,
            data={
                'order_id': instance.id,
                'order_number': order_number,
                'reason': reason,
            },
        )


# ============================================================
# SIGNALS PAYMENT — réagit aux changements de statut
# ============================================================

@receiver(pre_save, sender=Payment)
def payment_pre_save(sender, instance, **kwargs):
    """Mémorise l'ancien statut avant modification."""
    if instance.pk:
        try:
            instance._old_status = Payment.objects.get(pk=instance.pk).status
        except Payment.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Payment)
def payment_post_save(sender, instance, created, **kwargs):
    """Envoie une notification à chaque changement de statut paiement."""
    client = instance.order.client
    order_number = instance.order.order_number
    amount = f"{instance.amount:,.0f} FCFA"
    method = instance.get_payment_method_display()

    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    if old_status == new_status and not created:
        return

    # ── Paiement réussi ──────────────────────────────────────
    if new_status == Payment.Status.SUCCESS:
        _create_notif(
            user=client,
            notif_type=Notification.NotificationType.PAYMENT_SUCCESS,
            title='Paiement réussi',
            message=f'Votre paiement de {amount} via {method} pour la commande '
                    f'#{order_number} a été accepté.',
            priority=Notification.Priority.HIGH,
            related_object=instance,
            data={
                'payment_id': instance.id,
                'order_id': instance.order.id,
                'amount': str(instance.amount),
                'method': instance.payment_method,
            },
        )

    # ── Paiement échoué ──────────────────────────────────────
    elif new_status == Payment.Status.FAILED:
        reason = instance.failed_reason or 'Paiement refusé'
        _create_notif(
            user=client,
            notif_type=Notification.NotificationType.PAYMENT_FAILED,
            title='Paiement échoué',
            message=f'Le paiement de {amount} pour la commande #{order_number} '
                    f'a échoué. {reason}. Veuillez réessayer.',
            priority=Notification.Priority.URGENT,
            related_object=instance,
            data={
                'payment_id': instance.id,
                'order_id': instance.order.id,
                'reason': reason,
            },
        )
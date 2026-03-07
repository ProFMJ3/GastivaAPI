from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from .models import Notification, NotificationPreference


class NotificationService:
    """
    Service pour créer et envoyer des notifications.
    """

    @classmethod
    def create_order_notification(cls, order, notification_type, **kwargs):
        """
        Crée une notification liée à une commande.
        """
        from apps.orders.models import Order

        templates = {
            Notification.NotificationType.ORDER_CREATED: {
                'title': 'Commande créée',
                'message': 'Votre commande #{order_number} a été créée avec succès.'
            },
            Notification.NotificationType.ORDER_CONFIRMED: {
                'title': 'Commande confirmée',
                'message': 'Votre commande #{order_number} a été confirmée.'
            },
            Notification.NotificationType.ORDER_READY: {
                'title': 'Commande prête',
                'message': 'Votre commande #{order_number} est prête à être retirée.'
            },
            Notification.NotificationType.ORDER_PICKED_UP: {
                'title': 'Commande retirée',
                'message': 'Votre commande #{order_number} a été retirée. Merci !'
            },
            Notification.NotificationType.ORDER_CANCELLED: {
                'title': 'Commande annulée',
                'message': 'Votre commande #{order_number} a été annulée.'
            },
            Notification.NotificationType.PICKUP_REMINDER: {
                'title': 'Rappel de retrait',
                'message': 'N\'oubliez pas de retirer votre commande #{order_number} !'
            },
        }

        template = templates.get(notification_type, {})
        if not template:
            return None

        # Formater le message
        title = template['title']
        message = template['message'].format(order_number=order.order_number)

        # Données supplémentaires
        data = {
            'order_id': order.id,
            'order_number': order.order_number,
            'total_amount': str(order.total_amount),
            'partner_name': order.partner.name,
            'partner_quarter': order.partner.quarter,
            **kwargs
        }

        # Créer la notification pour le client
        client_notification = Notification.objects.create(
            recipient=order.client,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data,
            content_type=ContentType.objects.get_for_model(order),
            object_id=order.id
        )

        # Si la commande est pour un partenaire, notifier aussi le partenaire
        if notification_type in [
            Notification.NotificationType.ORDER_CREATED,
            Notification.NotificationType.ORDER_CANCELLED
        ]:
            partner_notification = Notification.objects.create(
                recipient=order.partner.owner,
                notification_type=notification_type,
                title=f"Nouvelle commande - {order.partner.name}",
                message=f"Commande #{order.order_number} - {order.client.get_full_name()}",
                data=data,
                content_type=ContentType.objects.get_for_model(order),
                object_id=order.id
            )
            return [client_notification, partner_notification]

        return client_notification

    @classmethod
    def create_payment_notification(cls, payment, notification_type, **kwargs):
        """
        Crée une notification liée à un paiement.
        """
        from apps.payments.models import Payment

        templates = {
            Notification.NotificationType.PAYMENT_SUCCESS: {
                'title': 'Paiement réussi',
                'message': 'Votre paiement de {amount} FCFA pour la commande #{order_number} a été effectué avec succès.'
            },
            Notification.NotificationType.PAYMENT_FAILED: {
                'title': 'Paiement échoué',
                'message': 'Le paiement de {amount} FCFA pour la commande #{order_number} a échoué.'
            },
            Notification.NotificationType.PAYMENT_REFUNDED: {
                'title': 'Remboursement effectué',
                'message': 'Votre paiement de {amount} FCFA pour la commande #{order_number} a été remboursé.'
            },
        }

        template = templates.get(notification_type, {})
        if not template:
            return None

        # Formater le message
        title = template['title']
        message = template['message'].format(
            amount=str(payment.amount),
            order_number=payment.order.order_number
        )

        # Données supplémentaires
        data = {
            'payment_id': payment.id,
            'transaction_id': payment.transaction_id,
            'order_id': payment.order.id,
            'order_number': payment.order.order_number,
            'amount': str(payment.amount),
            'payment_method': payment.payment_method,
            **kwargs
        }

        return Notification.objects.create(
            recipient=payment.order.client,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data,
            content_type=ContentType.objects.get_for_model(payment),
            object_id=payment.id
        )

    @classmethod
    def create_offer_notification(cls, offer, notification_type, **kwargs):
        """
        Crée une notification liée à une offre.
        """
        from apps.offers.models import FoodOffer

        templates = {
            Notification.NotificationType.OFFER_NEAR_EXPIRY: {
                'title': 'Offre bientôt expirée',
                'message': 'L\'offre "{offer_title}" expire dans moins d\'une heure !'
            },
            Notification.NotificationType.OFFER_NEW: {
                'title': 'Nouvelle offre',
                'message': 'Découvrez "{offer_title}" chez {partner_name} à -{discount}% !'
            },
            Notification.NotificationType.OFFER_POPULAR: {
                'title': 'Offre populaire',
                'message': '"{offer_title}" cartonne ! Dépêchez-vous avant qu\'il n\'y en ait plus.'
            },
        }

        template = templates.get(notification_type, {})
        if not template:
            return None

        # Formater le message
        title = template['title']
        message = template['message'].format(
            offer_title=offer.title,
            partner_name=offer.partner.name,
            discount=offer.discount_percentage
        )

        # Données supplémentaires
        data = {
            'offer_id': offer.id,
            'offer_title': offer.title,
            'partner_id': offer.partner.id,
            'partner_name': offer.partner.name,
            'original_price': str(offer.original_price),
            'discounted_price': str(offer.discounted_price),
            'discount': offer.discount_percentage,
            **kwargs
        }

        # Pour les offres, on peut notifier tous les clients (à implémenter avec des tâches Celery)
        # Pour l'instant, on retourne juste la notification sans destinataire
        return data

    @classmethod
    def send_welcome_notification(cls, user):
        """
        Envoie une notification de bienvenue à un nouvel utilisateur.
        """
        return Notification.objects.create(
            recipient=user,
            notification_type=Notification.NotificationType.WELCOME,
            priority=Notification.Priority.MEDIUM,
            title=f'Bienvenue {user.first_name} !',
            message='Nous sommes ravis de vous accueillir sur Gastiva. Découvrez les offres anti-gaspillage près de chez vous !',
            data={
                'user_id': user.id,
                'first_name': user.first_name
            }
        )

    @classmethod
    def send_partner_approved_notification(cls, partner):
        """
        Notifie un partenaire que son établissement a été approuvé.
        """
        return Notification.objects.create(
            recipient=partner.owner,
            notification_type=Notification.NotificationType.PARTNER_APPROVED,
            priority=Notification.Priority.HIGH,
            title='Établissement approuvé',
            message=f'Félicitations ! Votre établissement "{partner.name}" a été approuvé. Vous pouvez maintenant créer des offres.',
            data={
                'partner_id': partner.id,
                'partner_name': partner.name
            },
            content_type=ContentType.objects.get_for_model(partner),
            object_id=partner.id
        )
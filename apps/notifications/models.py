from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import User
from apps.orders.models import Order
from apps.partners.models import Partner


class Notification(models.Model):
    """
    Modèle de notification pour les utilisateurs.
    Supporte les notifications in-app et les notifications push.
    """

    class NotificationType(models.TextChoices):
        # Notifications de commande
        ORDER_CREATED = 'ORDER_CREATED', _('Commande créée')
        ORDER_CONFIRMED = 'ORDER_CONFIRMED', _('Commande confirmée')
        ORDER_READY = 'ORDER_READY', _('Commande prête')
        ORDER_PICKED_UP = 'ORDER_PICKED_UP', _('Commande retirée')
        ORDER_CANCELLED = 'ORDER_CANCELLED', _('Commande annulée')
        
        # Notifications de paiement
        PAYMENT_SUCCESS = 'PAYMENT_SUCCESS', _('Paiement réussi')
        PAYMENT_FAILED = 'PAYMENT_FAILED', _('Paiement échoué')
        PAYMENT_REFUNDED = 'PAYMENT_REFUNDED', _('Remboursement effectué')
        
        # Notifications d'offre
        OFFER_NEAR_EXPIRY = 'OFFER_NEAR_EXPIRY', _('Offre bientôt expirée')
        OFFER_NEW = 'OFFER_NEW', _('Nouvelle offre')
        OFFER_POPULAR = 'OFFER_POPULAR', _('Offre populaire')
        
        # Notifications de rappel
        PICKUP_REMINDER = 'PICKUP_REMINDER', _('Rappel de retrait')
        REVIEW_REMINDER = 'REVIEW_REMINDER', _('Rappel d\'avis')
        
        # Notifications système
        WELCOME = 'WELCOME', _('Bienvenue')
        ACCOUNT_VERIFIED = 'ACCOUNT_VERIFIED', _('Compte vérifié')
        PARTNER_APPROVED = 'PARTNER_APPROVED', _('Partenaire approuvé')
        PARTNER_SUSPENDED = 'PARTNER_SUSPENDED', _('Partenaire suspendu')

    class Priority(models.TextChoices):
        LOW = 'LOW', _('Basse')
        MEDIUM = 'MEDIUM', _('Moyenne')
        HIGH = 'HIGH', _('Haute')
        URGENT = 'URGENT', _('Urgente')

    # Destinataire
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )

    # Type et priorité
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True
    )

    # Contenu
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)

    # Image/icône (optionnelle)
    image = models.ImageField(
        upload_to='notifications/',
        null=True,
        blank=True
    )
    icon = models.CharField(max_length=50, default='notifications')

    # Statut de lecture
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Statut d'envoi (pour les différents canaux)
    is_sent_push = models.BooleanField(default=False)
    push_sent_at = models.DateTimeField(null=True, blank=True)
    
    is_sent_email = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    is_sent_sms = models.BooleanField(default=False)
    sms_sent_at = models.DateTimeField(null=True, blank=True)

    # Relation avec l'objet concerné (Order, Offer, Partner, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', 'priority']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.recipient.get_full_name()}"

    def save(self, *args, **kwargs):
        """Définit la date d'expiration par défaut si non spécifiée."""
        if not self.expires_at:
            # Expire après 30 jours par défaut
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)

    def mark_as_read(self):
        """Marque la notification comme lue."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_sent(self, channel='push'):
        """Marque la notification comme envoyée sur un canal spécifique."""
        now = timezone.now()
        
        if channel == 'push':
            self.is_sent_push = True
            self.push_sent_at = now
            update_fields = ['is_sent_push', 'push_sent_at']
        elif channel == 'email':
            self.is_sent_email = True
            self.email_sent_at = now
            update_fields = ['is_sent_email', 'email_sent_at']
        elif channel == 'sms':
            self.is_sent_sms = True
            self.sms_sent_at = now
            update_fields = ['is_sent_sms', 'sms_sent_at']
        else:
            return
        
        self.save(update_fields=update_fields)

    @property
    def is_expired(self):
        """Vérifie si la notification est expirée."""
        return self.expires_at and self.expires_at < timezone.now()

    @property
    def time_ago(self):
        """Retourne le temps écoulé depuis la création."""
        delta = timezone.now() - self.created_at
        
        if delta.days > 30:
            months = delta.days // 30
            return f"il y a {months} mois"
        elif delta.days > 0:
            return f"il y a {delta.days} jours"
        elif delta.seconds // 3600 > 0:
            hours = delta.seconds // 3600
            return f"il y a {hours} heures"
        elif delta.seconds // 60 > 0:
            minutes = delta.seconds // 60
            return f"il y a {minutes} minutes"
        else:
            return "à l'instant"


class NotificationPreference(models.Model):
    """
    Préférences de notification pour chaque utilisateur.
    Permet de choisir les canaux de réception pour chaque type.
    """
    
    class Channel(models.TextChoices):
        PUSH = 'PUSH', _('Push')
        EMAIL = 'EMAIL', _('Email')
        SMS = 'SMS', _('SMS')
        IN_APP = 'IN_APP', _('In-App')

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # Préférences globales
    allow_push = models.BooleanField(default=True)
    allow_email = models.BooleanField(default=True)
    allow_sms = models.BooleanField(default=False)
    allow_in_app = models.BooleanField(default=True)

    # Préférences par type de notification (JSON)
    # Exemple: {"ORDER_CONFIRMED": ["PUSH", "IN_APP"], "OFFER_NEAR_EXPIRY": ["PUSH", "SMS"]}
    type_preferences = models.JSONField(default=dict, blank=True)

    # Heures de silence (ne pas envoyer de notifications pendant ces heures)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    # Dernière mise à jour
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('préférence de notification')
        verbose_name_plural = _('préférences de notification')

    def __str__(self):
        return f"Préférences de {self.user.get_full_name()}"

    def should_send(self, notification_type, channel):
        """
        Vérifie si une notification doit être envoyée via un canal spécifique.
        """
        # Vérifier les préférences globales
        if channel == 'PUSH' and not self.allow_push:
            return False
        if channel == 'EMAIL' and not self.allow_email:
            return False
        if channel == 'SMS' and not self.allow_sms:
            return False
        if channel == 'IN_APP' and not self.allow_in_app:
            return False

        # Vérifier les préférences par type
        type_pref = self.type_preferences.get(notification_type, [])
        if type_pref and channel not in type_pref:
            return False

        # Vérifier les heures de silence
        if self.quiet_hours_start and self.quiet_hours_end:
            now = timezone.now().time()
            if self.quiet_hours_start <= now <= self.quiet_hours_end:
                return False

        return True
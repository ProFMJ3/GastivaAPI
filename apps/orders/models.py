

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.partners.models import Partner
from apps.offers.models import FoodOffer
import random
import string



class Order(models.Model):
    """
    Order model exactly as specified in the diagram.
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        CONFIRMED = 'CONFIRMED', _('Confirmed')
        READY = 'READY', _('Ready')
        PICKED_UP = 'PICKED_UP', _('Picked Up')
        CANCELLED = 'CANCELLED', _('Cancelled')

    order_number = models.CharField(max_length=20, unique=True, db_index=True)
    
    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        limit_choices_to={'role': User.Role.CLIENT}
    )
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    total_amount = models.DecimalField(max_digits=8, decimal_places=2)
    
    pickup_code = models.CharField(max_length=6, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    confirmed_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=300, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['partner', 'status']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

    # @classmethod
    # def generate_order_number(cls):
    #     """Génère un numéro de commande unique."""
    #     prefix = 'ORD'
    #     timestamp = timezone.now().strftime('%y%m%d')
        
    #     # Ajouter une partie aléatoire
    #     random_part = ''.join(random.choices(string.digits, k=4))
        
    #     # Ajouter une partie séquentielle (les 2 derniers chiffres d'un compteur)
    #     last_order = cls.objects.filter(
    #         order_number__startswith=f"{prefix}{timestamp}"
    #     ).order_by('-order_number').first()
        
    #     if last_order:
    #         try:
    #             last_sequence = int(last_order.order_number[-2:])
    #             sequence = (last_sequence + 1) % 100
    #         except (ValueError, IndexError):
    #             sequence = 0
    #     else:
    #         sequence = 0
        
    #     sequence_part = f"{sequence:02d}"
        
    #     return f"{prefix}{timestamp}{random_part}{sequence_part}"


    @classmethod
    def generate_order_number(cls):
        """
        Génère un numéro de commande unique au format:
        ORD + AA (année) + MM (mois) + JJ (jour) + XXXXX (aléatoire) + CC (checksum)
        Exemple: ORD250227A3F7C2
        """
        now = timezone.now()
        date_part = now.strftime('%y%m%d')  # 250227
        
        # Partie aléatoire (5 caractères alphanumériques)
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        
        # Checksum simple (2 chiffres basés sur la date + aléatoire)
        checksum = str((int(date_part) + sum(ord(c) for c in random_part)) % 100).zfill(2)
        
        order_number = f"ORD{date_part}{random_part}{checksum}"
        
        # Vérifier l'unicité
        while cls.objects.filter(order_number=order_number).exists():
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            checksum = str((int(date_part) + sum(ord(c) for c in random_part)) % 100).zfill(2)
            order_number = f"ORD{date_part}{random_part}{checksum}"
        
        return order_number

    @classmethod
    def generate_pickup_code(cls):
        """Génère un code de retrait à 6 chiffres."""
        return ''.join(random.choices(string.digits, k=6))

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        if not self.pickup_code:
            self.pickup_code = self.generate_pickup_code()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """
    OrderItem model exactly as specified in the diagram.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    offer = models.ForeignKey(
        FoodOffer,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    subtotal = models.DecimalField(max_digits=8, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('order item')
        verbose_name_plural = _('order items')

    def __str__(self):
        return f"{self.quantity}x {self.offer.title}"

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)
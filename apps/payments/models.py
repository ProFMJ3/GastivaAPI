
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.orders.models import Order
import uuid


class Payment(models.Model):
    """
    Payment model exactly as specified in the diagram.
    """
    
    class PaymentMethod(models.TextChoices):
        TMONEY = 'TMONEY', _('T-Money')
        FLOZ = 'FLOOZ', _('Flooz')
        CASH = 'CASH', _('Cash')

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        SUCCESS = 'SUCCESS', _('Success')
        FAILED = 'FAILED', _('Failed')

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        db_index=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)  # For additional payment details
    
    paid_at = models.DateTimeField(null=True, blank=True)
    failed_reason = models.CharField(max_length=300, null=True, blank=True)
    
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('payment')
        verbose_name_plural = _('payments')
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.transaction_id or self.id}"

    @classmethod
    def generate_transaction_id(cls):
        prefix = 'TXN'
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"{prefix}{timestamp}{unique_id}"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)
from datetime import timezone

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User
from apps.orders.models import Order


class Review(models.Model):
    """
    Review model - partner is derived from the order.
    """
    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        limit_choices_to={'role': User.Role.CLIENT}
    )
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='review',
        null=True,
        blank=True
    )
    
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, null=True)
    is_visible = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('review')
        verbose_name_plural = _('reviews')
        ordering = ['-created_at']
        unique_together = ['client', 'order']  # One review per order

    def __str__(self):
        partner_name = self.order.partner.name if self.order else "Unknown"
        return f"Review by {self.client.get_full_name()} for {partner_name} - {self.rating}★"

    @property
    def partner(self):
        """Get partner from the associated order."""
        return self.order.partner if self.order else None
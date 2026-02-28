

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.partners.models import Partner

class FoodCategory(models.Model):
    """
    FoodCategory model exactly as specified in the diagram.
    """
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('food category')
        verbose_name_plural = _('food categories')
        ordering = ['name']

    def __str__(self):
        return self.name


class FoodOffer(models.Model):
    """
    FoodOffer model exactly as specified in the diagram.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        RESERVED = 'RESERVED', _('Reserved')
        EXPIRED = 'EXPIRED', _('Expired')
        CANCELLED = 'CANCELLED', _('Cancelled')

    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='food_offers'
    )
    category = models.ForeignKey(
        FoodCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='offers'
    )

    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='offers/', null=True, blank=True)
    
    original_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    discounted_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    quantity_available = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0)]
    )
    quantity_reserved = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    pickup_deadline = models.DateTimeField(db_index=True)
    available_from = models.DateTimeField(default=timezone.now)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    
    is_featured = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('food offer')
        verbose_name_plural = _('food offers')
        ordering = ['pickup_deadline', '-created_at']

    def __str__(self):
        return self.title

    @property
    def discount_percentage(self):
        """Calculate discount percentage."""
        if self.original_price and self.original_price > 0:
            return int(((self.original_price - self.discounted_price) / self.original_price) * 100)
        return 0

    @property
    def remaining_quantity(self):
        """Get remaining available quantity."""
        return max(0, self.quantity_available - self.quantity_reserved)

    @property
    def is_available(self):
        """Check if offer is available for purchase."""
        now = timezone.now()
        return (
            self.status == self.Status.ACTIVE and
            self.remaining_quantity > 0 and
            self.pickup_deadline > now and
            self.available_from <= now
        )

    def reserve(self, quantity=1):
        """
        Reserve a quantity of this offer.
        Returns True if successful, False otherwise.
        """
        if not self.is_available or quantity > self.remaining_quantity:
            return False
        
        self.quantity_reserved += quantity
        self.save(update_fields=['quantity_reserved', 'status'])
        return True

    def release_reservation(self, quantity=1):
        """
        Release a reserved quantity.
        Called when order is cancelled or payment fails.
        """
        self.quantity_reserved = max(0, self.quantity_reserved - quantity)
        self.save(update_fields=['quantity_reserved', 'status'])

    def update_status(self):
        """
        Update offer status based on current state.
        Called automatically before save and by cron jobs.
        """
        now = timezone.now()
        
        # Check if expired
        if self.pickup_deadline <= now:
            self.status = self.Status.EXPIRED
            return
        
        # Check if sold out
        if self.quantity_available <= 0:
            self.status = self.Status.SOLD_OUT
            return
        
        # Check if fully reserved
        if self.quantity_reserved >= self.quantity_available:
            self.status = self.Status.RESERVED
            return
        
        # Default to active
        if self.status != self.Status.ACTIVE:
            self.status = self.Status.ACTIVE
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User


class CategoryPartner(models.Model):
    """
    Catégorie de partenaire (Restaurant, Boulangerie, Traiteur, Épicerie, etc.)
    """
    name = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        verbose_name=_("Nom de la catégorie")
    )
    slug = models.SlugField(
        max_length=100, 
        unique=True,
        verbose_name=_("Slug")
    )
    description = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_("Description")
    )
    icon = models.CharField(
        max_length=50,
        help_text=_("Icône FontAwesome ou classe CSS"),
        default="fa-store"
    )
    image = models.ImageField(
        upload_to='categories/',
        null=True,
        blank=True,
        verbose_name=_("Image d'illustration")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active")
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name=_("Ordre d'affichage")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Catégorie de partenaire")
        verbose_name_plural = _("Catégories de partenaires")
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Partner(models.Model):
    """
    Partenaire model with working days and category.
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        SUSPENDED = 'SUSPENDED', _('Suspended')

    # Days of week choices
    DAYS_OF_WEEK = [
        ('monday', 'Lundi'),
        ('tuesday', 'Mardi'),
        ('wednesday', 'Mercredi'),
        ('thursday', 'Jeudi'),
        ('friday', 'Vendredi'),
        ('saturday', 'Samedi'),
        ('sunday', 'Dimanche'),
    ]

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='partners',
        limit_choices_to={'role': User.Role.PARTNER}
    )

    # Category
    category = models.ForeignKey(
        CategoryPartner,
        on_delete=models.SET_NULL,
        null=True,
        related_name='partners',
        verbose_name=_("Catégorie")
    )

    # Basic info
    name = models.CharField(max_length=200, db_index=True, verbose_name=_("Nom"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    
    # Media
    logo = models.ImageField(
        upload_to='partenaires/logos/', 
        null=True, 
        blank=True,
        verbose_name=_("Logo")
    )
    cover_image = models.ImageField(
        upload_to='partenaires/covers/', 
        null=True, 
        blank=True,
        verbose_name=_("Image de couverture")
    )
    
    # Location
    address = models.CharField(max_length=300, verbose_name=_("Adresse"))
    city = models.CharField(max_length=100, default="Lomé", verbose_name=_("Ville"))
    quarter = models.CharField(max_length=100, db_index=True, verbose_name=_("Quartier"))
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        verbose_name=_("Latitude")
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        verbose_name=_("Longitude")
    )
    
    # Contact
    phone = models.CharField(max_length=20, verbose_name=_("Téléphone"))
    email = models.EmailField(blank=True, null=True, verbose_name=_("Email"))
    website = models.URLField(blank=True, null=True, verbose_name=_("Site web"))
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    # Operating hours (applies to all working days)
    opening_time = models.TimeField(verbose_name=_("Heure d'ouverture"))
    closing_time = models.TimeField(verbose_name=_("Heure de fermeture"))
    
    # Working days - stockés comme JSON pour plus de flexibilité
    working_days = models.JSONField(
        default=list,
        help_text=_("Liste des jours d'ouverture (ex: ['monday', 'tuesday', 'wednesday'])")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('partner')
        verbose_name_plural = _('partners')
        indexes = [
            models.Index(fields=['status', 'quarter']),
            models.Index(fields=['category', 'status']),
             models.Index(fields=['owner', 'status']),
        ]

    def __str__(self):
        return f"{self.name} - {self.quarter}"

    def clean(self):
        """Validate working days."""
        if self.working_days:
            valid_days = [day[0] for day in self.DAYS_OF_WEEK]
            for day in self.working_days:
                if day not in valid_days:
                    raise ValidationError(
                        f"'{day}' n'est pas un jour valide. Choisissez parmi {valid_days}"
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def is_open_on(self, day):
        """
        Check if Partenaire is open on a specific day.
        Args:
            day: string like 'monday', 'tuesday', etc.
        """
        return day in self.working_days

    def is_open_now(self):
        """
        Check if Partenaire is currently open.
        """
        from django.utils import timezone
        import datetime

        now = timezone.now()
        current_day = now.strftime('%A').lower()
        current_time = now.time()

        # Map English day names
        day_mapping = {
            'monday': 'monday',
            'tuesday': 'tuesday',
            'wednesday': 'wednesday',
            'thursday': 'thursday',
            'friday': 'friday',
            'saturday': 'saturday',
            'sunday': 'sunday'
        }
        
        current_day = day_mapping.get(current_day, current_day)

        return (
            current_day in self.working_days and
            self.opening_time <= current_time <= self.closing_time
        )

    def get_working_days_display(self):
        """
        Return human-readable list of working days.
        """
        day_display = dict(self.DAYS_OF_WEEK)
        return [day_display.get(day, day) for day in self.working_days]

    def get_working_days_string(self):
        """
        Return a comma-separated string of working days.
        """
        days = self.get_working_days_display()
        if len(days) == 7:
            return "Tous les jours"
        elif len(days) == 5 and set(['monday', 'tuesday', 'wednesday', 'thursday', 'friday']).issubset(set(self.working_days)):
            return "Lundi au Vendredi"
        else:
            return ", ".join(days)
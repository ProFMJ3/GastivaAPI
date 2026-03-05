from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    User model allowing authentication with either email or phone number.
    Phone number is the preferred method for Togolese users.
    """
    
    class Role(models.TextChoices):
        CLIENT = 'CLIENT', _('Client')
        PARTNER = 'PARTNER', _('Partner')
        ADMIN = 'ADMIN', _('Administrator')

   # Garder username mais le rendre optionnel
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Optional. Will be auto-generated if not provided.')
    )
    
    # Email est optionnel pour les utilisateurs togolais
    email = models.EmailField(_('email address'),  null=True, blank=True, db_index=True)
    
    # Phone number validation for Togo
    phone_regex = RegexValidator(
        regex=r'^(90|91|92|93|70|71|79|78|99|98|96|97)\d{6}$',
        message=_("Numéro de téléphone togolais valide requis (8 chiffres commençant par 90,91,92,93,70,71,79)")
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=20,
        unique=True,
        db_index=True,
        null=True, blank=True,

        help_text=_("Format de numéro togolais")
    )
    
    # Personal info - déjà dans AbstractUser
    # first_name et last_name sont déjà dans AbstractUser
    
    # Role management
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
        db_index=True
    )
    
    # Account status
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Designates whether the user has verified their phone.")
    )
    
    # Profile
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text=_("User profile picture")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Store Mobile Money info for clients
    preferred_payment_method = models.CharField(
        max_length=20,
        choices=[
            ('TMONEY', 'T-Money'),
            ('FLOZ', 'Floz'),
            ('CASH', 'Cash'),
        ],
        null=True,
        blank=True
    )
    
    # Utiliser phone_number comme identifiant principal pour l'authentification
    #USERNAME_FIELD = 'phone_number'
    #REQUIRED_FIELDS = ['first_name', 'last_name']  # email est optionnel

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        indexes = [
            models.Index(fields=['email', 'role']),
            models.Index(fields=['phone_number', 'is_verified']),
        ]
        constraints = []


    def __str__(self):
        return f"{self.get_full_name()} ({self.phone_number})"

    def get_full_name(self):
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Return the short name of the user."""
        return self.first_name

    def is_restaurant_owner(self):
        """Check if user is a restaurant owner."""
        return self.role == self.Role.RESTAURANT

    def is_client(self):
        """Check if user is a client."""
        return self.role == self.Role.CLIENT

    def is_admin(self):
        """Check if user is an admin."""
        return self.role == self.Role.ADMIN or self.is_superuser

    def save(self, *args, **kwargs):
        """Override save to auto-generate username if not provided."""
        if not self.username:
            # Generate username from phone_number (plus fiable que email)
            self.username = f"user_{self.phone_number}"

        # Si email est une chaîne vide, le mettre à None
        if self.email == '':
            self.email = None
        super().save(*args, **kwargs)

    def clean(self):
        """Ensure at least email or phone is provided."""
        super().clean()
        if not self.email and not self.phone_number:
            raise ValidationError(_("Au moins un email ou un numéro de téléphone est requis."))
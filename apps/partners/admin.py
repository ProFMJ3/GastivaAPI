from django.contrib import admin
from .models import CategoryPartner, Partner
from django import forms

class PartnerAdminForm(forms.ModelForm):
    working_days = forms.MultipleChoiceField(
        choices=[
            ('monday', 'Lundi'),
            ('tuesday', 'Mardi'),
            ('wednesday', 'Mercredi'),
            ('thursday', 'Jeudi'),
            ('friday', 'Vendredi'),
            ('saturday', 'Samedi'),
            ('sunday', 'Dimanche'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Sélectionnez les jours d'ouverture"
    )
    
    class Meta:
        model = Partner
        fields = '__all__'

@admin.register(CategoryPartner)
class CategoryPartnerAdmin(admin.ModelAdmin):
    """Simple admin for partner categories."""
    list_display = ['name', 'icon', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    form = PartnerAdminForm
    """Simple admin for partners."""
    list_display = ['name', 'category', 'quarter', 'phone', 'status']
    list_filter = ['status', 'category', 'quarter']
    search_fields = ['name', 'phone', 'email']
    fieldsets = (
        ('Info', {
            'fields': ('owner', 'name', 'category','logo', 'description')
        }),
        ('Contact', {
            'fields': ('address', 'quarter', 'phone', 'email')
        }),
        ('Hours', {
            'fields': ('opening_time', 'closing_time', 'working_days')
        }),
        ('Status', {
            'fields': ('status',)
        }),
    )
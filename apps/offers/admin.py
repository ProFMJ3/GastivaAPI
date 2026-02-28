from django.contrib import admin
from .models import FoodCategory, FoodOffer


@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(FoodOffer)
class FoodOfferAdmin(admin.ModelAdmin):
    list_display = ['title', 'partner', 'category', 'discounted_price', 'status', 'pickup_deadline']
    list_filter = ['status', 'category', 'is_featured']
    search_fields = ['title', 'partner__name']
    autocomplete_fields = ['partner', 'category']
    radio_fields = {'status': admin.HORIZONTAL}
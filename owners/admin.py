from django.contrib import admin
from .models import Owner, Pet, PetType, SocialMedia

# Register your models here.

class PetInline(admin.TabularInline):
    model = Pet
    extra = 1 # Start with one empty form for a pet

@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'code', 'phone_number', 'clinic')
    search_fields = ('full_name', 'code', 'phone_number')
    list_filter = ('clinic', 'knew_us_from')
    inlines = [PetInline]

admin.site.register(PetType)
admin.site.register(SocialMedia)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Country, ClinicOwnerProfile, DoctorProfile, ReceptionProfile, SubscriptionType, PaymentMethod


class ClinicOwnerProfileInline(admin.StackedInline):
    """
    Allows editing of the ClinicOwnerProfile directly within the User admin page.
    """
    model = ClinicOwnerProfile
    can_delete = False
    verbose_name_plural = 'Clinic Owner Profile'


class DoctorProfileInline(admin.StackedInline):
    """
    Allows editing of the DoctorProfile directly within the User admin page.
    """
    model = DoctorProfile
    can_delete = False
    verbose_name_plural = 'Doctor Profile'


class ReceptionProfileInline(admin.StackedInline):
    """
    Allows editing of the ReceptionProfile directly within the User admin page.
    """
    model = ReceptionProfile
    can_delete = False
    verbose_name_plural = 'Reception Profile'


class CustomUserAdmin(UserAdmin):
    """
    Custom UserAdmin to display and edit the 'role' field.
    """

    # Add 'role' to the list of fields displayed in the user list
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "role",
    )

    # Add 'role' to the fieldsets to make it editable in the user detail view
    fieldsets = UserAdmin.fieldsets + (("Custom Fields", {"fields": ("role",)}),)

    inlines = []

    def get_inlines(self, request, obj=None):
        """
        Show the ClinicOwnerProfileInline only for users with the CLINIC_OWNER role.
        """
        if obj and obj.role == User.Role.CLINIC_OWNER:
            return [ClinicOwnerProfileInline]
        if obj and obj.role == User.Role.DOCTOR:
            return [DoctorProfileInline]
        if obj and obj.role == User.Role.RECEPTION:
            return [ReceptionProfileInline]
        return []


admin.site.register(User, CustomUserAdmin)
admin.site.register(ClinicOwnerProfile)
admin.site.register(DoctorProfile)
admin.site.register(ReceptionProfile)
admin.site.register(SubscriptionType)
admin.site.register(PaymentMethod)
admin.site.register(Country)

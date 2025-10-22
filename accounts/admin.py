#accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Prefetch, Q
from .models import User, Country, ClinicOwnerProfile, DoctorProfile, ReceptionProfile, SubscriptionType, PaymentMethod, SubscriptionHistory


class SubscriptionHistoryInline(admin.TabularInline):
    """
    Allows viewing subscription history directly within the ClinicOwnerProfile admin page.
    """
    model = SubscriptionHistory
    extra = 0  # Don't show extra blank forms
    readonly_fields = ('days_left', 'end_date', 'activation_date', 'comments')
    fields = ('subscription_type', 'payment_method', 'amount_paid', 'start_date', 'end_date', 'status', 'days_left', 'activated_by', 'comments')


class ClinicOwnerProfileInline(admin.StackedInline):
    """
    Allows editing of the ClinicOwnerProfile directly within the User admin page.
    """
    model = ClinicOwnerProfile
    can_delete = False


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


@admin.action(description='Mark selected clinics as Ended')
def make_ended(modeladmin, request, queryset):
    queryset.update(status=ClinicOwnerProfile.Status.ENDED)

@admin.action(description='Suspend selected ACTIVE clinics')
def suspend_clinics(modeladmin, request, queryset):
    for profile in queryset.filter(status=ClinicOwnerProfile.Status.ACTIVE):
        # New Rule: Cannot suspend if there is an upcoming subscription.
        if profile.subscription_history.filter(status=SubscriptionHistory.Status.UPCOMING).exists():
            continue # Silently skip this profile in the admin action

        active_sub = profile.active_subscription
        if active_sub:
            profile.status = ClinicOwnerProfile.Status.SUSPENDED
            active_sub.status = SubscriptionHistory.Status.SUSPENDED
            active_sub.comments = f"Suspended via admin action by {request.user.username}."
            profile.save()
            active_sub.save()

@admin.action(description='Reactivate selected SUSPENDED clinics')
def reactivate_clinics(modeladmin, request, queryset):
    for profile in queryset.filter(status=ClinicOwnerProfile.Status.SUSPENDED):
        suspended_sub = profile.subscription_history.filter(status=SubscriptionHistory.Status.SUSPENDED).first()
        if suspended_sub:
            # The model's save() method will handle changing the status back to ACTIVE
            suspended_sub.comments = f"Reactivated via admin action by {request.user.username}."
            suspended_sub.save()

        profile.status = ClinicOwnerProfile.Status.ACTIVE
        profile.save()

@admin.action(description='Refund active/suspended subscription for selected clinics')
def refund_active_subscription(modeladmin, request, queryset):
    for profile in queryset:
        # Find an active, suspended, or upcoming subscription to refund
        sub_to_refund = profile.subscription_history.filter(
            Q(status=SubscriptionHistory.Status.ACTIVE) | Q(status=SubscriptionHistory.Status.SUSPENDED) | Q(status=SubscriptionHistory.Status.UPCOMING)
        ).first()

        if sub_to_refund:
            sub_to_refund.status = SubscriptionHistory.Status.REFUNDED
            sub_to_refund.comments = f"Refunded via admin action by {request.user.username}."
            sub_to_refund.save()

            # Check if the clinic has any other active or upcoming subscriptions.
            if not profile.subscription_history.filter(
                Q(status=SubscriptionHistory.Status.ACTIVE) | Q(status=SubscriptionHistory.Status.UPCOMING)
            ).exists():
                profile.status = ClinicOwnerProfile.Status.ENDED
                profile.save()


@admin.register(ClinicOwnerProfile)
class ClinicOwnerProfileAdmin(admin.ModelAdmin):
    list_display = ('clinic_name', 'clinic_owner_name', 'country', 'status', 'current_plan', 'days_left')
    list_filter = ('status', 'country')
    search_fields = ('clinic_name', 'clinic_owner_name', 'user__username')
    inlines = [SubscriptionHistoryInline]
    readonly_fields = ('user', 'joined_date', 'added_by', 'active_subscription', 'current_plan', 'days_left')
    actions = [make_ended, suspend_clinics, reactivate_clinics, refund_active_subscription]

    def get_queryset(self, request):
        """Optimize the queryset to prevent N+1 queries."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'country').prefetch_related(
            Prefetch(
                'subscription_history',
                queryset=SubscriptionHistory.objects.filter(status=SubscriptionHistory.Status.ACTIVE).select_related('subscription_type'),
                to_attr='_active_subscription_cached'
            )
        )

    def days_left(self, obj):
        """Display days left from the prefetched active subscription."""
        return obj.active_subscription.days_left if obj.active_subscription else None
    days_left.short_description = 'Days Left'


admin.site.register(User, CustomUserAdmin)
admin.site.register(DoctorProfile)
admin.site.register(ReceptionProfile)

@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ('clinic', 'subscription_type', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'subscription_type')
    readonly_fields = ('end_date', 'days_left', 'activation_date', 'comments')
    search_fields = ('clinic__clinic_name', 'ref_number')

admin.site.register(SubscriptionType)
admin.site.register(Country)

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name',)

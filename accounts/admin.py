#accounts/admin.py
from datetime import date, timedelta
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.db.models import Subquery, OuterRef, Prefetch, Q
from .models import User, Country, ClinicOwnerProfile, DoctorProfile, ReceptionProfile, SubscriptionType, PaymentMethod, SubscriptionHistory, UserSession


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
    fk_name = 'user' # Explicitly specify the foreign key linking to User
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

@admin.action(description='Suspend selected ACTIVE subscriptions')
def suspend_subscriptions(modeladmin, request, queryset):
    for sub in queryset.filter(status=SubscriptionHistory.Status.ACTIVE):
        # Rule: Cannot suspend if there is an upcoming subscription.
        if sub.clinic.subscription_history.filter(status=SubscriptionHistory.Status.UPCOMING).exists():
            continue

        # Calculate remaining days to "freeze" them
        days_remaining = sub.days_left

        # Create a new suspended record
        SubscriptionHistory.objects.create(
            subscription_group=sub.subscription_group,
            clinic=sub.clinic,
            subscription_type=sub.subscription_type,
            payment_method=sub.payment_method,
            amount_paid=sub.amount_paid,
            start_date=date.today(),
            end_date=sub.end_date, # Original end_date is kept for reference
            status=SubscriptionHistory.Status.SUSPENDED,
            comments=f"Suspended via admin by {request.user.username}.\n[Days Remaining: {days_remaining}]",
            activated_by=request.user
        )

@admin.action(description='Reactivate selected SUSPENDED subscriptions')
def reactivate_subscriptions(modeladmin, request, queryset):
    for sub in queryset.filter(status=SubscriptionHistory.Status.SUSPENDED):
        # Extract the frozen days remaining from the comment
        days_remaining = 0
        try:
            comment_lines = sub.comments.split('\n')
            for line in comment_lines:
                if line.startswith('[Days Remaining:'):
                    days_remaining = int(line.split(':')[1].strip().strip(']'))
                    break
        except (ValueError, IndexError):
            new_end_date = sub.end_date # Fallback if parsing fails
        else:
            new_end_date = date.today() + timedelta(days=days_remaining)

        # Create a new active record
        SubscriptionHistory.objects.create(
            subscription_group=sub.subscription_group,
            clinic=sub.clinic,
            subscription_type=sub.subscription_type,
            payment_method=sub.payment_method,
            amount_paid=sub.amount_paid,
            start_date=date.today(),
            end_date=new_end_date,
            status=SubscriptionHistory.Status.ACTIVE,
            comments=f"Reactivated via admin by {request.user.username}.",
            activated_by=request.user
        )

@admin.action(description='Refund selected subscriptions')
def refund_subscriptions(modeladmin, request, queryset):
    """Refund selected subscriptions. Clinic status will auto-update based on remaining subscriptions."""
    for sub in queryset.filter(status__in=[SubscriptionHistory.Status.ACTIVE, SubscriptionHistory.Status.SUSPENDED, SubscriptionHistory.Status.UPCOMING]):
        sub.status = SubscriptionHistory.Status.REFUNDED
        sub.comments = f"Refunded via admin action by {request.user.username}."
        sub.save()
        # Note: clinic.status will automatically update (it's a computed property)


@admin.action(description='Deactivate selected clinics (soft delete)')
def deactivate_clinics(modeladmin, request, queryset):
    """Admin action to soft delete clinics with an ENDED status."""
    from django.contrib import messages
    updated_count = 0
    skipped_count = 0
    
    for clinic in queryset:
        if clinic.status == ClinicOwnerProfile.Status.ENDED and not clinic.is_deactivated:
            with transaction.atomic():
                clinic.is_deactivated = True
                clinic.save(update_fields=['is_deactivated'])
                
                # Deactivate all associated users
                User.objects.filter(
                    Q(clinic_owner_profile=clinic) |
                    Q(doctor_profile__clinic_owner_profile=clinic) |
                    Q(reception_profile__clinic_owner_profile=clinic)
                ).update(is_active=False)
                updated_count += 1
        else:
            skipped_count += 1
    
    if updated_count > 0:
        messages.success(request, f'Successfully deactivated {updated_count} clinic(s).')
    if skipped_count > 0:
        messages.warning(request, f'Skipped {skipped_count} clinic(s) - only ENDED clinics can be deactivated.')

@admin.action(description='Reactivate selected clinics')
def reactivate_clinics(modeladmin, request, queryset):
    """Admin action to reactivate soft-deleted clinics."""
    from django.contrib import messages
    updated_count = 0
    skipped_count = 0
    
    for clinic in queryset:
        if clinic.is_deactivated:
            with transaction.atomic():
                clinic.is_deactivated = False
                clinic.save(update_fields=['is_deactivated'])
                
                # Reactivate all associated users
                User.objects.filter(
                    Q(clinic_owner_profile=clinic) |
                    Q(doctor_profile__clinic_owner_profile=clinic) |
                    Q(reception_profile__clinic_owner_profile=clinic)
                ).update(is_active=True)
                updated_count += 1
        else:
            skipped_count += 1
    
    if updated_count > 0:
        messages.success(request, f'Successfully reactivated {updated_count} clinic(s).')
    if skipped_count > 0:
        messages.info(request, f'Skipped {skipped_count} clinic(s) - already active.')


@admin.register(ClinicOwnerProfile)
class ClinicOwnerProfileAdmin(admin.ModelAdmin):
    list_display = ('clinic_name', 'clinic_owner_name', 'country', 'status', 'current_plan', 'days_left', 'is_deactivated')
    list_filter = ('is_deactivated', 'country')
    search_fields = ('clinic_name', 'clinic_owner_name', 'user__username')
    inlines = [SubscriptionHistoryInline]
    readonly_fields = ('joined_date', 'added_by', 'active_subscription', 'current_plan', 'days_left', 'status')
    actions = [deactivate_clinics, reactivate_clinics]

    def get_queryset(self, request):
        """Optimize the queryset to prevent N+1 queries."""
        qs = super().get_queryset(request).select_related('user', 'country')

        # Prefetch the entire subscription history to allow the `status` property to work efficiently.
        # The `status` property on the model is now the source of truth.
        qs = qs.prefetch_related(
            Prefetch(
                'subscription_history',
                queryset=SubscriptionHistory.objects.order_by('-activation_date', '-pk')
            )
        )

        # Prefetch the active subscription for calculating days_left and current_plan
        qs = qs.prefetch_related(
            Prefetch(
                'subscription_history',
                queryset=SubscriptionHistory.objects.filter(status=SubscriptionHistory.Status.ACTIVE).select_related('subscription_type'),
                to_attr='_active_subscription_cached'
            )
        )
        return qs

    @admin.display(description='Status', ordering='is_deactivated')
    def status(self, obj):
        """Display the computed status property from the model with color coding."""
        status_colors = {
            'ACTIVE': '🟢',
            'INACTIVE': '⚪',
            'ENDED': '🔴',
            'SUSPENDED': '🟡',
            'DEACTIVATED': '⚫'
        }
        icon = status_colors.get(obj.status, '')
        return f"{icon} {obj.status}"

    @admin.display(description='Deactivated', boolean=True, ordering='is_deactivated')
    def deactivated_status(self, obj):
        """Display deactivation status as a boolean icon."""
        return obj.is_deactivated

    def get_form(self, request, obj=None, **kwargs):
        """
        Customize the form to filter the 'user' field.
        - On 'add' page, show only clinic owners who are not yet linked to a profile.
        - On 'change' page, the field is readonly, so no filtering is needed.
        """
        form = super().get_form(request, obj, **kwargs)
        if 'user' in form.base_fields:
            # Filter out users who already have a clinic owner profile
            form.base_fields['user'].queryset = User.objects.filter(
                role=User.Role.CLINIC_OWNER,
                clinic_owner_profile__isnull=True
            )
        return form

    def days_left(self, obj):
        """Display days left from the prefetched active subscription."""
        return obj.active_subscription.days_left if obj.active_subscription else None
    days_left.short_description = 'Days Left'


admin.site.register(User, CustomUserAdmin)
admin.site.register(DoctorProfile)
admin.site.register(ReceptionProfile)

@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ('clinic', 'subscription_type', 'start_date', 'end_date', 'status', 'subscription_group')
    list_filter = ('status', 'subscription_type', 'clinic', 'subscription_group')
    readonly_fields = ('end_date', 'days_left', 'activation_date', 'comments')
    search_fields = ('clinic__clinic_name', 'ref_number', 'subscription_group__iexact')
    actions = [suspend_subscriptions, reactivate_subscriptions, refund_subscriptions]

    def get_form(self, request, obj=None, **kwargs):
        """
        Customize the form to exclude 'ENDED' from the status choices on the 'add' page.
        """
        form = super().get_form(request, obj, **kwargs)
        # When creating a new subscription (obj is None)
        if obj is None and 'status' in form.base_fields:
            # Filter out the 'ENDED' choice from the status field
            form.base_fields['status'].choices = [
                choice for choice in SubscriptionHistory.Status.choices 
                if choice[0] != SubscriptionHistory.Status.ENDED
            ]
        return form

@admin.register(SubscriptionType)
class SubscriptionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'allowed_accounts', 'is_active')
    list_filter = ('is_active',)
    actions = ['make_active', 'make_inactive']

    @admin.action(description='Mark selected types as active')
    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='Mark selected types as inactive')
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    actions = ['make_active', 'make_inactive']

    @admin.action(description='Mark selected methods as active')
    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='Mark selected methods as inactive')
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_id_number', 'max_phone_number')
    search_fields = ('name',)

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_info_short', 'created_at', 'last_used')
    list_filter = ('created_at', 'last_used')
    search_fields = ('user__username', 'device_info')
    readonly_fields = ('user', 'jti', 'refresh_token_jti', 'device_info', 'created_at', 'last_used')
    
    def device_info_short(self, obj):
        """Display shortened device info"""
        return obj.device_info[:80] + '...' if len(obj.device_info) > 80 else obj.device_info
    device_info_short.short_description = 'Device Info'
    
    def has_add_permission(self, request):
        """Prevent manual creation of sessions"""
        return False

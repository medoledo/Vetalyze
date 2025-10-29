#accounts/admin.py
from django.db.models import Subquery, OuterRef
from datetime import date, timedelta
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


def _create_new_subscription_record(original_sub, new_status, comment, user):
    """Helper to create a new subscription record based on an old one."""
    return SubscriptionHistory.objects.create(
        subscription_group=original_sub.subscription_group, # Keep the same group
        clinic=original_sub.clinic,
        subscription_type=original_sub.subscription_type,
        payment_method=original_sub.payment_method,
        amount_paid=original_sub.amount_paid,
        start_date=date.today(),
        end_date=original_sub.end_date,
        status=new_status,
        comments=comment,
        activated_by=user
    )

@admin.action(description='Suspend selected ACTIVE subscriptions')
def suspend_subscriptions(modeladmin, request, queryset):
    for sub in queryset.filter(status=SubscriptionHistory.Status.ACTIVE):
        # Rule: Cannot suspend if there is an upcoming subscription.
        if sub.clinic.subscription_history.filter(status=SubscriptionHistory.Status.UPCOMING).exists():
            continue
        
        # End the current active subscription
        original_end_date = sub.end_date
        sub.end_date = date.today() - timedelta(days=1)
        sub.status = SubscriptionHistory.Status.ENDED
        sub.comments = f"{sub.comments}\nEnded on {date.today()} due to suspension.".strip()
        sub.save()

        # Create a new suspended record
        comment = f"Suspended via admin action by {request.user.username}."
        _create_new_subscription_record(sub, SubscriptionHistory.Status.SUSPENDED, comment, request.user)

        sub.clinic.status = ClinicOwnerProfile.Status.SUSPENDED
        sub.clinic.save()

@admin.action(description='Reactivate selected SUSPENDED subscriptions')
def reactivate_subscriptions(modeladmin, request, queryset):
    for sub in queryset.filter(status=SubscriptionHistory.Status.SUSPENDED):
        # End the current suspended subscription
        sub.end_date = date.today() - timedelta(days=1)
        sub.status = SubscriptionHistory.Status.ENDED
        sub.comments = f"{sub.comments}\nEnded on {date.today()} due to reactivation.".strip()
        sub.save()

        # Create a new active record
        comment = f"Reactivated via admin action by {request.user.username}."
        _create_new_subscription_record(sub, SubscriptionHistory.Status.ACTIVE, comment, request.user)

        sub.clinic.status = ClinicOwnerProfile.Status.ACTIVE
        sub.clinic.save()

@admin.action(description='Refund selected subscriptions')
def refund_subscriptions(modeladmin, request, queryset):
    for sub in queryset.filter(status__in=[SubscriptionHistory.Status.ACTIVE, SubscriptionHistory.Status.SUSPENDED, SubscriptionHistory.Status.UPCOMING]):
        sub.status = SubscriptionHistory.Status.REFUNDED
        sub.comments = f"Refunded via admin action by {request.user.username}."
        sub.save()
        if not sub.clinic.has_active_or_upcoming_subscription:
            sub.clinic.status = ClinicOwnerProfile.Status.ENDED
            sub.clinic.save()


class StatusListFilter(admin.SimpleListFilter):
    """
    Custom admin filter for the dynamic 'status' property on ClinicOwnerProfile.
    """
    title = 'status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return ClinicOwnerProfile.Status.choices

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            # This annotation logic must match the one in get_queryset
            if value == ClinicOwnerProfile.Status.INACTIVE:
                return queryset.filter(latest_status__isnull=True)
            if value == ClinicOwnerProfile.Status.ENDED:
                return queryset.filter(latest_status__in=[
                    SubscriptionHistory.Status.ENDED,
                    SubscriptionHistory.Status.REFUNDED,
                    SubscriptionHistory.Status.UPCOMING
                ])
            return queryset.filter(latest_status=value)
        return queryset


@admin.register(ClinicOwnerProfile)
class ClinicOwnerProfileAdmin(admin.ModelAdmin):
    list_display = ('clinic_name', 'clinic_owner_name', 'country', 'display_status', 'current_plan', 'days_left')
    list_filter = (StatusListFilter, 'country')
    search_fields = ('clinic_name', 'clinic_owner_name', 'user__username')
    inlines = [SubscriptionHistoryInline]
    readonly_fields = ('joined_date', 'added_by', 'active_subscription', 'current_plan', 'days_left', 'status')

    def get_queryset(self, request):
        """Optimize the queryset to prevent N+1 queries."""
        qs = super().get_queryset(request).select_related('user', 'country')

        # Annotate with the latest subscription status to be used by list_display and list_filter
        latest_sub_status = SubscriptionHistory.objects.filter(
            clinic=OuterRef('pk')
        ).order_by('-activation_date', '-pk').values('status')[:1]
        qs = qs.annotate(latest_status=Subquery(latest_sub_status))

        # Prefetch the active subscription for calculating days_left and current_plan
        qs = qs.prefetch_related(
            Prefetch(
                'subscription_history',
                queryset=SubscriptionHistory.objects.filter(status=SubscriptionHistory.Status.ACTIVE).select_related('subscription_type'),
                to_attr='_active_subscription_cached'
            )
        )
        return qs

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

    def display_status(self, obj):
        """
        Displays the clinic's status based on the annotated latest_status.
        """
        if not obj.latest_status:
            return ClinicOwnerProfile.Status.INACTIVE
        
        status_map = {
            SubscriptionHistory.Status.ACTIVE: ClinicOwnerProfile.Status.ACTIVE,
            SubscriptionHistory.Status.SUSPENDED: ClinicOwnerProfile.Status.SUSPENDED,
        }
        return status_map.get(obj.latest_status, ClinicOwnerProfile.Status.ENDED)
    display_status.short_description = 'Status'
    display_status.admin_order_field = 'latest_status' # Allow sorting by status


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

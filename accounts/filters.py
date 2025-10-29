# accounts/filters.py

from django.db.models import Subquery, OuterRef
import django_filters
from .models import ClinicOwnerProfile, SubscriptionType, SubscriptionHistory


class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    """
    Filter for a comma-separated list of numbers.
    Example: ?plan_id__in=1,2,3
    """
    pass


class ClinicOwnerProfileFilter(django_filters.FilterSet):
    """
    FilterSet for the ClinicOwnerProfile model.
    """
    status = django_filters.ChoiceFilter(
        choices=ClinicOwnerProfile.Status.choices,
        method='filter_by_status',
        label="Filter by clinic status"
    )
    plan_id__in = NumberInFilter(method='filter_by_plan_ids', label="Filter by one or more active plan IDs (comma-separated)")

    class Meta:
        model = ClinicOwnerProfile
        fields = [] # Status is now a custom method

    def filter_by_status(self, queryset, name, value):
        """
        Custom filter method to filter clinics by their dynamic status.
        """
        # Subquery to get the status of the latest subscription for each clinic
        latest_sub_status = SubscriptionHistory.objects.filter(
            clinic=OuterRef('pk')
        ).order_by('-activation_date', '-pk').values('status')[:1]

        # Annotate the queryset with the latest status
        queryset = queryset.annotate(latest_status=Subquery(latest_sub_status))

        if value == ClinicOwnerProfile.Status.INACTIVE:
            return queryset.filter(latest_status__isnull=True)
        
        if value == ClinicOwnerProfile.Status.ENDED:
            return queryset.filter(latest_status__in=[SubscriptionHistory.Status.ENDED, SubscriptionHistory.Status.REFUNDED, SubscriptionHistory.Status.UPCOMING])

        return queryset.filter(latest_status=value)

    def filter_by_plan_ids(self, queryset, name, value):
        """
        Custom filter to find clinics with an active subscription matching one of the given plan IDs.
        """
        if not value:
            return queryset
        
        return queryset.filter(subscription_history__status=SubscriptionHistory.Status.ACTIVE, subscription_history__subscription_type_id__in=value).distinct()
# accounts/filters.py

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
    status = django_filters.ChoiceFilter(choices=ClinicOwnerProfile.Status.choices)
    plan_id__in = NumberInFilter(method='filter_by_plan_ids', label="Filter by one or more active plan IDs (comma-separated)")

    class Meta:
        model = ClinicOwnerProfile
        fields = ['status']

    def filter_by_plan_ids(self, queryset, name, value):
        """
        Custom filter to find clinics with an active subscription matching one of the given plan IDs.
        """
        if not value:
            return queryset
        
        return queryset.filter(subscription_history__status=SubscriptionHistory.Status.ACTIVE, subscription_history__subscription_type_id__in=value).distinct()
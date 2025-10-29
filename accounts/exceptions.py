# accounts/exceptions.py

from rest_framework.exceptions import APIException
from rest_framework import status


class InactiveUserError(APIException):
    """Raised when a user account is inactive."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Your account has been deactivated. Please contact support.'
    default_code = 'inactive_user'


class InactiveClinicError(APIException):
    """Raised when a clinic is inactive, suspended, or ended."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'The clinic associated with this account is inactive. Please contact support.'
    default_code = 'inactive_clinic'


class SubscriptionExpiredError(APIException):
    """Raised when a clinic's subscription has expired."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'The clinic subscription has expired. Please renew to continue.'
    default_code = 'subscription_expired'


class OverlappingSubscriptionError(APIException):
    """Raised when trying to create overlapping subscriptions."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'An active or upcoming subscription already exists that overlaps with this date range.'
    default_code = 'overlapping_subscription'


class SuspendedClinicError(APIException):
    """Raised when trying to perform actions on a suspended clinic."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'This clinic has been suspended. Please contact support.'
    default_code = 'suspended_clinic'


class InvalidSubscriptionStatusError(APIException):
    """Raised when a subscription status transition is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid subscription status transition.'
    default_code = 'invalid_status_transition'


class ProtectedObjectInUseError(APIException):
    """Raised when trying to delete an object protected by a ForeignKey."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'This item cannot be deleted because it is currently in use by other records.'
    default_code = 'object_in_use'


class AccountLimitExceededError(APIException):
    """Raised when trying to create more accounts than allowed by subscription."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Account creation limit exceeded for current subscription plan.'
    default_code = 'account_limit_exceeded'


class PaginationBypassError(APIException):
    """Raised when trying to bypass pagination without proper authorization."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Pagination bypass not allowed. You must be a site owner to retrieve all data without pagination.'
    default_code = 'pagination_bypass_not_allowed'


class CountryInUseError(APIException):
    """Raised when trying to delete a country that has associated clinics."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Cannot delete country because clinics are assigned to it.'
    default_code = 'country_in_use'

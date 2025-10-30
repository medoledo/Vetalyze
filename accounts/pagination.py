# accounts/pagination.py

from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .exceptions import PaginationBypassError


class ClinicPagination(PageNumberPagination):
    """
    Custom pagination that allows site owners to bypass pagination.
    Use query parameter 'all=true' to get all results (site owners only).
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """
        Override to allow site owners to bypass pagination.
        """
        # Check if user wants to bypass pagination
        all_param = request.query_params.get('all', 'false').lower() == 'true'

        if all_param:
            # Only site owners can bypass pagination
            if not hasattr(request.user, 'role') or request.user.role != 'SITE_OWNER':
                raise PaginationBypassError()

            # Return all results without pagination
            self.page = None
            self.request = request
            return list(queryset)

        # Use normal pagination
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        """
        Override to handle non-paginated responses.
        """
        if self.page is None:
            return Response(data)
        return super().get_paginated_response(data)

    def get_paginated_response_schema(self, schema):
        """
        Update schema to include 'all' parameter.
        """
        schema = super().get_paginated_response_schema(schema)
        schema['properties']['all'] = {
            'type': 'boolean',
            'description': 'Set to true to bypass pagination (site owners only)',
            'default': False
        }
        return schema

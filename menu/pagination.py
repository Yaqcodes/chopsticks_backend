"""Pagination for public catalog list endpoints (honours client ?page_size=)."""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class MenuItemPageNumberPagination(PageNumberPagination):
    """
    ZMall catalog expects a stable page size (default 25) and sends ?page_size= from the app.
    DRF's default PageNumberPagination ignores page_size unless page_size_query_param is set.
    """

    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        page_size = self.page.paginator.per_page if self.page is not None else None
        return Response(
            {
                'count': self.page.paginator.count if self.page is not None else len(data),
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'page_size': page_size,
                'results': data,
            }
        )

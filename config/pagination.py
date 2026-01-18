from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Standard pagination for list endpoints.
    
    Query params:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 10, max: 100)
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

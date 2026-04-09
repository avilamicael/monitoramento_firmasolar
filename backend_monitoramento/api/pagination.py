from rest_framework.pagination import PageNumberPagination


class PaginacaoSnapshots(PageNumberPagination):
    """Paginacao para endpoints de historico de snapshots (D-06)."""

    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500

import django_filters
from usinas.models import Inversor


class InversorFilterSet(django_filters.FilterSet):
    """Filtros para listagem de inversores (D-03)."""

    usina = django_filters.UUIDFilter(field_name='usina__id')
    provedor = django_filters.CharFilter(field_name='usina__provedor', lookup_expr='exact')
    modelo = django_filters.CharFilter(field_name='modelo', lookup_expr='icontains')

    class Meta:
        model = Inversor
        fields = ['usina', 'provedor', 'modelo']

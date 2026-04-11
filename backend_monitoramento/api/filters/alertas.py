import django_filters
from alertas.models import Alerta


class AlertaFilterSet(django_filters.FilterSet):
    """Filtros para listagem de alertas (D-03)."""

    estado = django_filters.CharFilter(field_name='estado', lookup_expr='exact')
    nivel = django_filters.CharFilter(field_name='nivel', lookup_expr='exact')
    origem = django_filters.CharFilter(field_name='origem', lookup_expr='exact')
    categoria = django_filters.CharFilter(field_name='categoria', lookup_expr='exact')
    provedor = django_filters.CharFilter(field_name='usina__provedor', lookup_expr='exact')
    usina = django_filters.UUIDFilter(field_name='usina__id')
    busca = django_filters.CharFilter(method='filtrar_busca')

    class Meta:
        model = Alerta
        fields = ['estado', 'nivel', 'origem', 'categoria', 'provedor', 'usina', 'busca']

    def filtrar_busca(self, queryset, name, value):
        """Busca por texto livre em nome da usina, mensagem e equipamento."""
        from django.db.models import Q
        return queryset.filter(
            Q(usina__nome__icontains=value) |
            Q(mensagem__icontains=value) |
            Q(equipamento_sn__icontains=value)
        )

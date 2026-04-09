import django_filters
from django.utils import timezone
from usinas.models import Usina, GarantiaUsina


class UsinaFilterSet(django_filters.FilterSet):
    """
    Filtros para listagem de usinas (D-03, D-04).

    status_garantia e filtro customizado porque data_fim e @property no model
    e nao pode ser usada diretamente em ORM filter.
    """

    provedor = django_filters.CharFilter(field_name='provedor', lookup_expr='exact')
    ativo = django_filters.BooleanFilter(field_name='ativo')
    status_garantia = django_filters.CharFilter(method='filtrar_status_garantia')

    class Meta:
        model = Usina
        fields = ['provedor', 'ativo']

    def filtrar_status_garantia(self, queryset, name, value):
        """
        Filtro customizado por status de garantia (D-04).

        CRITICO: data_fim e @property, NAO coluna SQL.
        Para 'sem_garantia': ORM puro (garantia__isnull=True) — eficiente.
        Para 'ativa'/'vencida': avalia propriedade Python por garantia existente,
        depois filtra usinas pelo ID resultante. Volume controlado (poucas garantias).

        Valores nao reconhecidos retornam queryset inalterado — sem erro, sem bypass (T-2-06).
        """
        hoje = timezone.now().date()

        if value == 'sem_garantia':
            return queryset.filter(garantia__isnull=True)

        elif value == 'ativa':
            ids_ativas = [
                g.usina_id
                for g in GarantiaUsina.objects.select_related('usina').all()
                if g.data_fim >= hoje
            ]
            return queryset.filter(id__in=ids_ativas)

        elif value == 'vencida':
            ids_vencidas = [
                g.usina_id
                for g in GarantiaUsina.objects.select_related('usina').all()
                if g.data_fim < hoje
            ]
            return queryset.filter(id__in=ids_vencidas)

        # Valor nao reconhecido — retorna sem filtro (T-2-06)
        return queryset

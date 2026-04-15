from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import PingView, LogColetaListView
from .views.usinas import UsinaViewSet
from .views.garantias import GarantiaListView
from .views.inversores import InversorViewSet
from .views.alertas import AlertaViewSet
from .views.configuracoes import ConfiguracaoSistemaView
from .views.provedores import CredencialProvedorViewSet, ProvedoresMetaView
from .views.analytics import (
    PotenciaMediaView, RankingFabricantesView, MapaUsinasView,
    AlertasResumoView, GeracaoDiariaView, EnergiaResumoView,
)

router = DefaultRouter()
router.register('usinas', UsinaViewSet, basename='usina')
router.register('inversores', InversorViewSet, basename='inversor')
router.register('alertas', AlertaViewSet, basename='alerta')
router.register('provedores', CredencialProvedorViewSet, basename='provedor')

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('ping/', PingView.as_view(), name='api_ping'),
    path('garantias/', GarantiaListView.as_view(), name='garantia-list'),
    path('coleta/logs/', LogColetaListView.as_view(), name='log-coleta-list'),
    path('configuracoes/', ConfiguracaoSistemaView.as_view(), name='configuracoes-detail'),
    path('provedores/meta/', ProvedoresMetaView.as_view(), name='provedores-meta'),
    path('analytics/potencia/', PotenciaMediaView.as_view(), name='analytics-potencia'),
    path('analytics/ranking-fabricantes/', RankingFabricantesView.as_view(), name='analytics-ranking'),
    path('analytics/mapa/', MapaUsinasView.as_view(), name='analytics-mapa'),
    path('analytics/alertas-resumo/', AlertasResumoView.as_view(), name='analytics-alertas-resumo'),
    path('analytics/geracao-diaria/', GeracaoDiariaView.as_view(), name='analytics-geracao-diaria'),
    path('analytics/energia-resumo/', EnergiaResumoView.as_view(), name='analytics-energia-resumo'),
    path('', include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import PingView, LogColetaListView
from .views.usinas import UsinaViewSet
from .views.garantias import GarantiaListView
from .views.inversores import InversorViewSet
from .views.alertas import AlertaViewSet

router = DefaultRouter()
router.register('usinas', UsinaViewSet, basename='usina')
router.register('inversores', InversorViewSet, basename='inversor')
router.register('alertas', AlertaViewSet, basename='alerta')

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('ping/', PingView.as_view(), name='api_ping'),
    path('garantias/', GarantiaListView.as_view(), name='garantia-list'),
    path('coleta/logs/', LogColetaListView.as_view(), name='log-coleta-list'),
    path('', include(router.urls)),
]

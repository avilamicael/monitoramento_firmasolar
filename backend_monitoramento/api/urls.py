from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import PingView
from .views.usinas import UsinaViewSet
from .views.garantias import GarantiaListView

router = DefaultRouter()
router.register('usinas', UsinaViewSet, basename='usina')

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('ping/', PingView.as_view(), name='api_ping'),
    path('garantias/', GarantiaListView.as_view(), name='garantia-list'),
    path('', include(router.urls)),
]

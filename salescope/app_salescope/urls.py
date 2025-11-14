from django.urls import include, path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
"""
router.register('supers', SuperViewSet,)
router.register('productos', ProductoViewSet,)
router.register('producto_super', ProductoSuperViewSet,)
router.register('ventas', VentaViewSet,)
router.register('scrapping', ScrappingDataViewSet,)
"""
urlpatterns = [
    # --- Rutas principales ---
    #path('', include(router.urls)),  # ViewSet principal para CRUD de ScrappingData
    path("choose_super/", views.choose_super, name="choose_super"),
    path("data/over_time/", views.data_over_time, name="data_over_time"),
    path("data/over_price/", views.data_over_price, name="data_over_price"),
]
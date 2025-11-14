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
    path('super', views.get_supers, name="get_supers"),
    path('super/<int:super_id>', views.get_prods_by_super, name="get_prods"),
    path('super/<int:super_id>/<int:prod_id>/time', views.get_prod_time_data, name="get_prod_time_data"),
    path('super/<int:super_id>/<int:prod_id>/price', views.get_prod_price_data, name="get_prod_time_data"),

    path("choose_super/", views.choose_super, name="choose_super"),
    path("data/over_time/", views.data_over_time, name="data_over_time"),
    path("data/over_price/", views.data_over_price, name="data_over_price"),
]
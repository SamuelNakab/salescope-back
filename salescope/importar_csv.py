import os
import django

# ============================
# 1. CONFIGURAR ENTORNO DJANGO
# ============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "salescope.settings")
django.setup()

# ============================
# 2. IMPORTAR FUNCIONES EXISTENTES
# ============================
from app_salescope.views import (
    cargar_productos_y_fuentes_desde_csv,
    productoPrecios_to_pg
)

# ============================
# 3. DEFINIR RUTA DEL CSV
# ============================
CSV_PATH = os.path.join(BASE_DIR, "..", "csvs_simulated", "productos_2025-11-")


# ============================
# 4. EJECUCIÓN PRINCIPAL
# ============================
if __name__ == "__main__":
    print("🚀 Iniciando carga desde CSV...\n")

    try:
        print("📦 Cargando productos y fuentes...")
        resultado1 = cargar_productos_y_fuentes_desde_csv(CSV_PATH)
        print(f"✅ {resultado1['mensaje']}")
        print(f"   → {resultado1['fuentes_insertadas']} fuentes insertadas")
        print(f"   → {resultado1['productos_insertados']} productos insertados\n")

        print("💾 Cargando histórico de precios...")
        resultado2 = productoPrecios_to_pg(CSV_PATH)
        print(f"✅ {resultado2['mensaje']}")
        print(f"   → {resultado2['precios_insertados']} precios insertados\n")

        print("🎯 Proceso completado correctamente.")

    except Exception as e:
        print("❌ Error durante la importación:")
        print(e)
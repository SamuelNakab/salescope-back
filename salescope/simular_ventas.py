import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "salescope.settings")
django.setup()

from app_salescope.views import simular_tabla_ventas

if __name__ == "__main__":
    simular_tabla_ventas()

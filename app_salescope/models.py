from django.db import models

# Create your models here.


class Productos(models.Model):
    name = models.CharField(max_length=100)
    marca = models.CharField(max_length=100)
    fuente = models.ForeignKey('Fuente', on_delete=models.SET_NULL, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    
    promocion_existente = models.BooleanField(default=False)
    precio_descontado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True, blank=True  # puede no existir descuento
    )
    
    promocion = models.CharField(
        max_length=100,
        null=True, blank=True  # puede estar vacío
    )
    
    def __str__(self):
        return f"{self.marca} - {self.name}"

class Fuente(models.Model):
    id = models.AutoField(primary_key=True)
    super = models.CharField(max_length=100)

    def __str__(self):
        return self.super
    
"""class Promocion(models.Model):
    id = models.AutoField(primary_key=True)
    ean = models.ForeignKey('Productos', on_delete=models.CASCADE)
    fuente = models.ForeignKey('Fuente', on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    descuento = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.ean.descripcion} - {self.fuente.super} ({self.descuento}%)"""
    
class ProductoPrecio(models.Model):
    id = models.AutoField(primary_key=True) 
    fuente = models.ForeignKey('Fuente', on_delete=models.SET_NULL, null=True)   
    name = models.CharField(max_length=100)
    marca = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()

    # Nuevos campos
    promocion_existente = models.BooleanField(default=False)
    precio_descontado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True, blank=True  # puede no existir descuento
    )
    promocion = models.CharField(
        max_length=100,
        null=True, blank=True  # puede estar vacío
    )

    def __str__(self):
        fuente_name = self.fuente.super if self.fuente else "Fuente eliminada"

        promo_text = f"Promo: {self.promocion} (${self.precio_descontado})" if self.promocion_existente else "Sin promo"
        return f"{self.name} - {fuente_name} (${self.precio}) | {promo_text}"



class Venta(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.ForeignKey('Productos', on_delete=models.SET_NULL, null=True)
    fuente = models.ForeignKey('Fuente', on_delete=models.SET_NULL, null=True)
    cantidad = models.DecimalField(max_digits=6, decimal_places=2)
    fecha = models.DateField()

    def __str__(self):
        return f"Venta de {self.cantidad} unidades de {self.name} en {self.fuente.super} ({self.fecha})"



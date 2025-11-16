from decimal import Decimal
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from decimal import Decimal
import pandas as pd
import numpy as np
from .models import Productos, Fuente, ProductoPrecio, Venta
import datetime
from django.db import transaction
import random
from collections import defaultdict

# ==========================================================
# 1) UTILITIES FUNCTIONS
# ==========================================================

# (acá irán tus funciones utilitarias si después agregás)


# ==========================================================
# 2) DATABASE FUNCTIONS
# ==========================================================

def cargar_productos_y_fuentes_desde_csv(file_path):
    """
    Importa productos y fuentes desde un archivo CSV a la base de datos PostgreSQL.
    No borra tablas: agrega fuentes y productos nuevos y actualiza los existentes.
    """
    df = pd.read_csv(file_path)

    df = df.rename(columns={
        "name": "nombre",
        "price": "precio",
        "discprice": "precio_desc",
        "ecomerce": "fuente",
        "brand": "marca",
        "datefield": "fecha"
    })

    # --- Fuentes ---
    fuentes_unicas = df["fuente"].dropna().unique()
    fuentes_existentes = set(Fuente.objects.values_list('super', flat=True))

    nuevas_fuentes = [f for f in fuentes_unicas if f not in fuentes_existentes]
    fuente_objs = [Fuente(super=f) for f in nuevas_fuentes]
    if fuente_objs:
        Fuente.objects.bulk_create(fuente_objs)

    fuentes_db = {f.super: f for f in Fuente.objects.all()}

    # --- Productos ---
    productos_existentes = {
        (p.name, p.marca, p.fuente_id): p
        for p in Productos.objects.all()
    }

    nuevos_productos = []
    actualizados = 0

    for _, row in df.iterrows():
        fuente_obj = fuentes_db.get(row["fuente"])
        if not fuente_obj:
            continue  # seguridad

        precio = float(row.get("precio", 0))
        precio_desc = row.get("precio_desc", None)

        # Determinar si tiene promoción
        if pd.notna(precio_desc) and precio_desc != "" and float(precio_desc) < precio:
            promocion_existente = True
            promocion = "Descuento"
            precio_descontado = float(precio_desc)
        else:
            promocion_existente = False
            promocion = None
            precio_descontado = None

        key = (row["nombre"], row["marca"], fuente_obj.id)

        if key in productos_existentes:
            # Si ya existe → actualizar precios y promoción
            producto = productos_existentes[key]
            producto.precio = precio
            producto.promocion_existente = promocion_existente
            producto.precio_descontado = precio_descontado
            producto.promocion = promocion
            producto.save(update_fields=[
                "precio",
                "promocion_existente",
                "precio_descontado",
                "promocion"
            ])
            actualizados += 1
        else:
            # Si no existe → crear nuevo producto
            nuevos_productos.append(
                Productos(
                    name=row["nombre"],
                    marca=row["marca"],
                    fuente=fuente_obj,
                    precio=precio,
                    promocion_existente=promocion_existente,
                    precio_descontado=precio_descontado,
                    promocion=promocion
                )
            )

    if nuevos_productos:
        Productos.objects.bulk_create(nuevos_productos)

    return {
        "fuentes_insertadas": len(fuente_objs),
        "productos_insertados": len(nuevos_productos),
        "productos_actualizados": actualizados,
        "mensaje": "Carga completa: productos nuevos agregados y existentes actualizados."
    }


def productoPrecios_to_pg(file_path):
    """
    Carga histórico de precios a la tabla ProductoPrecio sin borrar los registros existentes.

    Lógica:
    - Lee un CSV con columnas: name, price, discprice, ecomerce, brand, datefield
    - Inserta una fila en ProductoPrecio por cada línea del CSV
    - Detecta promociones si discprice < price
    - Calcula el porcentaje de descuento con la fórmula:
        (precio_original - precio_desc) / precio_original
    """

    df = pd.read_csv(file_path)

    df = df.rename(columns={
        "name": "nombre",
        "price": "precio",
        "discprice": "precio_desc",
        "ecomerce": "fuente",
        "brand": "marca",
        "datefield": "fecha"
    })

    fuentes_db = {f.super: f for f in Fuente.objects.all()}

    producto_precio_objs = []

    for _, row in df.iterrows():

        precio = float(row.get("precio", 0))
        precio_desc = row.get("precio_desc", None)

        if pd.notna(precio_desc) and precio_desc != "" and float(precio_desc) < precio:
            precio_descontado = float(precio_desc)
            promocion_existente = True
            promocion = (precio - precio_descontado) / precio
        else:
            promocion_existente = False
            precio_descontado = None
            promocion = None

        fuente_obj = fuentes_db.get(row["fuente"])

        if not fuente_obj:
            continue

        producto_precio_objs.append(
            ProductoPrecio(
                name=row["nombre"],
                marca=row["marca"],
                fuente=fuente_obj,
                precio=precio,
                fecha=row["fecha"],
                promocion_existente=promocion_existente,
                precio_descontado=precio_descontado,
                promocion=promocion
            )
        )

    ProductoPrecio.objects.bulk_create(producto_precio_objs, batch_size=1000)

    return {
        "precios_insertados": len(producto_precio_objs),
        "mensaje": "Histórico de precios actualizado sin borrar registros previos."
    }


def simular_tabla_ventas():
    """
    Simula la tabla de ventas generando una fila por cada producto existente.

    - Usa el nombre y la fuente del producto desde la tabla Productos.
    - Simula la cantidad vendida en millones, entre 0.1 y 3, 
      dependiendo del precio y si el producto tiene descuento.
    - Usa una fecha fija definida al principio del código.
    """

    # --- FECHA DE SIMULACIÓN ---
    fecha = datetime.date(2025, 11,)  # Cambiá esta fecha si querés

    print(f"📆 Simulando ventas para la fecha {fecha}...")

    # --- Obtener todos los productos ---
    productos = Productos.objects.all()

    if not productos.exists():
        print("⚠️ No hay productos en la base de datos.")
        return

    ventas_creadas = []

    # --- Calcular rango de precios ---
    precios = [p.precio for p in productos if p.precio is not None]
    min_precio = min(precios)
    max_precio = max(precios)
    rango = max_precio - min_precio if max_precio > min_precio else 1

    def categorizar_precio(precio):
        """Clasifica un precio en una categoría de 1 (menos vendida) a 5 (más vendida)."""
        normalizado = (precio - min_precio) / rango
        if normalizado < 0.2:
            return 5
        elif normalizado < 0.4:
            return 4
        elif normalizado < 0.6:
            return 3
        elif normalizado < 0.8:
            return 2
        else:
            return 1

    def simular_cantidad(categoria, tiene_descuento):
        """Devuelve una cantidad aleatoria según la categoría y descuento."""
        rangos = {
            1: (0.1, 0.8),
            2: (0.4, 1.5),
            3: (0.7, 2.0),
            4: (1.0, 2.5),
            5: (1.5, 3.0),
        }
        minimo, maximo = rangos[categoria]
        cantidad = random.uniform(minimo, maximo)

        # Si tiene descuento → vende más (entre +10% y +25%)
        if tiene_descuento:
            cantidad *= random.uniform(1.1, 1.25)

        return round(cantidad, 3)

    # --- Crear las ventas simuladas ---
    for producto in productos:
        if producto.precio is None:
            continue

        tiene_descuento = (
            producto.promocion_existente
            and producto.precio_descontado is not None
            and producto.precio_descontado < producto.precio
        )
        
        categoria = categorizar_precio(producto.precio)
        cantidad = simular_cantidad(categoria, tiene_descuento)

        venta = Venta(
            name=producto,
            fuente=producto.fuente,
            cantidad=cantidad,
            fecha=fecha,
        )
        ventas_creadas.append(venta)

    # --- Guardar en la base de datos ---
    with transaction.atomic():
        Venta.objects.bulk_create(ventas_creadas)

    print(f"✅ Se generaron {len(ventas_creadas)} ventas simuladas para {fecha}.")
# ==========================================================
# 3) API VIEWS
# ==========================================================

# (Acá después van tus @api_view endpoints)
@api_view(["GET" , "POST"])
def choose_super(request):
    if request.method == "GET":
        """Endpoint GET para elegir supermercado"""
        # obtener todas las filas de la tabla Fuente como diccionarios
        supers = list(Fuente.objects.values())

        return Response(supers)
    
    elif request.method == "POST":
        """
        Endpoint POST para elegir supermercado y devolver productos filtrados
        """
        # 1. Leer el super enviado desde el front
        super_elegido = request.data.get("super")

        # Validación básica
        if not super_elegido:
            return Response({"error": "Debe enviar un supermercado"}, status=400)

        # 2. Obtener el id de la fuente correspondiente
        try:
            fuente_obj = Fuente.objects.get(super=super_elegido)
            fuente_id = fuente_obj.id
        except Fuente.DoesNotExist:
            return Response({"error": "Supermercado no encontrado"}, status=404)

        # 3. Filtrar productos por fuente_id
        productos = list(Productos.objects.filter(fuente_id=fuente_id).values())

        # 4. Enviar la lista al front
        return Response(productos)


@api_view(["POST"])
def data_over_time(request):
    """
    Viene un super, una cantidad de fechas y un name.
    -------------------------------------------------
    Devuelve las ventas agrupadas por fecha junto con su precio.
    """
    super_name = request.data.get("super")
    product_name = request.data.get("producto")
    cantidad = request.data.get("cantidad", 8)
    
    if not super_name or not product_name:
        return Response({"error": "Debe enviar 'super' y 'producto'"}, status=400)

    # --- Buscar la fuente ---
    try:
        fuente_obj = Fuente.objects.get(super=super_name)
    except Fuente.DoesNotExist:
        return Response({"error": f"No tenemos datos de este supermercado: {super_name}"}, status=404)

    # --- Buscar el producto dentro de la fuente ---
    try:
        producto_obj = Productos.objects.get(
            name=product_name,
            fuente_id=fuente_obj.id
        )
    except Productos.DoesNotExist:
        return Response({"error": f"No existe el producto: {product_name} en el supermercado {super_name}"}, status=404)

    # --- Ventas por fecha ---
    ventas_qs = Venta.objects.filter(
        fuente_id=fuente_obj.id,
        name_id=producto_obj.id
    ).values("fecha", "cantidad")

    if not ventas_qs.exists():
        return Response([], status=200)

    df = pd.DataFrame(list(ventas_qs))
    df = df.groupby("fecha", as_index=False)["cantidad"].sum()

    # --- Precios por fecha ---
    precios_qs = ProductoPrecio.objects.filter(
        fuente_id=fuente_obj.id,
        name=producto_obj.name
    ).values(
        "fecha", "precio", "promocion_existente", "precio_descontado", "promocion"
    )

    df_precios = pd.DataFrame(list(precios_qs))
    if df_precios.empty:
        df_precios = pd.DataFrame(columns=["fecha", "precio", "promocion_existente", "precio_descontado", "promocion"])
    else:
        # --- Normalizar precios y promociones ---
        df_precios["precio_descontado"] = df_precios.apply(
            lambda row: row["precio"] if not row["promocion_existente"] else row["precio_descontado"],
            axis=1
        )
        df_precios["promocion"] = df_precios.apply(
            lambda row: "Ninguna" if not row["promocion_existente"] else row["promocion"],
            axis=1
        )

    # --- Merge ventas y precios ---
    df_final = pd.merge(df, df_precios, on="fecha", how="left").sort_values(by="fecha")
    
    # --- Convertir Decimals a float y reemplazar valores no serializables ---
    for col in df_final.columns:
        df_final[col] = df_final[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

    df_final = df_final.replace([np.inf, -np.inf], None)
    df_final = df_final.where(pd.notnull(df_final), None)

    # --- Limitar a las últimas n fechas ---
    try:
        cantidad = int(cantidad)
        df_final = df_final.tail(cantidad)
    except ValueError:
        pass

    data = df_final.to_dict(orient="records")
    return Response(data)


@api_view(["POST"])
def data_over_price(request):
    """
    Viene un super, una cantidad y un name
    -------------------------------------------------
    Devuelve las ventas que tuvo un producto en cada precio distinto,
    con cantidad total vendida, días vigentes y promedio diario.
    """
    super_name = request.data.get("super")
    product_name = request.data.get("producto")

    if not super_name or not product_name:
        return Response({"error": "Debe enviar 'super' y 'producto'"}, status=400)

    # --- Buscar el producto por nombre ---
    try:
        producto = Productos.objects.get(name=product_name, fuente__super=super_name)
    except Productos.DoesNotExist:
        return Response({"error": f"No existe: {product_name} en {super_name}"}, status=404)

    # --- 1. Obtener precios históricos del producto ---
    precios_qs = ProductoPrecio.objects.filter(
        fuente__super=super_name,
        name=product_name
    ).values("fecha", "precio", "precio_descontado").order_by("fecha")

    if not precios_qs.exists():
        return Response([], status=200)

    df_precios = pd.DataFrame(list(precios_qs))
    df_precios = df_precios.sort_values(by="fecha").reset_index(drop=True)

    # --- 2. Calcular períodos de vigencia ---
    df_precios["fecha_fin"] = df_precios["fecha"].shift(-1)
    df_precios["fecha_fin"].fillna(datetime.date.today(), inplace=True)

    resultados = []

    for _, row in df_precios.iterrows():
        fecha_inicio = row["fecha"]
        fecha_fin = row["fecha_fin"]
        precio = float(row["precio"])

        # --- 3. Ventas dentro del rango ---
        ventas_qs = Venta.objects.filter(
            fuente__super=super_name,
            name=producto,
            fecha__gte=fecha_inicio,
            fecha__lt=fecha_fin
        ).values("cantidad")

        total_vendido = sum(v["cantidad"] for v in ventas_qs) if ventas_qs else 0

        dias_vigentes = max((fecha_fin - fecha_inicio).days, 1)
        promedio_diario = round(total_vendido / dias_vigentes, 2)

        resultados.append({
            "precio": precio,
            "precio_descontado": float(row["precio_descontado"]) if row["precio_descontado"] else None,
            "fecha_inicio": str(fecha_inicio),
            "fecha_fin": str(fecha_fin),
            "dias_vigentes": dias_vigentes,
            "cantidad_total_vendida": total_vendido,
            "promedio_diario_ventas": promedio_diario
        })

    return Response(resultados)



# ==========================================================
# 4) API VIEWS NEW
# =============================================

@api_view(["GET"])
def get_supers(request):
    """Endpoint GET para elegir supermercado"""
    # obtener todas las filas de la tabla Fuente como diccionarios
    supers = list(Fuente.objects.values())

    return Response(supers)


@api_view(["GET"])
def get_prods_by_super(request, super_id):
    """
    Endpoint GET para elegir supermercado y devolver productos filtrados
    """
    print(super_id)
    # Validación básica (opcional pero recomendable)
    if not super_id:
        return Response({"error": "Debe enviar un supermercado"}, status=400)

    # 2. Filtrar productos por el campo fuente
    productos = list(Productos.objects.filter(fuente_id=super_id).values())

    # 3. Enviar la lista al front
    return Response(productos)


#TERMINAR ESTA FUNCION, CAMBIARLA PARA QUE USE IDS EN VEZ DE NAMES
@api_view(["GET"])
def get_prod_time_data(request, super_id, prod_id):
    """
    Igual que data_over_time pero usando IDs y query param ?cantidad=
    - super_id: Fuente.id (en la URL)
    - prod_id: Productos.id (en la URL)
    - cantidad: opcional en query params (por defecto 8)
    """
    cantidad = request.GET.get("cantidad", 8)

    if not super_id or not prod_id:
        return Response({"error": "Debe enviar 'super' y 'producto'"}, status=400)

    # --- Buscar la fuente por id ---
    try:
        fuente_obj = Fuente.objects.get(id=super_id)
    except Fuente.DoesNotExist:
        return Response({"error": f"No tenemos datos de este supermercado id: {super_id}"}, status=404)

    # --- Buscar el producto por id y que pertenezca a la fuente ---
    try:
        producto_obj = Productos.objects.get(id=prod_id, fuente_id=fuente_obj.id)
    except Productos.DoesNotExist:
        return Response({"error": f"No existe el producto id: {prod_id} en el supermercado id {super_id}"}, status=404)

    # --- Ventas por fecha ---
    ventas_qs = Venta.objects.filter(
        fuente_id=fuente_obj.id,
        name_id=producto_obj.id
    ).values("fecha", "cantidad")

    if not ventas_qs.exists():
        return Response([], status=200)

    df = pd.DataFrame(list(ventas_qs))
    df = df.groupby("fecha", as_index=False)["cantidad"].sum()

    # --- Precios por fecha ---
    precios_qs = ProductoPrecio.objects.filter(
        fuente_id=fuente_obj.id,
        name=producto_obj.name
    ).values(
        "fecha", "precio", "promocion_existente", "precio_descontado", "promocion"
    )

    df_precios = pd.DataFrame(list(precios_qs))
    if df_precios.empty:
        df_precios = pd.DataFrame(columns=["fecha", "precio", "promocion_existente", "precio_descontado", "promocion"])
    else:
        # --- Normalizar precios y promociones ---
        df_precios["precio_descontado"] = df_precios.apply(
            lambda row: row["precio"] if not row["promocion_existente"] else row["precio_descontado"],
            axis=1
        )
        df_precios["promocion"] = df_precios.apply(
            lambda row: "Ninguna" if not row["promocion_existente"] else row["promocion"],
            axis=1
        )

    # --- Merge ventas y precios ---
    df_final = pd.merge(df, df_precios, on="fecha", how="left").sort_values(by="fecha")
    
    # --- Convertir Decimals a float y reemplazar valores no serializables ---
    for col in df_final.columns:
        df_final[col] = df_final[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

    df_final = df_final.replace([np.inf, -np.inf], None)
    df_final = df_final.where(pd.notnull(df_final), None)

    # --- Limitar a las últimas n fechas ---
    try:
        cantidad = int(cantidad)
        df_final = df_final.tail(cantidad)
    except (ValueError, TypeError):
        pass

    data = df_final.to_dict(orient="records")
    return Response(data)
# ...existing code...

# Response format:
# - Returns a JSON array of objects (one per fecha), example:
#   [
#     {
#       "fecha": "2025-11-01",               # fecha (string YYYY-MM-DD)
#       "cantidad": 12.34,                   # cantidad vendida (float)
#       "precio": 5.99,                      # precio registrado ese día (float) o null
#       "promocion_existente": true,         # bool or null
#       "precio_descontado": 4.99,           # float or null
#       "promocion": "Descuento"             # string or null ("Ninguna" si no hay)
#     },
#     ...
#   ]



#TERMINAR ESTA FUNCION, CAMBIARLA PARA QUE USE IDS EN VEZ DE NAMES
@api_view(["GET"])
def get_prod_price_data(request, super_id, prod_id):
    """
    Igual que data_over_price pero usando IDs en la URL en vez de nombre y POST body.
    Agrupa TODOS los períodos con el mismo precio y descuento (no solo consecutivos).
    - super_id: Fuente.id en la URL
    - prod_id: Productos.id en la URL
    """
    # --- Validación básica ---
    if not super_id or not prod_id:
        return Response({"error": "Debe enviar 'super' y 'producto' en la URL"}, status=400)

    # --- Buscar la fuente por id ---
    try:
        fuente_obj = Fuente.objects.get(id=super_id)
    except Fuente.DoesNotExist:
        return Response({"error": f"No tenemos datos de este supermercado id: {super_id}"}, status=404)

    # --- Buscar el producto por id y que pertenezca a la fuente ---
    try:
        producto = Productos.objects.get(id=prod_id, fuente_id=fuente_obj.id)
    except Productos.DoesNotExist:
        return Response({"error": f"No existe el producto id: {prod_id} en el supermercado id {super_id}"}, status=404)

    # --- 1. Obtener precios históricos del producto ---
    precios_qs = ProductoPrecio.objects.filter(
        fuente_id=fuente_obj.id,
        name=producto.name
    ).values("fecha", "precio", "precio_descontado").order_by("fecha")

    if not precios_qs.exists():
        return Response([], status=200)

    df_precios = pd.DataFrame(list(precios_qs))
    df_precios = df_precios.sort_values(by="fecha").reset_index(drop=True)

    # --- 2. Calcular períodos de vigencia ---
    df_precios["fecha_fin"] = df_precios["fecha"].shift(-1)
    df_precios["fecha_fin"].fillna(datetime.date.today(), inplace=True)

    # --- 3. Calcular datos de ventas para cada período ---
    periodos = []

    for _, row in df_precios.iterrows():
        fecha_inicio = row["fecha"]
        fecha_fin = row["fecha_fin"]
        precio = float(row["precio"])
        precio_descontado = float(row["precio_descontado"]) if row["precio_descontado"] else None

        # Ventas dentro del rango
        ventas_qs = Venta.objects.filter(
            fuente_id=fuente_obj.id,
            name=producto,
            fecha__gte=fecha_inicio,
            fecha__lt=fecha_fin
        ).values("cantidad")

        total_vendido = sum(v["cantidad"] for v in ventas_qs) if ventas_qs else 0
        dias_vigentes = max((fecha_fin - fecha_inicio).days, 1)

        periodos.append({
            "precio": precio,
            "precio_descontado": precio_descontado,
            "dias_vigentes": dias_vigentes,
            "cantidad_total_vendida": total_vendido
        })

    # --- 4. Agrupar TODOS los períodos con mismo precio y descuento (no solo consecutivos) ---

    
    grupos = defaultdict(lambda: {
        "dias_vigentes": 0,
        "cantidad_total_vendida": 0
    })
    
    for periodo in periodos:
        # Crear clave basada en precio y precio_descontado
        clave = (periodo["precio"], periodo["precio_descontado"])
        
        grupos[clave]["dias_vigentes"] += periodo["dias_vigentes"]
        grupos[clave]["cantidad_total_vendida"] += periodo["cantidad_total_vendida"]
    
    # --- 5. Convertir a lista y calcular promedio_diario_ventas ---
    resultados = []
    
    for (precio, precio_descontado), datos in grupos.items():
        promedio_diario = round(datos["cantidad_total_vendida"] / datos["dias_vigentes"], 2)
        
        resultados.append({
            "precio": precio,
            "precio_descontado": precio_descontado,
            "dias_disponible": datos["dias_vigentes"],
            "cantidad_total_vendida": datos["cantidad_total_vendida"],
            "promedio_diario_ventas": promedio_diario
        })
    
    return Response(resultados)
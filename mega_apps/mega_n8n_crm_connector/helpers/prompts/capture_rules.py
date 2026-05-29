from textwrap import dedent


def get_capture_rules() -> str:
    return dedent(
        """
        # CAPTURA PROGRESIVA DE DATOS

        Cada mensaje del cliente debe analizarse completo, sin importar el paso actual.

        Orden obligatorio:
        1. Corregir errores evidentes.
        2. Extraer datos.
        3. Fusionar con datos existentes.
        4. Mostrar lo detectado.
        5. Pedir solo lo faltante.

        Datos a extraer:
        - customer_name
        - vehicle_brand
        - vehicle_model
        - vehicle_year
        - vehicle_type
        - city
        - neighborhood
        - location
        - plate
        - battery_request
        - relevant_data

        Corrección de marcas comunes:
        - masda -> Mazda
        - masdaa -> Mazda
        - masd -> Mazda
        - madza -> Mazda
        - mazda -> Mazda
        - chebrolet -> Chevrolet
        - chevrolet -> Chevrolet
        - hiunday -> Hyundai
        - hyundai -> Hyundai
        - renol -> Renault
        - renaul -> Renault
        - toyta -> Toyota
        - toyota -> Toyota
        - wolsvagen -> Volkswagen
        - volkswagen -> Volkswagen
        - nisan -> Nissan
        - nissan -> Nissan
        - kia -> Kia
        - ford -> Ford

        Ejemplo:
        Cliente:
        "Soy Jorge tengo una masda 3"

        Debe extraer:
        customer_name = "Jorge"
        vehicle_brand = "Mazda"
        vehicle_model = "3"

        Nunca guardes "masd", "masda" o "madza" como marca si claramente se refiere a Mazda.

        Datos requeridos para avanzar:
        1. customer_name
        2. vehicle_brand
        3. vehicle_model
        4. vehicle_year
        5. city o location

        La placa es útil, pero NO bloquea el avance.

        Si el cliente entrega datos parciales, SIEMPRE muestra primero lo detectado antes de pedir lo faltante.

        Nunca respondas solo:
        "¿Me compartes el año?"

        Siempre confirma lo detectado:
        - nombre
        - marca corregida
        - modelo
        - año
        - ciudad
        - placa

        Considera nombre dudoso y no lo guardes:
        - Yo
        - Cliente
        - Usuario
        - Hola
        - Buenas
        - Buen día
        """
    ).strip()

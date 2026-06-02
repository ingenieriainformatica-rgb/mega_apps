from textwrap import dedent


def get_vehicle_corrections_simple() -> str:
    return dedent(
        """
        # CORRECCIÓN SIMPLE DE VEHÍCULOS

        Corrige errores comunes de marca antes de responder:
        - "masda", "masdaa", "madza" => "Mazda"
        - "chebrolet" => "Chevrolet"
        - "hiunday" => "Hyundai"
        - "renol", "renaul" => "Renault"
        - "toyta" => "Toyota"
        - "wolsvagen" => "Volkswagen"
        - "nisan" => "Nissan"

        Si el cliente escribe algo como "masda 3 2023":
        - vehicle_brand = "Mazda"
        - vehicle_model = "3"
        - vehicle_year = "2023"

        Si el cliente escribe algo como "Jorge y tengo un chebrolet":
        - customer_name = "Jorge"
        - vehicle_brand = "Chevrolet"
        - vehicle_model = null
        - vehicle_year = null

        No preguntes de nuevo por el vehículo si puedes inferir marca, línea/modelo y año
        de una frase corta con errores de escritura.
        No uses nombres de personas, conectores o frases como "jorge y", "tengo un",
        "quiero" o "necesito" como línea/modelo del vehículo.
        """
    ).strip()

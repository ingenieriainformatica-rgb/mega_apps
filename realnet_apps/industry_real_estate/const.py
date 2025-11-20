# condiciones de item de propiedad
CONDITION_SELECTION = [
    ('good', 'En buen estado'),
    ('for_repair', 'Requiere reparación'),
    ('damaged', 'Dañado'),
    ('missing', 'Perdido')
]
# estados de contrato
ESTATES = [
    ('draft', 'Solicitud'),
    ('contract_signed', 'Contrato firmado'),
    ('pending_delivery', 'Pendiente entrega'),
    ('delivered', 'Entregado'),
    ('pending_receipt', 'Pendiente recepción'),
    ('received', 'Recibido'),
    ('done', 'Finalizado'),
]
# estados finales de contrato
FINAL_STATES = ('draft','contract_signed','pending_delivery','delivered','pending_receipt','received','done')
# nomenclatura de direccion
TIPO = [
    ('cll', 'Calle'),
    ('cra', 'Carrera'),
    ('av', 'Avenida'),
    ('dg', 'Diagonal'),
    ('tv', 'Transversal'),
]
# digitos de porcentaje para propiedad
PCT_DIGITS = 2
# tipos de propiedad
TIPO_PROPIEDAD = [
    ('Local', 'Local'),
    ('Warehouse', 'Bodega'), 
    ('Office', 'Oficina/Consultorio'), 
    ('Apartment', 'Apartamento'), 
    ('House', 'Casa'), 
    ('Studio', 'Estudio'), 
    ('Commercial space', 'Espacio comercial/Publicidad'), 
    ('Land', 'Terreno'), 
    ('House Land', 'Casa lote'), 
    ('Garage', 'Garaje'), 
    ('Room', 'Habitación'),
    ('Parking', 'Parqueadero'),
    ('Terrace', 'Terraza'),
    ('Farm', 'Finca')
]

""" SIGLAS DE VARIABLES DE CONTRATO también en el JS del widget o crear funcionalidad para sincronizar """
""" PUEBNTE CREADO EN EL MODELO CLAUSE_VARS_BRIDGE.PY """
CLAUSE_VARS = [
        "ARRENDATARIO_DOCUMENTO",#
        "ARRENDATARIO_ENCABEZADO",#
        "ARRENDATARIO_NOMBRE",#
        "COMISION_MENSUAL",#
        "CONTRATO_CANON",#
        "CONTRATO_CANON_LETRAS",#
        "CONTRATO_DURACION",#
        "DEUDORES_SOLIDARIOS",#
        "DOCUMENTO_DEUDOR_SOLIDARIO",#
        "FECHA_FIN_CONTRATO_LETRAS",#
        "FECHA_INICIO_CONTRATO_LETRAS",#
        "FORMAS_PAGO_LISTA_COMPLETA",
        "INMUEBLE_DIRECCION",#
        "INMUEBLE_MUNICIPIO",#
        "INMUEBLE_NUMERO_CUARTO_UTIL",#
        "INMUEBLE_NUMERO_PARQUEADERO",#
        "LINEA_TELEFONICA",#
        "MUNICIPIO",#
        "NOMBRE_ARRENDADOR",#
        "NOMBRE_DEUDOR_SOLIDARIO",#
        "PROPIETARIOS_LISTA_COMPLETA",#
        "PROYECTO_NOMBRE",
        "SOLICITUD_DESTINO_INMUEBLE",#
        "RAZON_SOCIAL_ARRENDADOR",
    ]

SATES_TO_PAY = ['draft', 'contract_signed', 'pending_delivery', 'delivered', 'pending_receipt', 'received'] # estados de contrato en los que se puede realizar cobro

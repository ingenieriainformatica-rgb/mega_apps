# Carga normal del addon.
# Sin este import Odoo no registra los modelos antes de procesar
# accesos, vistas y demas datos del modulo.
from . import models

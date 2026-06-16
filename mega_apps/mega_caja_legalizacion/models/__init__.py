# Registro de modelos.
# Se reutiliza el mixin generico y se conecta al flujo real de account_petty_cash
# mediante herencias sobre la caja y sus movimientos.
from . import caja_legalizacion_mixin
from . import petty_cash_box
from . import petty_cash_box_line

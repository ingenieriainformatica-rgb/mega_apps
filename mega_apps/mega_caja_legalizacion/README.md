# Mega Caja Legalizacion

Modulo base para preparar el control de legalizacion de movimientos de caja.

Estado actual:
- Define un mixin reutilizable con campos y metodos de legalizacion.
- Define un modelo de seguimiento desacoplado del modulo operativo de caja.
- No hereda aun de los modelos reales de cuadre o movimientos, porque ese modulo todavia no existe en este workspace.

Siguiente fase sugerida:
- Crear un modulo puente que dependa de este addon y del modulo real de caja.
- Heredar la linea de movimiento para agregar estado de legalizacion.
- Heredar el cuadre diario para calcular pendientes y generar arrastres de seguimiento.

Realnet boton Comunicaciones
=============================

Módulo de Odoo que inserta un botón flotante (FAB) con accesos a WhatsApp, Chatbot y Llamada en todas las páginas del sitio web. Las imágenes se sirven desde `static/src/img`.

Instalación
-----------
1. Copia este directorio dentro de `odoo/addons`.
2. Actualiza la lista de aplicaciones y busca "Realnet boton Comunicaciones".
3. Instala el módulo.

Imágenes
--------
Coloca o reemplaza archivos en `static/src/img` con los nombres:
- operador.png (icono del botón principal)
- cerca.png (icono de cerrar)
- conversacion.png (icono del chatbot)
- llamada.png (icono de llamada)
- chat.png (icono de WhatsApp)

Configuración
-------------
- El número de WhatsApp y el `tel:` están codificados en el template, cámbialos si es necesario.
- El enlace del chatbot usa `?chat=open#chatbot`.

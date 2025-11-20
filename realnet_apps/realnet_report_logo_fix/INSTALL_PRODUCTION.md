# Instalación en Producción - realnet_report_logo_fix (Odoo 18 Enterprise)

## Problema detectado
El módulo no se está cargando en producción. Los logs muestran:
```
WARNING aranzazudb odoo.modules.loading: invalid module names, ignored: realnet_report_logo_fix
WARNING aranzazudb odoo.modules.graph: module realnet_report_logo_fix: not installable, skipped
```

**Causa**: El módulo NO está en ninguna de las rutas de `addons_path` configuradas en Odoo.

## Tu configuración actual en producción

```
addons paths: ['/usr/lib/python3/dist-packages/odoo/addons', '/opt/odoo/.local/share/Odoo/addons/18.0']
```

**El módulo debe estar en una de estas dos rutas**, preferiblemente en `/opt/odoo/.local/share/Odoo/addons/18.0/`

## Solución paso a paso

### Paso 1: Comprimir el módulo en local

Desde Windows (PowerShell):

```powershell
# Ir a la carpeta de addons
cd c:\odoo_oskr\addons_realnet

# Crear un ZIP del módulo
Compress-Archive -Path realnet_report_logo_fix -DestinationPath realnet_report_logo_fix.zip
```

O usa WinRAR/7-Zip para crear un archivo `realnet_report_logo_fix.zip`

### Paso 2: Subir al servidor

**Opción A: Usando WinSCP o FileZilla**
1. Conectar al servidor: `vmi2886569` (IP o dominio)
2. Usuario: `root` o `odoo`
3. Navegar a `/opt/odoo/.local/share/Odoo/addons/18.0/`
4. Subir la carpeta `realnet_report_logo_fix` completa

**Opción B: Usando SCP desde PowerShell**
```powershell
scp -r c:\odoo_oskr\addons_realnet\realnet_report_logo_fix root@vmi2886569:/opt/odoo/.local/share/Odoo/addons/18.0/
```

**Opción C: Subir ZIP y descomprimirlo en el servidor**
```bash
# Subir el ZIP
scp c:\odoo_oskr\addons_realnet\realnet_report_logo_fix.zip root@vmi2886569:/tmp/

# Conectarse al servidor
ssh root@vmi2886569

# Descomprimir en la ubicación correcta
cd /opt/odoo/.local/share/Odoo/addons/18.0/
unzip /tmp/realnet_report_logo_fix.zip

# O si no tienes unzip:
cd /tmp
tar -xzf realnet_report_logo_fix.zip
mv realnet_report_logo_fix /opt/odoo/.local/share/Odoo/addons/18.0/
```

### Paso 3: Verificar que el módulo esté en el servidor

```bash
# Conectarse al servidor
ssh root@vmi2886569

# Verificar que el módulo existe
ls -la /opt/odoo/.local/share/Odoo/addons/18.0/ | grep realnet

# Debería aparecer algo como:
# drwxr-xr-x  3 odoo odoo  4096 Nov  6 20:50 realnet_report_logo_fix

# Verificar archivos dentro del módulo
ls -la /opt/odoo/.local/share/Odoo/addons/18.0/realnet_report_logo_fix/

# Debería mostrar:
# -rw-r--r-- 1 odoo odoo    0 __init__.py
# -rw-r--r-- 1 odoo odoo  XXX __manifest__.py
# drwxr-xr-x 2 odoo odoo    X views/
```

### Paso 4: Cambiar permisos (IMPORTANTE)

```bash
# Cambiar propietario a odoo
chown -R odoo:odoo /opt/odoo/.local/share/Odoo/addons/18.0/realnet_report_logo_fix

# Dar permisos de lectura
chmod -R 755 /opt/odoo/.local/share/Odoo/addons/18.0/realnet_report_logo_fix
```

### Paso 5: Instalar el módulo

```bash
# Detener Odoo (si está corriendo como servicio)
sudo systemctl stop odoo

# Instalar el módulo
sudo -u odoo /usr/bin/odoo -d aranzazudb -i realnet_report_logo_fix --stop-after-init

# Verificar que NO aparezca el error:
# ❌ "WARNING: invalid module names, ignored: realnet_report_logo_fix"
# ✅ Debería aparecer: "Loading module realnet_report_logo_fix"

# Reiniciar Odoo
sudo systemctl start odoo
```

### Paso 6: Verificar en la interfaz web

1. Ir a **Aplicaciones** en Odoo
2. Remover el filtro "Aplicaciones" (mostrar todos los módulos)
3. Buscar "realnet_report_logo_fix" o "Fix Report Logo"
4. Si NO aparece: Click en el menú (⋮) → **Actualizar lista de aplicaciones**
5. Debería aparecer el módulo y mostrarse como **Instalado**

### Paso 7: Probar el logo

1. Ve a **Ajustes** → **Compañías** → [Tu compañía]
2. Verifica que el logo esté subido
3. Ve a una **Factura** → Click en **Imprimir**
4. El logo debería aparecer en el PDF

## Troubleshooting

### ❌ Sigue apareciendo "invalid module names"

**Problema**: El módulo NO está en la ruta correcta.

**Solución**:
```bash
# Verifica la ruta exacta
pwd
ls -la /opt/odoo/.local/share/Odoo/addons/18.0/realnet_report_logo_fix

# Si no existe, copia el módulo a esa ubicación
```

### ❌ Aparece "module not installable"

**Problema**: Permisos incorrectos o error en `__manifest__.py`

**Solución**:
```bash
# Verificar permisos
ls -la /opt/odoo/.local/share/Odoo/addons/18.0/realnet_report_logo_fix/__manifest__.py

# Debería mostrar: -rw-r--r-- 1 odoo odoo

# Si no:
chown odoo:odoo /opt/odoo/.local/share/Odoo/addons/18.0/realnet_report_logo_fix/__manifest__.py
chmod 644 /opt/odoo/.local/share/Odoo/addons/18.0/realnet_report_logo_fix/__manifest__.py

# Verificar sintaxis del manifest
cat /opt/odoo/.local/share/Odoo/addons/18.0/realnet_report_logo_fix/__manifest__.py
```

### ❌ El logo NO aparece en el PDF

**Problema**: El logo no está subido o tiene formato incompatible.

**Solución**:
1. Ve a **Ajustes** → **Compañías**
2. **Borra** el logo actual
3. Sube un logo nuevo: PNG o JPG, máximo 200KB, tamaño recomendado 300x100px
4. **Guarda**
5. Genera el PDF nuevamente

### ❌ Error de WebSocket (puerto 8072)

**Problema**: Configuración de Nginx/Apache o firewall.

**Nota**: Esto NO afecta la generación de PDFs, solo las notificaciones en tiempo real. Puedes ignorarlo para el tema del logo.

## Comandos útiles

```bash
# Ver logs en tiempo real
tail -f /var/log/odoo/odoo-server.log

# Buscar errores del módulo
grep -i "realnet_report" /var/log/odoo/odoo-server.log

# Reiniciar Odoo
sudo systemctl restart odoo
sudo systemctl status odoo

# Ver módulos instalados
sudo -u odoo /usr/bin/odoo shell -d aranzazudb
>>> self.env['ir.module.module'].search([('name', '=', 'realnet_report_logo_fix')])
>>> exit()
```

## Resumen de archivos

```
/opt/odoo/.local/share/Odoo/addons/18.0/realnet_report_logo_fix/
├── __init__.py                     # Vacío
├── __manifest__.py                # version: 18.0.1.0.0
├── views/
│   └── report_logo_fix.xml       # Templates QWeb
├── README.md                      # Documentación
└── INSTALL_PRODUCTION.md         # Esta guía
```

## Contacto

Si después de seguir todos estos pasos el módulo aún no se instala, verifica:
1. ✅ El módulo está en `/opt/odoo/.local/share/Odoo/addons/18.0/realnet_report_logo_fix/`
2. ✅ Los permisos son `odoo:odoo`
3. ✅ El `__manifest__.py` existe y tiene sintaxis correcta
4. ✅ Reiniciaste Odoo después de copiar el módulo

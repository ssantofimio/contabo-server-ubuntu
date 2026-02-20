# POS Product Schedule

Este módulo agrega control de disponibilidad de productos en POS basado en días de la semana.


Características:

- Usa el modelo `pos.product.schedule` (definido por este módulo) para almacenar los 7 días de la semana.
- Añade la lógica frontend para filtrar productos que no estén disponibles para el día actual.
- Añade UI en la ficha de producto para seleccionar los días en que el producto está disponible en POS.

Instalación y Verificación:

1. Instalar dependencias y el módulo:

```bash
sudo -u odoo /opt/odoo/odoo17/odoo-venv/bin/python /opt/odoo/odoo17/odoo-bin -c /etc/odoo17.conf -d sarupetrol -i pos_product_schedule --stop-after-init
```

2. Verificar que:
- No aparezcan errores en la instalación.
- El modelo `pos.product.schedule` y sus registros existan (Lunes..Domingo). Este módulo proporciona esos registros por defecto.
- Los productos con `pos_weekday_ids` sólo se muestran en POS los días configurados.
 
Nota sobre `pos_weekday_mask`:
- Este módulo ya no usa ni almacena el campo `pos_weekday_mask`. La disponibilidad se calcula únicamente desde la relación many2many `pos_weekday_ids`.
- Si actualizas desde versiones anteriores y tienes la columna `pos_weekday_mask` en la base de datos, hay una migración SQL en `migrations/17.0.1.0.0/post-migration.sql` para eliminar las columnas en `product_product` y `product_template`. Ejecuta la SQL en un entorno de mantenimiento y con backup antes de aplicarla.

Pruebas manuales:
- En un producto, en la pestaña Ventas → Punto de Venta, seleccionar los días deseados.
- Abrir POS y verificar que el producto aparezca sólo los días seleccionados.

Compatibilidad:
- Este módulo no depende de `pos_product_availability`; proporciona su propio modelo `pos.product.schedule` y datos por defecto para los días de la semana.

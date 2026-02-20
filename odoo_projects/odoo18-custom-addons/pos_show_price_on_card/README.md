# POS Mostrar Precio en Tarjeta (Odoo 18)
Este módulo muestra el precio debajo del nombre del producto en la grilla del POS de Odoo 18.

## Instalación rápida
1. Copia esta carpeta a tu ruta de addons personalizada, por ejemplo `/opt/odoo/custom_addons/`.
2. Asegúrate de que `addons_path` en tu `odoo.conf` incluya la ruta padre (ej: `/opt/odoo/custom_addons`).
3. Reinicia Odoo.
4. Activa modo desarrollador en el backend y actualiza la lista de aplicaciones.
5. Instala el módulo "POS Mostrar Precio en Tarjeta".
6. Limpia caché del navegador y abre una sesión del POS. Deberías ver el precio en la tarjeta del producto.

## Notas
- Si no aparece el precio, revisa la consola de desarrollador para errores y ajusta el `t-inherit` si el nombre del template es diferente.
- Puedes modificar el XML para usar otra propiedad de precio si usas listas de precio.

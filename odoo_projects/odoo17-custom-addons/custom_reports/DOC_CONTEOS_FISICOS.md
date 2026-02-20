# Documentación Técnica: Reporte de Conteos Físicos

Este documento detalla el funcionamiento, origen de datos y lógica de cálculo del módulo de **Conteos Físicos** optimizado para Odoo 17.

## 1. Origen de los Datos

El informe se basa en una **Vista SQL Dinámica** (`stock.report.phys.count`) que consolida información de las siguientes tablas nativas y personalizadas de Odoo:

*   **`stock_quant_conteos_fisicos`**: Contiene los registros de los conteos realizados (instantánea de stock, cantidad contada y diferencia).
*   **`product_product` y `product_template`**: Información maestra de productos y categorías.
*   **`stock_valuation_layer` (SVL)**: Capa de valoración de Odoo donde se registran todos los movimientos de inventario con su valor contable.
*   **`purchase_order_line` y `purchase_order`**: Registro de compras para la obtención del último costo.
*   **`stock_location` y `stock_warehouse`**: Estructura de ubicaciones y almacenes para filtrado y priorización de costos.

---

## 2. Lógica de Cálculo de Cantidades

*   **Stock (Snapshot)**: Es la cantidad que el sistema esperaba que hubiera en la ubicación al momento de iniciar el conteo.
*   **Cant. Contada**: Es el valor ingresado manualmente por el operario durante el conteo físico.
*   **Diferencia**: Cálculo automático: `Cantidad Contada - Stock (Esperado)`.

---

## 3. Métodos de Valorización (Costo Unitario)

El reporte unifica la valoración en una sola columna dinámica. El valor mostrado depende del método seleccionado en el filtro del asistente (Wizard):

### A. Último Costo de Compra
Busca el precio unitario de la orden de compra más reciente siguiendo estas reglas:
1.  **Estado**: La orden de compra debe estar en estado **"Confirmado"** o **"Hecho"**.
2.  **Recepción**: Solo considera líneas donde la cantidad recibida sea mayor a cero (`qty_received > 0`).
3.  **Sin Devoluciones**: Para mayor precisión, prioriza líneas que no tengan descuadres significativos por devoluciones.
4.  **Historial Infinito**: Si no hubo compras en el mes del conteo, la consulta SQL busca hacia atrás en el tiempo sin límite hasta encontrar la última compra real del producto.
5.  **Conversión de Moneda**: Si la compra fue en dólares u otra divisa, el sistema aplica la tasa de cambio (`currency_rate`) de la fecha de la orden para llevar el costo a la moneda local de la compañía.

### B. Costo Promedio (Por Almacén + Documentos)
Calcula el costo promedio ponderado basándose en la capa de valoración contable, con un sistema de rescate documental:
1.  **Fórmula Principal (SVL)**: `Suma total del Valor / Suma total de Cantidad` de los movimientos registrados en `stock_valuation_layer`.
2.  **Filtro Geográfico Estricto**: Solo incluye movimientos que sucedieron en el almacén del conteo físico.
3.  **Rescate Documental (Orden de Compra)**: Si por alguna razón técnica el valor contable en Odoo es `0.0` para ese almacén (pero existen compras registradas), el sistema activa un **"Proxy Documental"**. Este calcula automáticamente el promedio ponderado de todas las **Órdenes de Compra** recibidas en ese almacén, asegurando que el costo refleje el precio real de tus adquisiciones.
4.  **Punto de Corte**: Solo considera datos generados **hasta la fecha del conteo**.

---

## 4. Estructura del Informe

### En Pantalla (Vista Lista y Pivot)
*   Se presenta una columna única de **Costo Unitario** y **Total Valorizado**.
*   Los totales se calculan sobre el **Stock (Snapshot)** del conteo para reflejar el valor de la mercadería que debería estar físicamente allí.

### Reportes PDF
Existen dos modalidades de impresión:
1.  **Detallado**: Muestra el desglose producto por producto, incluyendo almacén, categoría, cantidades y el costo unitario aplicado.
2.  **Resumen por Categoría**: Agrupa los valores por Almacén y Categoría de Producto, facilitando la conciliación rápida de grandes inventarios.

---

## 5. Garantía de Consistencia (Pantalla vs PDF)
Para asegurar que el PDF siempre coincida con lo que ves en pantalla (por ejemplo, los $24.1 millones reportados):
*   El PDF utiliza la misma consulta SQL que la interfaz de usuario.
*   Se implementó un sistema de **Redundancia de Contexto**: El sistema verifica primero el filtro activo en el navegador; si no lo encuentra, consulta el último filtro guardado por el usuario en la base de datos.

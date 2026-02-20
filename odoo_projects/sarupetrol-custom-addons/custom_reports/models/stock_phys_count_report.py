from odoo import fields, models, api, tools, _
from odoo.osv import expression
import io
import json
import xlsxwriter
import logging

_logger = logging.getLogger(__name__)

class StockReportPhysCount(models.Model):
    _name = "stock.report.phys.count"
    _description = "Reporte de Conteos Físicos - Versión Simplificada"
    _auto = False
    _order = 'product_id'

    # Campos básicos de la tabla
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Categoría', readonly=True)
    location_id = fields.Many2one('stock.location', string='Ubicación', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='UdM', readonly=True)
    
    expected_qty = fields.Float('Stock Esperado', readonly=True)
    counted_qty = fields.Float('Cantidad Contada', readonly=True)
    difference = fields.Float('Diferencia', readonly=True)
    current_stock = fields.Float('Stock Actual', readonly=True)
    
    scheduled_date = fields.Date('Fecha conteo', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)

    # Campos de costo y valorización
    cost_avg = fields.Float('Costo Promedio', readonly=True, digits='Product Price')
    cost_last = fields.Float('Último Costo', readonly=True, digits='Product Price')
    val_avg = fields.Float('Valor Promedio', readonly=True, digits='Product Price')
    val_last = fields.Float('Valor Último', readonly=True, digits='Product Price')
    val_stock_avg = fields.Float('Valor Stock Promedio', readonly=True, digits='Product Price')
    val_stock_last = fields.Float('Valor Stock Último', readonly=True, digits='Product Price')
    val_diff_avg = fields.Float('Valor Dif. Promedio', readonly=True, digits='Product Price')
    val_diff_last = fields.Float('Valor Dif. Último', readonly=True, digits='Product Price')

    # Campos de verificación (Referencia SAP-style)
    last_po_id = fields.Many2one('purchase.order', string='OC Referencia', readonly=True)
    last_po_date = fields.Date('Fecha OC', readonly=True)
    last_picking_id = fields.Many2one('stock.picking', string='Movimiento', readonly=True)

    # Campos dinámicos para la vista
    unit_cost = fields.Float('Costo unitario', compute='_compute_valuation', digits='Product Price')
    stock_value = fields.Float('Total Stock', compute='_compute_valuation', digits='Product Price')
    total_value = fields.Float('Total Contado', compute='_compute_valuation', digits='Product Price')
    diff_value = fields.Float('Valor Diferencia', compute='_compute_valuation', digits='Product Price')

    @api.depends_context('valuation_method')
    def _compute_valuation(self):
        method = self.env.context.get('valuation_method', 'avg')
        for record in self:
            if method == 'last':
                record.unit_cost = record.cost_last
                record.stock_value = record.val_stock_last
                record.total_value = record.val_last
                record.diff_value = record.val_diff_last
            else:
                record.unit_cost = record.cost_avg
                record.stock_value = record.val_stock_avg
                record.total_value = record.val_avg
                record.diff_value = record.val_diff_avg

    def action_print_report(self):
        domain = self.env.context.get('active_domain', []) if not self else [('id', 'in', self.ids)]
        return self.env.ref('custom_reports.action_report_stock_phys_count').report_action(None, data={
            'active_domain': domain,
            'valuation_method': self.env.context.get('valuation_method', 'avg')
        })

    def action_print_summary_report(self):
        domain = self.env.context.get('active_domain', []) if not self else [('id', 'in', self.ids)]
        return self.env.ref('custom_reports.action_report_stock_phys_summary').report_action(None, data={
            'active_domain': domain,
            'valuation_method': self.env.context.get('valuation_method', 'avg')
        })

    def action_xlsx(self):
        """Función para disparar la exportación a Excel"""
        import urllib.parse
        _logger.info("StockReportPhysCount: action_xlsx called")
        domain = self.env.context.get('active_domain', []) if not self else [('id', 'in', self.ids)]
        valuation_method = self.env.context.get('valuation_method', 'avg')
        
        data = {
            'active_domain': domain,
            'valuation_method': valuation_method,
        }
        
        params = {
            'model': self._name,
            'options': json.dumps(data, default=fields.date_utils.json_default),
            'output_format': 'xlsx',
            'report_name': 'Reporte_Conteos_Fisicos',
        }
        url = '/xlsx_reports?' + urllib.parse.urlencode(params)
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def get_xlsx_report(self, data, response):
        """Generar el archivo Excel con una pestaña por almacén"""
        _logger.info("StockReportPhysCount: get_xlsx_report called with data %s", data)
        domain = data.get('active_domain', [])
        valuation_method = data.get('valuation_method', 'avg')
        
        # Obtener datos
        docs = self.with_context(valuation_method=valuation_method).sudo().search(domain)
        
        # Agrupar por almacén
        grouped_data = {}
        for doc in docs:
            wh_name = doc.warehouse_id.name if doc.warehouse_id else 'Sin Almacen'
            if wh_name not in grouped_data:
                grouped_data[wh_name] = []
            grouped_data[wh_name].append(doc)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Formatos
        head_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'bg_color': '#E9ECEF'})
        header_format = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9EAD3', 'align': 'center'})
        text_format = workbook.add_format({'border': 1})
        num_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        curr_format = workbook.add_format({'border': 1, 'num_format': '$#,##0.00'})
        total_format = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#F3F3F3', 'num_format': '$#,##0.00'})

        if not grouped_data:
            sheet = workbook.add_worksheet('Sin Datos')
            sheet.write('A1', 'No se encontraron registros para los filtros seleccionados.')
        
        for wh_name, lines in grouped_data.items():
            # Limpiar nombre de la hoja (máx 31 caracteres, sin caracteres especiales)
            sheet_name = wh_name[:31].replace('[', '').replace(']', '').replace('*', '').replace('?', '').replace(':', '').replace('/', '').replace('\\', '')
            sheet = workbook.add_worksheet(sheet_name)
            
            # Título
            sheet.merge_range('A1:J1', f'REPORTE DE CONTEO FÍSICO - {wh_name.upper()}', head_format)
            sheet.write('A2', 'Método de Costeo:', workbook.add_format({'bold': True}))
            sheet.write('B2', 'Precio Promedio' if valuation_method == 'avg' else 'Último Precio de Compra')
            
            headers = [
                'Categoría', 'Producto', 'UdM', 'Costo Unitario', 
                'Stock Esperado', 'Cant. Contada', 'Diferencia', 
                'Total Stock', 'Total Contado', 'Valor Diferencia'
            ]
            
            for col, header in enumerate(headers):
                sheet.write(3, col, header, header_format)
            
            row = 4
            t_stock_val = 0.0
            t_total_val = 0.0
            t_diff_val = 0.0

            for line in lines:
                sheet.write(row, 0, line.product_categ_id.name or '', text_format)
                sheet.write(row, 1, line.product_id.name, text_format)
                sheet.write(row, 2, line.product_uom_id.name or '', text_format)
                sheet.write(row, 3, line.unit_cost, curr_format)
                sheet.write(row, 4, line.expected_qty, num_format)
                sheet.write(row, 5, line.counted_qty, num_format)
                sheet.write(row, 6, line.difference, num_format)
                sheet.write(row, 7, line.stock_value, curr_format)
                sheet.write(row, 8, line.total_value, curr_format)
                sheet.write(row, 9, line.diff_value, curr_format)
                
                t_stock_val += line.stock_value
                t_total_val += line.total_value
                t_diff_val += line.diff_value
                row += 1
            
            # Totales
            sheet.merge_range(row, 0, row, 6, 'TOTALES', workbook.add_format({'bold': True, 'align': 'right', 'border': 1, 'bg_color': '#F3F3F3'}))
            sheet.write(row, 7, t_stock_val, total_format)
            sheet.write(row, 8, t_total_val, total_format)
            sheet.write(row, 9, t_diff_val, total_format)

            # Ajustar anchos
            sheet.set_column('A:A', 20)
            sheet.set_column('B:B', 40)
            sheet.set_column('C:C', 10)
            sheet.set_column('D:J', 15)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Sobrescribir read_group para permitir totales en vistas agrupadas con campos virtuales """
        method = self.env.context.get('valuation_method', 'avg')
        mapping = {
            'stock_value': 'val_stock_last' if method == 'last' else 'val_stock_avg',
            'total_value': 'val_last' if method == 'last' else 'val_avg',
            'diff_value': 'val_diff_last' if method == 'last' else 'val_diff_avg',
        }
        
        # Mapear los campos de agregación (ej: 'total_value:sum')
        new_fields = []
        for field in fields:
            name = field.split(':')[0]
            if name in mapping:
                new_fields.append(field.replace(name, mapping[name]))
            else:
                new_fields.append(field)
        
        result = super(StockReportPhysCount, self).read_group(domain, new_fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        
        # Devolver los nombres originales a los resultados para que el cliente web los reconozca
        for res in result:
            for virtual, physical in mapping.items():
                for suffix in ['', ':sum', ':avg', ':max', ':min']:
                    key = physical + suffix
                    if key in res:
                        res[virtual + suffix] = res[key]
                        # Mantener el nombre sin sufijo para compatibilidad con widgets
                        res[virtual] = res[key]
        return result

    def init(self):
        # Asegurar índices en la tabla base para acelerar el filtrado del View
        # Usamos try-except porque en la instalación inicial la tabla puede no existir aún
        try:
            self.env.cr.execute("CREATE INDEX IF NOT EXISTS idx_sqcf_scheduled_date ON stock_quant_conteos_fisicos (scheduled_date)")
            self.env.cr.execute("CREATE INDEX IF NOT EXISTS idx_sqcf_product_id ON stock_quant_conteos_fisicos (product_id)")
            self.env.cr.execute("CREATE INDEX IF NOT EXISTS idx_sqcf_location_id ON stock_quant_conteos_fisicos (location_id)")
            
            # Índices adicionales para optimizar uniones pesadas
            self.env.cr.execute("CREATE INDEX IF NOT EXISTS idx_sm_warehouse_product_state ON stock_move (warehouse_id, product_id, state)")
            self.env.cr.execute("CREATE INDEX IF NOT EXISTS idx_pol_product_id ON purchase_order_line (product_id)")
            self.env.cr.execute("CREATE INDEX IF NOT EXISTS idx_po_date_approve ON purchase_order (date_approve, state)")
        except Exception:
            _logger.warning("Could not create indexes for StockReportPhysCount - tables might not exist yet")

        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    cf.id as id,
                    cf.product_id as product_id,
                    pt.categ_id as product_categ_id,
                    cf.location_id as location_id,
                    sl.warehouse_id as warehouse_id,
                    pt.uom_id as product_uom_id,
                    cf.expected_qty as expected_qty,
                    cf.expected_qty as current_stock,
                    cf.counted_qty as counted_qty,
                    cf.difference as difference,
                    
                    -- Costos calculados
                    COALESCE(wap_wh.avg_price, wap_purchase.avg_price, 0.0) as cost_avg,
                    COALESCE(lpw_wh.last_price, 0.0) as cost_last,
                    
                    cf.counted_qty * COALESCE(wap_wh.avg_price, wap_purchase.avg_price, 0.0) as val_avg,
                    cf.counted_qty * COALESCE(lpw_wh.last_price, 0.0) as val_last,
                    cf.expected_qty * COALESCE(wap_wh.avg_price, wap_purchase.avg_price, 0.0) as val_stock_avg,
                    cf.expected_qty * COALESCE(lpw_wh.last_price, 0.0) as val_stock_last,
                    cf.difference * COALESCE(wap_wh.avg_price, wap_purchase.avg_price, 0.0) as val_diff_avg,
                    cf.difference * COALESCE(lpw_wh.last_price, 0.0) as val_diff_last,

                    -- Verificación (Referencia OC y Movimiento)
                    lpw_wh.po_id as last_po_id,
                    lpw_wh.po_date as last_po_date,
                    lpw_wh.picking_id as last_picking_id,

                    CAST(cf.scheduled_date AS DATE) as scheduled_date,
                    sl.company_id as company_id,
                    c.currency_id as currency_id
                FROM stock_quant_conteos_fisicos cf
                JOIN product_product pp ON cf.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN stock_location sl ON cf.location_id = sl.id
                JOIN res_company c ON sl.company_id = c.id
                
                -- 1. Costo Promedio POR ALMACÉN (SVL Contable)
                LEFT JOIN LATERAL (
                    SELECT 
                        CASE WHEN SUM(svl.quantity) != 0 AND SUM(svl.value) != 0 
                             THEN SUM(svl.value) / SUM(svl.quantity) ELSE NULL END as avg_price
                    FROM stock_valuation_layer svl
                    JOIN stock_move sm ON svl.stock_move_id = sm.id
                    WHERE svl.product_id = cf.product_id 
                      AND svl.create_date <= (cf.scheduled_date + interval '1 day')
                      AND sm.warehouse_id = sl.warehouse_id
                ) wap_wh ON TRUE

                -- 2. Fallback: Promedio de Compras POR ALMACÉN (Weighted Average)
                LEFT JOIN LATERAL (
                    SELECT 
                        CASE WHEN SUM(pol.qty_received) != 0 
                             THEN SUM(pol.price_unit * pol.qty_received / COALESCE(po.currency_rate, 1.0)) / SUM(pol.qty_received)
                             ELSE NULL END as avg_price
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE pol.product_id = cf.product_id 
                      AND po.state IN ('purchase', 'done')
                      AND po.date_approve <= cf.scheduled_date
                      AND po.picking_type_id IN (SELECT id FROM stock_picking_type WHERE warehouse_id = sl.warehouse_id)
                      AND pol.qty_received > 0
                ) wap_purchase ON TRUE
                
                -- 3. Último Costo POR ALMACÉN (Con reglas estrictas)
                LEFT JOIN LATERAL (
                    SELECT 
                        (pol.price_unit / COALESCE(po.currency_rate, 1.0)) as last_price,
                        po.id as po_id,
                        po.date_approve as po_date,
                        (SELECT sm.picking_id 
                         FROM stock_move sm 
                         WHERE sm.purchase_line_id = pol.id 
                           AND sm.state = 'done' 
                         ORDER BY sm.date DESC LIMIT 1) as picking_id
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE pol.product_id = cf.product_id 
                      AND po.state IN ('purchase', 'done')
                      AND po.date_approve <= cf.scheduled_date
                      AND pol.qty_received > 0
                      AND po.picking_type_id IN (SELECT id FROM stock_picking_type WHERE warehouse_id = sl.warehouse_id)
                    ORDER BY 
                        po.date_approve DESC, 
                        (pol.qty_received >= pol.product_qty) DESC, 
                        po.id DESC
                    LIMIT 1
                ) lpw_wh ON TRUE
            )
        """ % self._table)

import logging
from odoo import models, fields, api
_logger = logging.getLogger(__name__)

class StockReportBalance(models.Model):
    _name = 'stock.report.balance'
    _description = 'Reporte de Balance de Inventario'
    _order = 'product_id'

    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Plantilla de Producto', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Categoría', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='UdM', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    date_from = fields.Date('Desde', readonly=True)
    date_to = fields.Date('Hasta', readonly=True)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.product_id.display_name

    # Cantidades
    qty_initial = fields.Float('Stock inicial', readonly=True)
    qty_in = fields.Float('Entradas', readonly=True)
    qty_out = fields.Float('Salidas', readonly=True)
    qty_final = fields.Float('Stock final', readonly=True)

    # Valores
    val_initial = fields.Float('Valor inicial', readonly=True)
    val_in = fields.Float('Valor entradas', readonly=True)
    val_out = fields.Float('Valor salidas', readonly=True)
    val_final = fields.Float('Valor final', readonly=True)

    # Detalle de movimientos para el drill-down
    move_line_ids = fields.Many2many('stock.move.line', compute='_compute_move_line_ids', string='Detalle de Movimientos')

    def _compute_move_line_ids(self):
        for rec in self:
            # Obtener todas las ubicaciones del almacén
            locations = self.env['stock.location'].search([
                ('id', 'child_of', rec.warehouse_id.view_location_id.id)
            ])
            
            domain = [
                ('product_id', '=', rec.product_id.id),
                ('state', '=', 'done'),
                ('date', '>=', rec.date_from),
                '|',
                ('location_id', 'in', locations.ids),
                ('location_dest_id', 'in', locations.ids)
            ]
            
            if rec.date_to:
                from datetime import timedelta
                to_date = fields.Date.from_string(rec.date_to) + timedelta(days=1)
                domain.append(('date', '<', fields.Date.to_string(to_date)))
                
            rec.move_line_ids = self.env['stock.move.line'].search(domain, order='date desc')

    def action_view_movements(self):
        self.ensure_one()
        # Intentar obtener la acción por XML ID para mayor robustez
        try:
            action = self.env.ref("stock.stock_move_line_action").read()[0]
        except Exception:
            # Fallback a búsqueda por modelo si el XML ID falla
            action = {
                'name': 'Historial de movimientos',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.move.line',
                'view_mode': 'tree,form,pivot',
                'target': 'current',
            }
        
        # Filtros de Almacén mejorados para Odoo 17
        warehouse = self.warehouse_id
        # Obtener todas las ubicaciones hijas del almacén (Stock, Input, Output, etc.)
        locations = self.env['stock.location'].search([
            ('id', 'child_of', warehouse.view_location_id.id)
        ])
        
        domain = [
            ('product_id', '=', self.product_id.id),
            ('state', '=', 'done'),
            ('date', '>=', self.date_from),
            '|',
            ('location_id', 'in', locations.ids),
            ('location_dest_id', 'in', locations.ids)
        ]
        
        if self.date_to:
            from datetime import timedelta
            to_date = fields.Date.from_string(self.date_to) + timedelta(days=1)
            domain.append(('date', '<', fields.Date.to_string(to_date)))
            
        action['domain'] = domain
        action['context'] = {'search_default_done': 1, 'search_default_groupby_product_id': 1}
        action['name'] = f"Movimientos: {self.product_id.display_name}"
        
        return action

    def generate_report_data(self, date_from, date_to, warehouse_ids, category_ids, company_id):
        self.env.cr.execute("""
            INSERT INTO stock_report_balance (
                product_id, product_tmpl_id, product_categ_id, product_uom_id, 
                warehouse_id, company_id, currency_id,
                date_from, date_to,
                qty_initial, qty_in, qty_out, qty_final,
                val_initial, val_in, val_out, val_final,
                create_uid, create_date, write_uid, write_date
            )
            WITH last_purchase_per_warehouse AS (
                SELECT DISTINCT ON (l.product_id, spt.warehouse_id, po.company_id)
                    l.product_id, spt.warehouse_id, po.company_id,
                    (l.price_unit / COALESCE(po.currency_rate, 1.0)) as price_unit
                FROM purchase_order_line l
                JOIN purchase_order po ON l.order_id = po.id
                JOIN stock_picking_type spt ON po.picking_type_id = spt.id
                WHERE po.state IN ('purchase', 'done') AND spt.warehouse_id IS NOT NULL
                ORDER BY l.product_id, spt.warehouse_id, po.company_id, po.date_approve DESC, l.id DESC
            ),
            last_purchase_global AS (
                SELECT DISTINCT ON (l.product_id, po.company_id)
                    l.product_id, po.company_id,
                    (l.price_unit / COALESCE(po.currency_rate, 1.0)) as price_unit
                FROM purchase_order_line l
                JOIN purchase_order po ON l.order_id = po.id
                WHERE po.state IN ('purchase', 'done')
                ORDER BY l.product_id, po.company_id, po.date_approve DESC, l.id DESC
            ),
            movement_data AS (
                -- Capturar TODOS los movimientos vinculados a un almacén vía ubicación
                SELECT 
                    ml.product_id,
                    COALESCE(ls.warehouse_id, ld.warehouse_id) as warehouse_id,
                    ml.quantity as qty,
                    ml.date,
                    CASE 
                        -- Entrada: El destino es interno del almacén pero el origen no lo es
                        WHEN ld.usage = 'internal' AND (ls.usage != 'internal' OR ls.warehouse_id != ld.warehouse_id) THEN 'in'
                        -- Salida: El origen es interno del almacén pero el destino no lo es
                        WHEN ls.usage = 'internal' AND (ld.usage != 'internal' OR ld.warehouse_id != ls.warehouse_id) THEN 'out'
                        ELSE 'none' END as move_type
                FROM stock_move_line ml
                JOIN stock_move m ON ml.move_id = m.id
                JOIN stock_location ls ON ml.location_id = ls.id
                JOIN stock_location ld ON ml.location_dest_id = ld.id
                WHERE m.state = 'done' 
                  AND ml.company_id = %s
                  AND (ls.warehouse_id IS NOT NULL OR ld.warehouse_id IS NOT NULL)
            ),
            balances AS (
                SELECT 
                    product_id,
                    warehouse_id,
                    SUM(CASE WHEN date < %s THEN 
                        CASE WHEN move_type = 'in' THEN qty ELSE -qty END
                        ELSE 0 END) as qty_initial,
                    SUM(CASE WHEN date >= %s AND date < %s::date + interval '1 day' AND move_type = 'in' THEN qty ELSE 0 END) as qty_in,
                    SUM(CASE WHEN date >= %s AND date < %s::date + interval '1 day' AND move_type = 'out' THEN qty ELSE 0 END) as qty_out
                FROM movement_data
                WHERE move_type != 'none'
                GROUP BY product_id, warehouse_id
            )
            SELECT 
                b.product_id, p.product_tmpl_id, t.categ_id, t.uom_id, b.warehouse_id,
                %s, c.currency_id,
                %s, %s, -- date_from, date_to
                b.qty_initial, b.qty_in, b.qty_out,
                (b.qty_initial + b.qty_in - b.qty_out) as qty_final,
                b.qty_initial * COALESCE(lpw.price_unit, lpg.price_unit, 0.0) as val_initial,
                b.qty_in * COALESCE(lpw.price_unit, lpg.price_unit, 0.0) as val_in,
                b.qty_out * COALESCE(lpw.price_unit, lpg.price_unit, 0.0) as val_out,
                (b.qty_initial + b.qty_in - b.qty_out) * COALESCE(lpw.price_unit, lpg.price_unit, 0.0) as val_final,
                %s, NOW(), %s, NOW()
            FROM balances b
            JOIN product_product p ON b.product_id = p.id
            JOIN product_template t ON p.product_tmpl_id = t.id
            JOIN res_company c ON c.id = %s
            LEFT JOIN last_purchase_per_warehouse lpw ON (lpw.product_id = b.product_id AND lpw.warehouse_id = b.warehouse_id AND lpw.company_id = %s)
            LEFT JOIN last_purchase_global lpg ON (lpg.product_id = b.product_id AND lpg.company_id = %s)
            WHERE (abs(b.qty_initial) > 0.0001 OR abs(b.qty_in) > 0.0001 OR abs(b.qty_out) > 0.0001)
              AND (%s = 0 OR b.warehouse_id = ANY(%s))
              AND (%s = 0 OR t.categ_id = ANY(%s))
        """, (
            company_id,
            date_from, 
            date_from, date_to, 
            date_from, date_to,
            company_id,
            date_from, date_to,
            self.env.uid, self.env.uid,
            company_id, company_id, company_id,
            1 if warehouse_ids else 0, warehouse_ids or [0],
            1 if category_ids else 0, category_ids or [0]
        ))

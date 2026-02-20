# -*- coding: utf-8 -*-
from odoo import fields, models, api

class StockReportAvailable(models.Model):
    _name = "stock.report.available"
    _description = "Reporte de Existencias"
    _auto = False
    _rec_name = 'product_id'

    # Definición de campos como campos de base de datos (se leen de la vista SQL)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Plantilla de Producto', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Categoría', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='UdM', readonly=True)
    location_id = fields.Many2one('stock.location', string='Ubicación', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lote/Serie', readonly=True)
    package_id = fields.Many2one('stock.quant.package', string='Paquete', readonly=True)
    owner_id = fields.Many2one('res.partner', string='Propietario', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', readonly=True)
    
    quantity = fields.Float('A Mano', readonly=True)
    reserved_quantity = fields.Float('Reservado', readonly=True)
    available_quantity = fields.Float('Disponible', readonly=True)
    in_date = fields.Datetime('Fecha de Entrada', readonly=True)

    def init(self):
        self._cr.execute("""
            DROP VIEW IF EXISTS stock_report_available;
            CREATE OR REPLACE VIEW stock_report_available AS (
                SELECT
                    q.id,
                    q.product_id,
                    q.location_id,
                    q.lot_id,
                    q.package_id,
                    q.owner_id,
                    q.quantity,
                    q.reserved_quantity,
                    (q.quantity - q.reserved_quantity) as available_quantity,
                    q.company_id,
                    q.in_date,
                    p.product_tmpl_id,
                    t.uom_id as product_uom_id,
                    t.categ_id as product_categ_id,
                    l.warehouse_id
                FROM
                    stock_quant q
                    JOIN product_product p ON q.product_id = p.id
                    JOIN product_template t ON p.product_tmpl_id = t.id
                    JOIN stock_location l ON q.location_id = l.id
                WHERE
                    l.usage = 'internal'
            )
        """)

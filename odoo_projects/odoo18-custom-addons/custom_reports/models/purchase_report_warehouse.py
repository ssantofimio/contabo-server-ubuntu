# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools

class PurchaseReportWarehouse(models.Model):
    _name = 'purchase.report.warehouse'
    _description = 'Reporte de Compras por Producto'
    _auto = False
    _order = 'date_order desc'

    location_id = fields.Many2one('stock.location', string='Ubicación', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén', readonly=True)
    date_order = fields.Datetime(string='Fecha O.C', readonly=True)
    purchase_id = fields.Many2one('purchase.order', string='Orden de Compra ID', readonly=True)
    purchase_name = fields.Char(string='Orden de Compra', readonly=True)
    partner_ref = fields.Char(string='Ref. Proveedor', readonly=True)
    state = fields.Selection([
        ('draft', 'Cotización'),
        ('sent', 'Cotización'),
        ('to approve', 'Por aprobar'),
        ('purchase', 'Orden de Compra'),
        ('done', 'Bloqueado'),
        ('cancel', 'Cancelado'),
    ], string='Estado O.C', readonly=True)
    default_code = fields.Char(string='Ref. Interna', readonly=True)
    receipt_status = fields.Char(string='Estado de Entrega', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='UdM', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Proveedor', readonly=True)
    product_qty = fields.Float(string='Cantidad', readonly=True)
    price_unit = fields.Float(string='Precio Unitario', readonly=True)
    price_subtotal = fields.Float(string='Total', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', readonly=True)
    invoice_status = fields.Selection([
        ('no', 'Nada por facturar'),
        ('to invoice', 'Facturas en espera'),
        ('invoiced', 'Totalmente facturado'),
    ], string='Estado de facturación', readonly=True)


    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s AS (
                SELECT
                    pol.id as id,
                    pol.product_id as product_id,
                    pt.uom_id as product_uom_id,
                    pp.default_code as default_code,
                    po.id as purchase_id,
                    po.name as purchase_name,
                    po.partner_ref as partner_ref,
                    po.state as state,
                    CASE 
                        WHEN po.receipt_status_display_es = 'Sin Recibir' THEN 'No recibido'
                        WHEN po.receipt_status_display_es = 'Parcial' THEN 'Recibido parcialmente'
                        WHEN po.receipt_status_display_es = 'Recibido' THEN 'Recibido totalmente'
                        ELSE po.receipt_status_display_es
                    END as receipt_status,
                    po.invoice_status as invoice_status,
                    po.partner_id as partner_id,
                    po.date_order as date_order,
                    po.company_id as company_id,
                    po.currency_id as currency_id,
                    spt.warehouse_id as warehouse_id,
                    spt.default_location_dest_id as location_id,
                    pol.product_qty as product_qty,
                    pol.price_unit as price_unit,
                    pol.price_subtotal as price_subtotal
                FROM purchase_order_line pol
                JOIN purchase_order po ON pol.order_id = po.id
                JOIN product_product pp ON pol.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN stock_picking_type spt ON po.picking_type_id = spt.id
                WHERE po.state IN ('purchase', 'done')
            )
        """ % self._table)

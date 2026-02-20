# -*- coding: utf-8 -*-
from odoo import fields, models, api, tools

class PurchaseReportPriceHistory(models.Model):
    _name = "purchase.report.price.history"
    _description = "Histórico de Precios (Facturas)"
    _auto = False
    _order = 'date desc'

    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Categoría', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Proveedor', readonly=True)
    date = fields.Date('Fecha Factura', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Factura', readonly=True)
    price_unit = fields.Float('Precio Unitario', readonly=True, digits='Product Price', group_operator=None)
    quantity = fields.Float('Cantidad', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='UdM', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    price_total = fields.Float('Total', readonly=True, digits='Product Price')
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén', readonly=True)
    location_id = fields.Many2one('stock.location', string='Ubicación', readonly=True)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        # Si el dominio está vacío, intentamos aplicar los filtros del último wizard del usuario
        if not domain and not self.env.context.get('no_wizard_filter'):
            last_wizard = self.env['purchase.price.history.wizard'].sudo().search(
                [('create_uid', '=', self.env.uid)], order='id desc', limit=1
            )
            if last_wizard:
                new_domain = []
                if last_wizard.warehouse_ids:
                    new_domain.append(('warehouse_id', 'in', last_wizard.warehouse_ids.ids))
                if last_wizard.date_from:
                    new_domain.append(('date', '>=', last_wizard.date_from))
                if last_wizard.date_to:
                    new_domain.append(('date', '<=', last_wizard.date_to))
                if last_wizard.partner_ids:
                    new_domain.append(('partner_id', 'in', last_wizard.partner_ids.ids))
                if last_wizard.product_categ_ids:
                    new_domain.append(('product_categ_id', 'in', last_wizard.product_categ_ids.ids))
                if last_wizard.product_ids:
                    new_domain.append(('product_id', 'in', last_wizard.product_ids.ids))
                domain = new_domain
        return super()._search(domain, offset=offset, limit=limit, order=order)

    def action_print_report(self):
        # Si hay una selección manual, usarla. Si no, usar el dominio del filtro actual.
        domain = self.env.context.get('active_domain', []) if not self else [('id', 'in', self.ids)]
        return self.env.ref('custom_reports.action_report_price_history').report_action(None, data={'active_domain': domain})

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    l.id as id,
                    l.product_id as product_id,
                    t.categ_id as product_categ_id,
                    m.partner_id as partner_id,
                    COALESCE(m.invoice_date, m.date) as date,
                    m.id as invoice_id,
                    l.price_unit as price_unit,
                    l.quantity as quantity,
                    l.product_uom_id as uom_id,
                    m.company_id as company_id,
                    m.currency_id as currency_id,
                    (l.price_unit * l.quantity) as price_total,
                    spt.warehouse_id as warehouse_id,
                    spt.default_location_dest_id as location_id
                FROM
                    account_move_line l
                    JOIN account_move m ON l.move_id = m.id
                    JOIN product_product p ON l.product_id = p.id
                    JOIN product_template t ON p.product_tmpl_id = t.id
                    LEFT JOIN purchase_order_line pol ON l.purchase_line_id = pol.id
                    LEFT JOIN purchase_order po ON pol.order_id = po.id
                    LEFT JOIN stock_picking_type spt ON po.picking_type_id = spt.id
                WHERE
                    m.move_type IN ('in_invoice', 'in_refund')
                    AND m.state = 'posted'
                    AND (l.display_type IS NULL OR l.display_type = 'product')
                    AND l.product_id IS NOT NULL
            )
        """ % self._table)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(PurchaseReportPriceHistory, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            if 'price_total' in line and 'quantity' in line and line['quantity']:
                line['price_unit'] = line['price_total'] / line['quantity']
        return res

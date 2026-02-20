# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class PurchasePriceHistoryWizard(models.TransientModel):
    _name = 'purchase.price.history.wizard'
    _description = 'Wizard Histórico de Precios'

    def _default_date_from(self):
        return fields.Date.context_today(self).replace(day=1)

    def _default_date_to(self):
        return fields.Date.context_today(self) + relativedelta(day=31)

    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén', required=True)
    date_from = fields.Date('Desde', required=True, default=_default_date_from)
    date_to = fields.Date('Hasta', required=True, default=_default_date_to)
    
    partner_ids = fields.Many2many('res.partner', string='Proveedores')
    product_categ_ids = fields.Many2many('product.category', string='Categorías')
    product_ids = fields.Many2many('product.product', string='Productos')

    allowed_partner_ids = fields.Many2many('res.partner', compute='_compute_allowed_filters')
    allowed_product_ids = fields.Many2many('product.product', compute='_compute_allowed_filters')
    allowed_categ_ids = fields.Many2many('product.category', compute='_compute_allowed_filters')

    @api.model
    def default_get(self, fields_list):
        res = super(PurchasePriceHistoryWizard, self).default_get(fields_list)
        # Si venimos del reporte, intentamos recuperar el último wizard utilizado por el usuario
        if self.env.context.get('is_adjustment') or self.env.context.get('active_model') == 'purchase.report.price.history':
            last_wizard = self.env['purchase.price.history.wizard'].sudo().search(
                [('create_uid', '=', self.env.uid)], 
                order='id desc', 
                limit=1
            )
            # Fallback: si no encuentra por UID (raro), busca el último de todo el sistema
            if not last_wizard:
                last_wizard = self.env['purchase.price.history.wizard'].sudo().search([], order='id desc', limit=1)
                
            if last_wizard:
                res.update({
                    'warehouse_id': last_wizard.warehouse_id.id,
                    'date_from': last_wizard.date_from,
                    'date_to': last_wizard.date_to,
                    'partner_ids': [(6, 0, last_wizard.partner_ids.ids)],
                    'product_categ_ids': [(6, 0, last_wizard.product_categ_ids.ids)],
                    'product_ids': [(6, 0, last_wizard.product_ids.ids)],
                })
        return res

    @api.depends('warehouse_id', 'date_from', 'date_to', 'partner_ids', 'product_ids', 'product_categ_ids')
    def _compute_allowed_filters(self):
        for record in self:
            base_domain = [
                ('move_id.move_type', 'in', ('in_invoice', 'in_refund')),
                ('move_id.state', '=', 'posted')
            ]
            
            if record.date_from:
                base_domain.append(('invoice_date', '>=', record.date_from))
            if record.date_to:
                base_domain.append(('invoice_date', '<=', record.date_to))
                
            if record.warehouse_id:
                base_domain += [
                    ('purchase_line_id.order_id.picking_type_id.warehouse_id', '=', record.warehouse_id.id)
                ]

            # Helper to search lines with additional domain
            def get_lines(extra_domain):
                return self.env['account.move.line'].search(base_domain + extra_domain)

            # Allowed Categories: filtered by Warehouse, Dates, Partners, Products
            categ_domain = []
            if record.partner_ids:
                categ_domain.append(('partner_id', 'in', record.partner_ids.ids))
            if record.product_ids:
                categ_domain.append(('product_id', 'in', record.product_ids.ids))
            record.allowed_categ_ids = get_lines(categ_domain).mapped('product_id.categ_id')

            # Allowed Products: filtered by Warehouse, Dates, Partners, Categories
            product_domain = []
            if record.partner_ids:
                product_domain.append(('partner_id', 'in', record.partner_ids.ids))
            if record.product_categ_ids:
                product_domain.append(('product_id.categ_id', 'in', record.product_categ_ids.ids))
            record.allowed_product_ids = get_lines(product_domain).mapped('product_id')

            # Allowed Partners: filtered by Warehouse, Dates, Products, Categories
            partner_domain = []
            if record.product_ids:
                partner_domain.append(('product_id', 'in', record.product_ids.ids))
            if record.product_categ_ids:
                partner_domain.append(('product_id.categ_id', 'in', record.product_categ_ids.ids))
            record.allowed_partner_ids = get_lines(partner_domain).mapped('partner_id')

    def action_view_report(self):
        self.ensure_one()
        action = self.env.ref('custom_reports.action_purchase_report_price_history').sudo().read()[0]
        
        domain = []
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.product_categ_ids:
            domain.append(('product_categ_id', 'in', self.product_categ_ids.ids))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))

        action['domain'] = domain
        action['context'] = {'search_default_group_product': 1}
        action['target'] = 'main'
        return action

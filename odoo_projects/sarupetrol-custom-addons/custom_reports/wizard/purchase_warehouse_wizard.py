# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PurchaseWarehouseWizard(models.TransientModel):
    _name = 'purchase.warehouse.wizard'
    _description = 'Asistente de Compras por Producto'

    def _default_date_from(self):
        return fields.Date.today().replace(day=1)

    def _default_date_to(self):
        return fields.Date.today()

    date_from = fields.Date('Desde', required=True, default=_default_date_from)
    date_to = fields.Date('Hasta', required=True, default=_default_date_to)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Almacenes', domain="[('company_id', '=', company_id)]")

    @api.model
    def default_get(self, fields_list):
        res = super(PurchaseWarehouseWizard, self).default_get(fields_list)
        # Solo cargar últimos valores si explícitamente venimos de "Ajustar Filtros"
        if self.env.context.get('is_adjustment'):
            last_wizard = self.search([('create_uid', '=', self.env.user.id)], order='id desc', limit=1)
            if last_wizard:
                res.update({
                    'date_from': last_wizard.date_from,
                    'date_to': last_wizard.date_to,
                    'warehouse_ids': [(6, 0, last_wizard.warehouse_ids.ids)],
                })
        return res

    def action_generate_report(self):
        self.ensure_one()
        domain = [
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to)
        ]
        if self.warehouse_ids:
            domain.append(('warehouse_id', 'in', self.warehouse_ids.ids))

        return {
            'name': _('Compras por Producto'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.report.warehouse',
            'view_mode': 'tree,pivot',
            'domain': domain,
            'context': {
                'active_test': False,
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
                'default_warehouse_ids': [(6, 0, self.warehouse_ids.ids)],
                'search_default_purchase_orders': 1,
            },
            'target': 'main',
        }
    

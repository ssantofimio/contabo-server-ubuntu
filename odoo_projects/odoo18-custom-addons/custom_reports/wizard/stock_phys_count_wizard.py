# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class StockPhysCountWizard(models.TransientModel):
    _name = 'stock.phys.count.wizard'
    _description = 'Wizard de Reporte de Conteos Físicos'

    def _default_date_from(self):
        # Primer día del mes anterior
        return (fields.Date.today() - relativedelta(months=1)).replace(day=1)

    def _default_date_to(self):
        # Último día del mes anterior
        return fields.Date.today().replace(day=1) - relativedelta(days=1)

    date_from = fields.Date('Desde', required=True, default=_default_date_from)
    date_to = fields.Date('Hasta', required=True, default=_default_date_to)

    valuation_method = fields.Selection([
        ('avg', 'Costo promedio'),
        ('last', 'Último costo'),
    ], string='Método de valorización', default='last', required=True)

    warehouse_ids = fields.Many2many('stock.warehouse', string='Almacenes')
    category_ids = fields.Many2many('product.category', string='Categorías')

    @api.model
    def default_get(self, fields_list):
        res = super(StockPhysCountWizard, self).default_get(fields_list)
        # Si venimos de "Filtros / Valorización" dentro del reporte, cargamos el último wizard del usuario
        if self.env.context.get('is_adjustment'):
            last_wizard = self.search([('create_uid', '=', self.env.user.id)], order='id desc', limit=1)
            if last_wizard:
                res.update({
                    'date_from': last_wizard.date_from,
                    'date_to': last_wizard.date_to,
                    'valuation_method': last_wizard.valuation_method,
                    'warehouse_ids': [(6, 0, last_wizard.warehouse_ids.ids)],
                    'category_ids': [(6, 0, last_wizard.category_ids.ids)],
                })
        return res

    def action_generate_report(self):
        self.ensure_one()
        action = self.env.ref('custom_reports.action_stock_report_phys_count').sudo().read()[0]
        
        domain = [
            ('scheduled_date', '>=', self.date_from),
            ('scheduled_date', '<=', self.date_to)
        ]
        if self.warehouse_ids:
            domain.append(('warehouse_id', 'in', self.warehouse_ids.ids))
        if self.category_ids:
            domain.append(('product_categ_id', 'in', self.category_ids.ids))
            
        action['name'] = 'Conteos Físicos'
        action['target'] = 'main'
        action['domain'] = domain
        action['context'] = {
            'valuation_method': self.valuation_method,
            'search_default_group_warehouse': 1 if not self.warehouse_ids else 0,
        }
        return action

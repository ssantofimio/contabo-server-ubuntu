# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockBalanceWizard(models.TransientModel):
    _name = 'stock.balance.wizard'
    _description = 'Asistente de Balance de Inventario'

    date_from = fields.Date('Desde', required=True, default=fields.Date.context_today)
    date_to = fields.Date('Hasta', required=True, default=fields.Date.context_today)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Almacenes', domain="[('company_id', '=', company_id)]")
    category_ids = fields.Many2many('product.category', string='Categorías')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    def action_generate_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("La fecha 'Desde' no puede ser mayor que la fecha 'Hasta'."))
        
        # Eliminar registros anteriores para este usuario
        self.env['stock.report.balance'].search([('create_uid', '=', self._uid)]).unlink()
        
        # Llamar al método de cálculo en el modelo de reporte
        self.env['stock.report.balance'].generate_report_data(
            self.date_from, 
            self.date_to, 
            self.warehouse_ids.ids, 
            self.category_ids.ids,
            self.company_id.id
        )

        return {
            'name': _('Balance de Inventario (Kardex)'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.report.balance',
            'view_mode': 'tree,pivot,form',
            'target': 'main',
        }

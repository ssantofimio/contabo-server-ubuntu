from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_open_change_date_wizard(self):
        return {
            'name': 'Reprogramar Fecha',
            'type': 'ir.actions.act_window',
            'res_model': 'change.scheduled.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,  # aquí pasamos el picking actual al wizard
            }
        }

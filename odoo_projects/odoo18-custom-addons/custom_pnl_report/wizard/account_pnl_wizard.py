from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountPnLWizard(models.TransientModel):
    _name = 'account.pnl.wizard'
    _description = 'Wizard for Estado de Resultados'

    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    date_from = fields.Date(string='Fecha Desde', required=True)
    date_to = fields.Date(string='Fecha Hasta', required=True)
    target_move = fields.Selection([
        ('posted', 'Todos los Asientos Asentados'),
        ('all', 'Todos los Asientos'),
    ], string='Movimientos Destino', required=True, default='posted')

    def check_report(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'company_id': self.company_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'target_move': self.target_move,
            }
        }
        return self.env.ref('custom_pnl_report.action_report_pnl').report_action(self, data=data)

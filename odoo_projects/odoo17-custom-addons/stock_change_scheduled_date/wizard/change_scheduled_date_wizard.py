from odoo import api, fields, models

class ChangeScheduledDateWizard(models.TransientModel):
    _name = "change.scheduled.date.wizard"
    _description = "Wizard para cambiar fecha programada de un picking"

    picking_id = fields.Many2one("stock.picking", string="Picking")
    scheduled_date = fields.Datetime("Nueva Fecha Programada", required=True)

    def change_date(self):
        self.picking_id.write({
            'scheduled_date': self.scheduled_date
        })

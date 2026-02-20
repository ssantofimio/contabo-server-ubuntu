from odoo import models, api, _
from odoo.exceptions import ValidationError

class ITAssignmentReport(models.AbstractModel):
    _name = 'report.sandor_it_inventory.report_it_assignment_template'
    _description = 'IT Assignment Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['it.assignment'].browse(docids)
        for doc in docs:
            if not doc.line_ids:
                raise ValidationError(_(
                    "No se puede imprimir el Acta de Entrega porque no existen productos asignados en 'Productos TIC'. "
                    "Por favor, agregue al menos un producto antes de imprimir."
                ))
        return {
            'doc_ids': docids,
            'doc_model': 'it.assignment',
            'docs': docs,
            'data': data,
        }

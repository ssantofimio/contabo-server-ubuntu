from odoo import models, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def write(self, values):
        # Llama al método original para guardar los cambios
        result = super().write(values)

        # Si el movimiento ya está en estado 'done' o 'cancelado'
        if self.state in ['done', 'cancel']:
            # Y el campo 'scheduled_date' está en los valores a cambiar
            # Y el usuario no pertenece al grupo de seguridad que le da permiso
            if 'scheduled_date' in values \
                and not self.env.user.has_group('stock_edit_scheduled_date.edit_scheduled_date_group_user'):
                # Si las condiciones se cumplen, lanza un error personalizado
                raise UserError(_("You have no access to change 'Scheduled Date' on a done or cancelled transfer."))
        return result

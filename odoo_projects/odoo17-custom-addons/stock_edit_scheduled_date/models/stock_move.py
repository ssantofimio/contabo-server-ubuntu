# /stock_edit_scheduled_date/models/stock_move.py

from odoo import models

class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        # La validación se dispara en el campo 'date', que es la fecha de los movimientos.
        if 'date' in vals:
            # Simplemente ignora la validación si el movimiento está hecho o cancelado.
            return super(StockMove, self.with_context(bypass_move_date_check=True)).write(vals)

        return super(StockMove, self).write(vals)

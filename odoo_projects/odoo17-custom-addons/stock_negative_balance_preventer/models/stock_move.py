
from odoo import models, api, exceptions, _

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        for move in self:
            if move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal':
                if move.product_uom_qty > move.product_id.qty_available:
                    raise exceptions.ValidationError(
                        _('Not enough stock for product: %s') % move.product_id.name
                    )
        return super(StockMove, self)._action_done(cancel_backorder)

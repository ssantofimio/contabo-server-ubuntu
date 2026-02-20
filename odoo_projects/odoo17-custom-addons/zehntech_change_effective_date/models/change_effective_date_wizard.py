from odoo import models,fields
from odoo.exceptions import UserError, ValidationError
import logging
from odoo import _
_logger = logging.getLogger(__name__)


class ChangeEffectiveDateWizard(models.Model):
    _name = 'change.effective.date.wizard'
    _description = 'Wizard to Change Effective Date'

    picking_id = fields.Many2one('stock.picking', required=True)
    new_effective_date = fields.Datetime(string="New Effective Date",help="Set the new effective date for the stock transfer. This date will be used to recalculate the stock valuation based on the currency rate at that time."
)
    def apply_new_effective_date(self):
        new_date = self.new_effective_date
        if not new_date:
            raise ValidationError(_("Please set the Effective date"))
        pickingid = self.picking_id
        pickingid.write({'date_done': new_date})
        if pickingid.picking_type_id.code == 'incoming' and pickingid.purchase_id:
            currencyid = pickingid.purchase_id.currency_id
            rate = self.env['res.currency.rate'].search([
                    ('currency_id', '=', currencyid.id),
                    ('name', '<=', new_date),
                ], order='name desc', limit=1)
            if not rate:
                rate = self.env['res.currency.rate'].search([
                    ('currency_id', '=', currencyid.id),
                ], order='name desc', limit=1)
            if not rate:
                raise ValidationError(_("No Exchange rate found for this currency"))
            for move in pickingid.move_ids:
                purchase_line = move.purchase_line_id
                vendor_unit_price = purchase_line.price_unit
                vendor_currency_rate_at_date = rate.inverse_company_rate
                product_qty = move.product_uom_qty
                total_value = vendor_unit_price*vendor_currency_rate_at_date*product_qty
                valuation_layer = self.env['stock.valuation.layer'].search([
                        ('stock_move_id', '=', move.id)
                    ], limit=1)
                if valuation_layer:
                        valuation_layer.write({
                            'create_date': new_date,
                            'value': total_value,
                            'unit_cost': total_value/product_qty,
                        })
                        try:
                            self.env.cr.execute(
                            "UPDATE stock_valuation_layer SET create_date = %s WHERE id = %s",
                            (new_date, valuation_layer.id) 
                            )
                            self.env.cr.commit()
                        except Exception as e:
                            raise ValidationError(_(F"Error while updating the create_date: {e}"))
                        update_valuation_layer = self.env['stock.valuation.layer'].browse(valuation_layer.id)
        elif pickingid.picking_type_id.code == 'outgoing':
            effective_date = new_date
            for move in pickingid.move_ids:
                valuation_layer = self.env['stock.valuation.layer'].search([
                        ('stock_move_id', '=', move.id)
                    ], limit=1)
                if valuation_layer:
                    self.env.cr.execute("""
                        UPDATE stock_valuation_layer 
                        SET create_date = %s 
                        WHERE id = %s
                    """, (effective_date, valuation_layer.id))
                    self.env.cr.commit()
        # raise ValidationError(F"currency rate 1 USD in rupees is {rate.inverse_company_rate}")
        # currency_name = currencyid.name
        # inverse_company_rate
        # raise ValidationError(F"picking id is {pickingid} and date is {pickingid.date_done} currency is {currency_name}")
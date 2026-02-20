
from odoo import _, models
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _get_available_quantity(
        self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False
    ):
        res = super()._get_available_quantity(
            product_id=product_id,
            location_id=location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=strict,
            allow_negative=allow_negative,
        )
        if location_id and not location_id.allow_negative_stock and res < -0.003 and location_id.usage == "internal":
            err = _(
                "\nNo hay suficiente stock del producto [{product_ref}] {product_name}, hacen falta {lot_qty} unidades en la ubicación {location_name} para completar la operación de inventario. "
                "Por favor, verifica el stock actual o realiza una actualización mediante un movimiento de ajuste de existencias."
            ).format(
                lot_qty=abs(res),
                product_ref=product_id.default_code or '',
                product_name=product_id.name or '',
                location_name=location_id.name or '',
            ) 
            raise UserError(err)
        return res

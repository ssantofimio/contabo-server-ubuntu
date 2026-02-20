# Copyright 2022 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

from odoo import api, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type="form", **options):
        key = super()._get_view_cache_key(
            view_id=view_id, view_type=view_type, options=options
        )
        return key + (
            self.env.user.has_group("stock_restrict_delete.delivery_delete_group"),
        )

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "form" and not self.env.user.has_group(
            "stock_restrict_delete.delivery_delete_group"
        ):
            for node in arch.xpath("//form"):
                node.set("delete", "0")
        if view_type == "tree" and not self.env.user.has_group(
            "stock_restrict_delete.delivery_delete_group"
        ):
            for node in arch.xpath("//tree"):
                node.set("delete", "0")
        return arch, view

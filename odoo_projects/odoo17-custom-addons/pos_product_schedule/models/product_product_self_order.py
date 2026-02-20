# -*- coding: utf-8 -*-
from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_self_order_data(self, pos_config):
        data = super()._get_self_order_data(pos_config)
        # Add schedule fields to each product
        for product_data in data:
            product = self.browse(product_data['id'])
            product_data.update({
                'pos_weekday_ids': product.pos_weekday_ids.read(['id', 'name']) or [],
                'pos_time_start': product.pos_time_start,
                'pos_time_end': product.pos_time_end,
            })
        return data
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta

class RestaurantTable(models.Model):
    _inherit = "restaurant.table"

    def _get_self_order_data(self):
        res = super()._get_self_order_data()
        
        # Check if table has active confirmed orders in the last 24h
        active_orders = self.env['pos.order'].sudo().search_count([
            ('table_id', '=', self.id),
            ('state', 'not in', ['paid', 'cancel']),
            ('date_order', '>=', fields.Datetime.now() - timedelta(hours=24)),
        ])
        
        res['id'] = self.id
        res['is_busy'] = active_orders > 0
        return res

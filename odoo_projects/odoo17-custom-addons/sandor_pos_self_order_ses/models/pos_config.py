# -*- coding: utf-8 -*-
from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    self_order_custom_identification = fields.Boolean(
        string="Custom Identification Flow",
        help="Enable custom NIF/Customer identification flow for self-ordering.",
        default=False
    )

    def _get_self_ordering_data(self):
        res = super()._get_self_ordering_data()
        if 'config' in res:
            res['config'].update({
                'self_order_custom_identification': self.self_order_custom_identification,
            })
        if 'company' in res:
            res['company'].update({
                'id': self.company_id.id,
                'country_id': self.company_id.country_id.id,
            })
        return res

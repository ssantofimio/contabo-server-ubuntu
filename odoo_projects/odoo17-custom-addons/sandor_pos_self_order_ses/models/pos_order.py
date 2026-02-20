# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = "pos.order"

    def _export_for_self_order(self):
        res = super()._export_for_self_order()
        if self.partner_id:
            res.update({
                'partner_id': self.partner_id.id,
                'partner_name': self.partner_id.name,
                'partner_vat': self.partner_id.vat,
                'partner_phone': self.partner_id.phone,
                'partner_mobile': self.partner_id.mobile,
                'partner_email': self.partner_id.email,
            })
        return res

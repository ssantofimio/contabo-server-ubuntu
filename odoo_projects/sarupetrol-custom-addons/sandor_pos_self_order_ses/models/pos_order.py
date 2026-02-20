# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        
        # If params is empty, it means we must provide at least the base fields
        # requested by the Autopedido frontend.
        base_fields = [
            'name', 'lines', 'amount_total', 'amount_tax', 'amount_paid', 'amount_return',
            'pos_reference', 'date_order', 'uuid', 'access_token', 'state', 'partner_id',
            'config_id', 'session_id', 'table_id', 'tracking_number', 'last_order_preparation_change',
            'general_note', 'nb_print', 'to_invoice', 'shipping_date'
        ]
        
        if not params:
            params = base_fields
        else:
            for field in base_fields:
                if field not in params:
                    params.append(field)

        custom_fields = ['partner_name', 'partner_vat', 'partner_phone', 'partner_mobile', 'partner_email']
        for field in custom_fields:
            if field not in params:
                params.append(field)
                
        return params

    partner_name = fields.Char(related='partner_id.name', store=False)
    partner_vat = fields.Char(related='partner_id.vat', store=False)
    partner_phone = fields.Char(related='partner_id.phone', store=False)
    partner_mobile = fields.Char(related='partner_id.mobile', store=False)
    partner_email = fields.Char(related='partner_id.email', store=False)

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

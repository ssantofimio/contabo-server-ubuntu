# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_self_order_custom_identification = fields.Boolean(
        related='pos_config_id.self_order_custom_identification',
        readonly=False,
        string="Custom Identification Flow"
    )

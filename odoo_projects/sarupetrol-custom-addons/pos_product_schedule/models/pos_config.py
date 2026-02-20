# -*- coding: utf-8 -*-
from odoo import models
import datetime
import pytz


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _load_self_data_models(self):
        models = super()._load_self_data_models()
        if 'pos.product.schedule' not in models:
            models.append('pos.product.schedule')
        return models
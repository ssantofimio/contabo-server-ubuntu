# -*- coding: utf-8 -*-
from odoo import models, fields
import datetime
import pytz


class PosSession(models.Model):
    _inherit = 'pos.session'

    # In Odoo 18, data loading is handled via pos.load.mixin on each model.
    # The product fields and domain are now managed in product_product.py 
    # overriding _load_pos_data_fields and _load_pos_data_domain.

    def _loader_params_pos_product_schedule(self):

        # Include schedules in the initial loaded_data so the client can access
        # them without extra RPCs (helps in environments where direct RPCs
        # from the client may be blocked).
        return {'search_params': {'domain': [], 'fields': ['id', 'name', 'code', 'bit', 'sequence']}}

    def _get_pos_ui_pos_product_schedule(self, params):
        return self.env['pos.product.schedule'].search_read(**params['search_params'])

    def _pos_ui_models_to_load(self):
        models = super()._pos_ui_models_to_load()
        if 'pos.product.schedule' not in models:
            models.append('pos.product.schedule')
        return models

    def _pos_data_process(self, loaded_data):
        # Reuse the pos_session process from parent but attach schedules payload
        # into the pos.session record so the client can access them easily.
        res = super()._pos_data_process(loaded_data)
        try:
            schedules = loaded_data.get('pos.product.schedule')
            if schedules:
                # Ensure pos.session key exists and attach schedules
                if 'pos.session' in loaded_data and isinstance(loaded_data['pos.session'], dict):
                    loaded_data['pos.session']['pos_product_schedules'] = schedules
        except Exception:
            pass
        return res

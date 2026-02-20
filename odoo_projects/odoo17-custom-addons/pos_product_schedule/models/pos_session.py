# -*- coding: utf-8 -*-
from odoo import models, fields
import datetime
import pytz


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        if 'search_params' in result and 'fields' in result['search_params']:
            # Load pos_weekday_ids so the JS can compute availability efficiently
            # from the many2many relation without relying on a separate mask field.
            result['search_params']['fields'].extend(['pos_weekday_ids', 'pos_time_start', 'pos_time_end'])
            # Add a server-side domain to filter products according to today's
            # schedule (based on the session config timezone). This prevents
            # sending products to the client that are not available today and
            # avoids stale cached products showing up.
            try:
                tz_name = self.config_id.tz or self.env.user.tz or 'UTC'
                tz = pytz.timezone(tz_name)
                now = datetime.datetime.now(tz)
                # isoweekday: Monday=1 .. Sunday=7 (same convention as schedule.sequence)
                today_seq = now.isoweekday()
                sched = self.env['pos.product.schedule'].search([('sequence', '=', today_seq)], limit=1)
                if sched:
                    domain = result['search_params'].get('domain', [])
                    # Filter by product.template schedules (many2many on template) so the
                    # server search works reliably. Keep products whose template has no
                    # restriction (no pos_weekday_ids) OR whose template includes today's schedule.
                    # Use product_tmpl_id.pos_weekday_ids to reference the template m2m.
                    domain += ['|', ('product_tmpl_id.pos_weekday_ids', '=', False), ('product_tmpl_id.pos_weekday_ids', 'in', [sched.id])]

                    # Nuevo: Filtrado por hora
                    current_hour = now.hour + now.minute / 60.0
                    # Lógica: Si ambos time_start y time_end son None o 0, permitir (sin restricción)
                    # Si solo uno es válido, aplicar rango parcial
                    # Si ambos válidos, aplicar rango completo
                    time_domain = [
                        '|',  # OR para casos sin restricción
                        '&', ('product_tmpl_id.pos_time_start', '=', False), ('product_tmpl_id.pos_time_end', '=', False),  # Ambos None (sin restricción)
                        '|',  # OR para casos con restricción
                        '&', ('product_tmpl_id.pos_time_start', '!=', False), ('product_tmpl_id.pos_time_end', '!=', False),  # Ambos no None
                        '&', ('product_tmpl_id.pos_time_start', '>=', current_hour), ('product_tmpl_id.pos_time_end', '<=', current_hour),  # Rango válido
                        '|',  # OR para rangos parciales
                        '&', ('product_tmpl_id.pos_time_start', '!=', False), ('product_tmpl_id.pos_time_end', '=', False), ('product_tmpl_id.pos_time_start', '<=', current_hour),  # Solo start: >= start
                        '&', ('product_tmpl_id.pos_time_end', '!=', False), ('product_tmpl_id.pos_time_start', '=', False), ('product_tmpl_id.pos_time_end', '>=', current_hour),  # Solo end: <= end
                    ]
                    # Nota: Esta domain es compleja; ajusta según Odoo. Para simplificar, podrías usar una condición más directa o un método personalizado.
                    domain += time_domain
                    result['search_params']['domain'] = domain
            except Exception:
                # If anything fails, do not break loading: keep previous result
                pass
        return result

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

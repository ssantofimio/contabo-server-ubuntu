# -*- coding: utf-8 -*-
from odoo import models
import datetime
import pytz


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_self_ordering_data(self):
        data = super()._get_self_ordering_data()
        # Add schedules for product filtering
        data['pos_product_schedules'] = self.env['pos.product.schedule'].search_read([], ['id', 'name', 'code', 'bit', 'sequence'])
        # Add timezone to config
        data['config']['tz'] = self.env.user.tz or self.company_id.tz or 'UTC'

        # Server-side: filter products according to today's schedule and time window
        # This prevents sending disallowed products to the self-order client and
        # keeps the behaviour consistent with POS session loader filtering.
        try:
            tz_name = data['config'].get('tz') or self.env.user.tz or self.company_id.tz or 'UTC'
            tz = pytz.timezone(tz_name)
            now = datetime.datetime.now(tz)
            today_seq = now.isoweekday()
            sched = self.env['pos.product.schedule'].search([('sequence', '=', today_seq)], limit=1)
            if sched and data.get('products'):
                def product_allowed(product):
                    # product may contain pos_weekday_ids as [{id, name}, ..] or []
                    weekday_ids = product.get('pos_weekday_ids') or []
                    # Normalize to list of ids
                    if weekday_ids and isinstance(weekday_ids[0], dict):
                        allowed_ids = [int(x.get('id')) for x in weekday_ids]
                    elif weekday_ids and isinstance(weekday_ids[0], (list, tuple)):
                        allowed_ids = [int(x[0]) for x in weekday_ids]
                    else:
                        allowed_ids = [int(x) for x in weekday_ids] if weekday_ids else []

                    # Day allowed when no restriction or today's schedule contained
                    day_allowed = (len(allowed_ids) == 0) or (int(sched.id) in allowed_ids)

                    # Time check
                    time_start = product.get('pos_time_start')
                    time_end = product.get('pos_time_end')
                    time_allowed = True # Por defecto, permitir
                    if time_start is not None and time_end is not None:
                        # Ambos tienen valores: aplicar rango normal
                        if time_start > 0 or time_end > 0:
                            current_hour = now.hour + now.minute / 60.0
                            try:
                                time_allowed = (float(current_hour) >= float(time_start)) and (float(current_hour) <= float(time_end))
                            except Exception:
                                time_allowed = True
                        # Si ambos son 0, ya está en True por defecto
                    elif time_start is not None and time_start > 0:
                        # Solo start válido: de start a 24
                        current_hour = now.hour + now.minute / 60.0
                        try:
                            time_allowed = float(current_hour) >= float(time_start)
                        except Exception:
                            time_allowed = True
                    elif time_end is not None and time_end > 0:
                        # Solo end válido: de 0 a end
                        current_hour = now.hour + now.minute / 60.0
                        try:
                            time_allowed = float(current_hour) <= float(time_end)
                        except Exception:
                            time_allowed = True
                    # Si ambos None o start/end == 0, time_allowed ya es True
                    return day_allowed and time_allowed

                data['products'] = [p for p in data.get('products', []) if product_allowed(p)]
        except Exception:
            # Do not break self-order page loading on exceptions; keep default data
            pass
        return data
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # expose template fields on product.product for POS loader
    pos_weekday_ids = fields.Many2many(related='product_tmpl_id.pos_weekday_ids', readonly=False)
    pos_time_start = fields.Float(related='product_tmpl_id.pos_time_start', readonly=False)
    pos_time_end = fields.Float(related='product_tmpl_id.pos_time_end', readonly=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['pos_weekday_ids', 'pos_time_start', 'pos_time_end']
        return params

    @api.model
    def _load_pos_data_domain(self, data):
        domain = super()._load_pos_data_domain(data)
        config_id = data.get('pos.config', {}).get('data', [{}])[0].get('id')
        config = self.env['pos.config'].browse(config_id)
        return self._get_availability_domain(domain, config)

    @api.model
    def _load_pos_self_data_fields(self, config_id):
        params = super()._load_pos_self_data_fields(config_id)
        params += ['pos_weekday_ids', 'pos_time_start', 'pos_time_end']
        return params

    @api.model
    def _load_pos_self_data_domain(self, data):
        domain = super()._load_pos_self_data_domain(data)
        config_id = data.get('pos.config', {}).get('data', [{}])[0].get('id')
        config = self.env['pos.config'].browse(config_id)
        return self._get_availability_domain(domain, config)

    def _get_availability_domain(self, domain, config):
        try:
            import pytz
            import datetime
            tz_name = self.env.user.tz or config.company_id.partner_id.tz or 'UTC'
            tz = pytz.timezone(tz_name)
            now = datetime.datetime.now(tz)
            today_seq = now.isoweekday()
            sched = self.env['pos.product.schedule'].search([('sequence', '=', today_seq)], limit=1)
            
            # Day logic
            if sched:
                domain += ['|', ('product_tmpl_id.pos_weekday_ids', '=', False), ('product_tmpl_id.pos_weekday_ids', 'in', [sched.id])]
            else:
                domain += [('product_tmpl_id.pos_weekday_ids', '=', False)]

            # Time logic
            h = now.hour + now.minute / 60.0
            time_domain = [
                '|',
                    '&', ('product_tmpl_id.pos_time_start', '=', 0), ('product_tmpl_id.pos_time_end', '=', 0),
                '|',
                    '&', '&', ('product_tmpl_id.pos_time_start', '>', 0), ('product_tmpl_id.pos_time_end', '>', 0),
                         '&', ('product_tmpl_id.pos_time_start', '<=', h), ('product_tmpl_id.pos_time_end', '>=', h),
                '|',
                    '&', ('product_tmpl_id.pos_time_start', '<=', h), ('product_tmpl_id.pos_time_end', '=', 0),
                    '&', ('product_tmpl_id.pos_time_end', '>=', h), ('product_tmpl_id.pos_time_start', '=', 0)
            ]
            domain += time_domain
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Failed to apply pos_product_schedule domain: %s", e)
            
        return domain



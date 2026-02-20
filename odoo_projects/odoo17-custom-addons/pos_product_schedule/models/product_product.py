# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # expose template fields on product.product for POS loader
    pos_weekday_ids = fields.Many2many(related='product_tmpl_id.pos_weekday_ids', readonly=False)
    pos_time_start = fields.Float(related='product_tmpl_id.pos_time_start', readonly=False)
    pos_time_end = fields.Float(related='product_tmpl_id.pos_time_end', readonly=False)

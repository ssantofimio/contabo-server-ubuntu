# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosProductSchedule(models.Model):
    _name = 'pos.product.schedule'
    _inherit = 'pos.load.mixin'
    _description = 'POS Product Schedule'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=0)
    code = fields.Char(string='Code', help='Short code for schedule. Any value allowed (eg. MON, 1, ...).')
    bit = fields.Integer(string='Bit', required=True, help='Bit value for schedule mask.')
    active = fields.Boolean(string='Active', default=True)
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_weekday_ids = fields.Many2many('pos.product.schedule', 'pos_product_template_schedule_rel', 'product_tmpl_id', 'schedule_id', string='Días Disponibles', help='Schedule on which this product is available on POS')
    pos_time_start = fields.Float(string='Hora Inicio', help='Hora de inicio de disponibilidad (formato 24h, ej: 7.0 para 07:00)')
    pos_time_end = fields.Float(string='Hora Fin', help='Hora de fin de disponibilidad (formato 24h, ej: 10.0 para 10:00)')
    # Horario de disponibilidad para el POS (expuestos en product.product con campos related)



    # NOTE: We intentionally do NOT compute/store any bit mask on the product
    # template. The availability filtering in POS uses the many2many
    # relation `pos_weekday_ids` as the single source of truth.

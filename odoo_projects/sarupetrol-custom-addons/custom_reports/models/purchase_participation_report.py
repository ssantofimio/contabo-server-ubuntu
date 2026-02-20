# -*- coding: utf-8 -*-
from odoo import fields, models, api

class PurchaseReportParticipation(models.Model):
    _name = "purchase.report.participation"
    _description = "Reporte de Participación de Compras"
    _inherit = "purchase.report"
    _auto = False

    participation_percent = fields.Float('Participación (%)', readonly=True, group_operator='avg', digits=(16, 4))

    def _select(self):
        # El campo picking_type_id ya viene en super()._select() gracias a purchase_stock
        return super()._select() + ", 0.0 as participation_percent"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(PurchaseReportParticipation, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        
        if 'participation_percent' in fields:
            # Obtener el total general para el mismo dominio filtrado
            groups = super(PurchaseReportParticipation, self).read_group(domain, ['price_total'], [])
            grand_total = groups[0]['price_total'] if groups and groups[0].get('price_total') else 0
            
            if grand_total:
                for line in res:
                    if 'price_total' in line:
                        line['participation_percent'] = (line['price_total'] / grand_total)
        return res

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        res = super().web_search_read(domain, specification, offset=offset, limit=limit, order=order, count_limit=count_limit)
        if 'participation_percent' in specification:
            # Obtener el total general para el mismo dominio (100% base)
            groups = super(PurchaseReportParticipation, self).read_group(domain, ['price_total'], [])
            grand_total = groups[0]['price_total'] if groups and groups[0].get('price_total') else 0
            
            if grand_total:
                for record in res['records']:
                    if 'price_total' in record:
                        record['participation_percent'] = record['price_total'] / grand_total
        return res


# -*- coding: utf-8 -*-
from odoo import models, api

class PurchaseReportParser(models.AbstractModel):
    _name = 'report.custom_reports.report_purchase_order_table'
    _description = 'Purchase Report Table Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Parsea los datos del wizard y las órdenes seleccionadas
        para pasarlos al template del reporte.
        """
        if not data:
            data = {}
            
        # Si venimos del wizard, 'columns' estará en data
        # Si no (impresión directa), usaremos valores por defecto (todo True)
        columns = data.get('columns')
        
        # Obtener los registros (órdenes de compra)
        # 1. Intentar obtener desde data['order_ids'] (enviado por el wizard)
        if data.get('order_ids'):
            docids = data['order_ids']
        # 2. Si no, usar docids original (si no está vacío)
        elif not docids and data.get('context', {}).get('active_ids'):
            # 3. Si no, intentar obtener desde active_ids del contexto
            docids = data['context']['active_ids']
            
        docs = self.env['purchase.order'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': docs,
            'data': data,
            'columns': columns or {}, 
            'report_title': data.get('report_title'), # Pasar título personalizado si existe
        }

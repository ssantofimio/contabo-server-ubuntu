# -*- coding: utf-8 -*-
from odoo import api, models

class ReportStockPhysCount(models.AbstractModel):
    _name = 'report.custom_reports.report_stock_phys_count_document'
    _description = 'Abstract Model for Stock Physical Count Report'

    @api.model
    @api.model
    def _get_report_values(self, docids, data=None):
        # 1. Obtener el dominio de búsqueda
        domain = data.get('active_domain', []) if data else []
        if not domain and docids:
            domain = [('id', 'in', docids)]
        if not domain:
            domain = self.env.context.get('active_domain', [])
            
        # 2. Obtener método de valorización
        valuation_method = data.get('valuation_method') if data else None
        if not valuation_method:
            valuation_method = self.env.context.get('valuation_method') or 'avg'
            
        # 3. Buscar datos
        docs_data = self.env['stock.report.phys.count'].with_context(valuation_method=valuation_method).sudo().search(domain)
        
        # 4. Agrupar por almacén
        grouped_docs = {}
        for doc in docs_data:
            wh_name = doc.warehouse_id.name if doc.warehouse_id else 'Sin Almacén'
            if wh_name not in grouped_docs:
                grouped_docs[wh_name] = self.env['stock.report.phys.count']
            grouped_docs[wh_name] |= doc
        
        # 5. Formatear para el template
        final_docs = []
        # Ordenar por nombre de almacén para consistencia
        for wh in sorted(grouped_docs.keys()):
            final_docs.append({
                'warehouse': wh,
                'lines': grouped_docs[wh]
            })
 
        return {
            'doc_ids': docids,
            'doc_model': 'stock.report.phys.count',
            'grouped_data': final_docs,
            'valuation_method': valuation_method,
            'res_company': self.env.company,
        }

class ReportStockPhysSummary(models.AbstractModel):
    _name = 'report.custom_reports.report_stock_phys_summary_document'
    _description = 'Abstract Model for Stock Physical Count Summary Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        domain = data.get('active_domain', []) if data else []
        if not domain and docids:
            domain = [('id', 'in', docids)]
        if not domain:
            domain = self.env.context.get('active_domain', [])

        valuation_method = data.get('valuation_method') if data else None
        if not valuation_method:
            valuation_method = self.env.context.get('valuation_method') or 'avg'
        
        val_total_field = 'val_last' if valuation_method == 'last' else 'val_avg'
        group_fields = ['expected_qty', 'counted_qty', 'difference', val_total_field]
        groupby = ['warehouse_id', 'product_categ_id']
        
        groups = self.env['stock.report.phys.count'].sudo().read_group(domain, group_fields, groupby, lazy=False)
        
        grouped_summary = {}
        for g in groups:
            wh_name = g.get('warehouse_id')[1] if g.get('warehouse_id') else 'Sin Almacén'
            if wh_name not in grouped_summary:
                grouped_summary[wh_name] = []
            
            grouped_summary[wh_name].append({
                'category': g.get('product_categ_id')[1] if g.get('product_categ_id') else '',
                'expected_qty': g.get('expected_qty', 0.0),
                'counted_qty': g.get('counted_qty', 0.0),
                'difference': g.get('difference', 0.0),
                'total_value': g.get(val_total_field, 0.0),
            })
        
        final_summary = []
        for wh in sorted(grouped_summary.keys()):
            final_summary.append({
                'warehouse': wh,
                'categories': grouped_summary[wh]
            })
        
        return {
            'doc_ids': docids,
            'doc_model': 'stock.report.phys.count',
            'grouped_data': final_summary,
            'res_company': self.env.company,
            'valuation_method': valuation_method,
        }

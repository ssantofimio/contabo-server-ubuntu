# -*- coding: utf-8 -*-
from odoo import models, api
import datetime

class ReportPriceHistory(models.AbstractModel):
    _name = 'report.custom_reports.report_price_history_document'
    _description = 'Price History Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        domain = data.get('active_domain') if data else []
        if domain:
            docs = self.env['purchase.report.price.history'].search(domain)
        elif docids:
            docs = self.env['purchase.report.price.history'].browse(docids)
        else:
            docs = self.env['purchase.report.price.history'].search([])
        
        # Extraer información para el resumen formal del encabezado y filtros adicionales
        summary = {
            'warehouses': 'Todos',
            'date_from': False,
            'date_to': False,
        }
        other_filters = []
        for leaf in domain:
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                field, op, value = leaf
                if field == 'warehouse_id':
                    ids = [value] if isinstance(value, int) else value
                    names = self.env['stock.warehouse'].browse(ids).mapped('name')
                    summary['warehouses'] = ', '.join(names)
                elif field == 'date':
                    if op == '>=':
                        summary['date_from'] = value
                    elif op == '<=':
                        summary['date_to'] = value
                elif field == 'product_categ_id':
                    ids = [value] if isinstance(value, int) else value
                    names = self.env['product.category'].browse(ids).mapped('name')
                    other_filters.append(f"Categorías: {', '.join(names)}")
                elif field == 'product_id':
                    ids = [value] if isinstance(value, int) else value
                    names = self.env['product.product'].browse(ids).mapped('display_name')
                    other_filters.append(f"Productos: {', '.join(names)}")
                elif field == 'partner_id':
                    ids = [value] if isinstance(value, int) else value
                    names = self.env['res.partner'].browse(ids).mapped('name')
                    other_filters.append(f"Proveedores: {', '.join(names)}")

        # Agrupar datos por (Almacén, Ubicación, Categoría, Producto, Mes)
        groups = {}
        for record in docs:
            # Extraer mes (Formato: Mes AAAA)
            month_label = record.date.strftime('%B %Y') if record.date else 'N/A'
            key = (
                record.warehouse_id.id,
                record.location_id.id,
                record.product_categ_id.id,
                record.product_id.id,
                month_label
            )
            if key not in groups:
                groups[key] = {
                    'month': month_label,
                    'month_date': record.date or datetime.date.min, # Para ordenar cronológicamente
                    'warehouse': record.warehouse_id.name or '',
                    'location': record.location_id.name or '',
                    'category': record.product_categ_id.complete_name or '',
                    'product_id': record.product_id.id,
                    'product_name': record.product_id.display_name or '',
                    'uom': record.uom_id.name or '',
                    'quantity': 0.0,
                    'total': 0.0,
                    'invoice_ids': set()
                }
            
            groups[key]['quantity'] += record.quantity
            groups[key]['total'] += record.price_total
            groups[key]['invoice_ids'].add(record.invoice_id.id)

        # Estructurar para el template: Categoría -> Producto -> Líneas (Meses)
        temp_dict = {}
        for key in sorted(groups.keys(), key=lambda k: (groups[k]['category'], groups[k]['product_name'], groups[k]['month_date'])):
            val = groups[key]
            val['price_unit'] = val['total'] / val['quantity'] if val['quantity'] else 0.0
            val['invoice_count'] = len(val['invoice_ids'])
            
            cat_name = val['category'] or 'Sin Categoría'
            prod_name = val['product_name'] or 'Sin Producto'
            
            if cat_name not in temp_dict:
                temp_dict[cat_name] = {}
            if prod_name not in temp_dict[cat_name]:
                temp_dict[cat_name][prod_name] = []
            
            temp_dict[cat_name][prod_name].append(val)

        # Convertir a lista final
        final_groups = []
        grand_total = 0.0
        unique_months = set()
        
        for cat in sorted(temp_dict.keys()):
            cat_total = 0.0
            product_list = []
            for prod in sorted(temp_dict[cat].keys()):
                prod_lines = temp_dict[cat][prod]
                prod_total = sum(l['total'] for l in prod_lines)
                cat_total += prod_total
                
                for l in prod_lines:
                    unique_months.add(l['month'])
                
                product_list.append({
                    'product': prod,
                    'lines': prod_lines,
                    'total': prod_total
                })
            
            grand_total += cat_total
            final_groups.append({
                'category': cat,
                'products': product_list,
                'total': cat_total
            })

        return {
            'doc_ids': docids or docs.ids,
            'doc_model': 'purchase.report.price.history',
            'docs': docs,
            'grouped_data': final_groups,
            'grand_total': grand_total,
            'is_multi_month': len(unique_months) > 1,
            'summary': summary,
            'other_filters': other_filters,
            'datetime': datetime,
        }

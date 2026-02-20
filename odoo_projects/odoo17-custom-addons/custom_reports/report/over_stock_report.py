# -*- coding: utf-8 -*-
###############################################################################
#
#  Cybrosys Technologies Pvt. Ltd.
#
#  Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#  Author: Jumana Haseen (odoo@cybrosys.com)
#
#  You can modify it under the terms of the GNU LESSER
#  GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#  You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#  (LGPL v3) along with this program.
#  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class OverStockReport(models.AbstractModel):
    """Create an abstract model for passing reporting values"""
    _name = 'report.custom_reports.report_inventory_over_stock'
    _description = 'Over Stock Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """This function has working in get the pdf report."""
        values = data
        if data is None or not isinstance(data, dict):
            raise ValueError("Datos inválidos o faltantes para el reporte")
        product_ids = data.get('product_ids', [])
        category_ids = data.get('category_ids', [])
        company_ids = data.get('company_ids', [])
        warehouse_ids = data.get('warehouse_ids', [])
        inventory_for_next_x_days = data.get('inventory_for_next_x_days', [])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if not start_date or not end_date:
            raise ValueError(
                "Falta la fecha de inicio o fin en los datos")
        processed_product_ids = []
        filtered_result_data = []
        query = """
                    SELECT
                            product_id,
                            product_code_and_name,
                            category_id,
                            category_name,
                            company_id,
                            current_stock,
                            warehouse_id,
                            incoming_quantity,
                            outgoing_quantity,
                            virtual_stock,
                            sales,
                            ads,
                            advance_stock_days,
                            ROUND(advance_stock_days * ads, 0) 
                            AS demanded_quantity,
                            ROUND(CASE
                        WHEN ads = 0 THEN virtual_stock / 0.001
                        ELSE virtual_stock / ads
                    END,0) AS in_stock_days,
                    ROUND(virtual_stock-(ads*advance_stock_days),0) 
                    AS over_stock_qty,
                ROUND(
        CASE
        WHEN virtual_stock = 0 THEN 0 
        ELSE sales / virtual_stock
        END, 2
    ) AS turnover_ratio,
                CASE
                    WHEN
                        CASE
                            WHEN sales > 0 
                            THEN ROUND((sales / NULLIF(virtual_stock, 0)), 2)
                            ELSE 0
                        END > 3 THEN 'Alta Rotación'
                    WHEN
                        CASE
                            WHEN sales > 0 
                            THEN ROUND((sales / NULLIF(virtual_stock, 0)), 2)
                            ELSE 0
                        END >= 1 AND
                        CASE
                            WHEN sales > 0 
                            THEN ROUND((sales / NULLIF(virtual_stock, 0)), 2)
                            ELSE 0
                        END <= 3 THEN 'Baja Rotación'
                    ELSE 'Sin Movimiento'
                END AS fsn_classification
                FROM(
                SELECT 
                    CASE
                        WHEN pp.default_code IS NOT NULL 
                            THEN CONCAT(pp.default_code, ' - ', 
                            pt.name->>'en_US')
                        ELSE
                            pt.name->>'en_US'
                    END AS product_code_and_name,
                    company.id AS company_id,
                    company.name AS company_name,
                    sm.product_id AS product_id,
                    pc.id AS category_id,
                    pc.complete_name AS category_name,
                    sw.id AS warehouse_id,
                            SUM(CASE
                WHEN sld_dest.usage = 'internal' AND sm.state 
                IN ('assigned', 'confirmed', 'waiting') THEN sm.product_uom_qty
                ELSE 0
                END) AS incoming_quantity,
                SUM(CASE
                WHEN sld_src.usage = 'internal' AND sm.state 
                IN ('assigned', 'confirmed', 'waiting') THEN sm.product_uom_qty
                ELSE 0
                END) AS outgoing_quantity,
                SUM(CASE
                WHEN sld_dest.usage = 'internal' AND sm.state = 'done' 
                THEN sm.product_uom_qty
                ELSE 0
                END) -
                SUM(CASE
                WHEN sld_src.usage = 'internal' AND sm.state = 'done' 
                THEN sm.product_uom_qty
                ELSE 0
                END) AS current_stock,
                SUM(CASE
                WHEN sld_dest.usage = 'internal' AND sm.state = 'done' 
                THEN sm.product_uom_qty
                ELSE 0
                END) -
                SUM(CASE
                WHEN sld_src.usage = 'internal' AND sm.state = 'done' 
                THEN sm.product_uom_qty
                ELSE 0
                END)+
                SUM(CASE
                WHEN sld_dest.usage = 'internal' AND sm.state 
                IN ('assigned', 'confirmed', 'waiting') THEN sm.product_uom_qty
                ELSE 0
                END) -
                SUM(CASE
                WHEN sld_src.usage = 'internal' AND sm.state 
                IN ('assigned', 'confirmed', 'waiting') THEN sm.product_uom_qty
                ELSE 0
                END) AS virtual_stock,
                SUM(CASE WHEN sm.date BETWEEN %s AND %s 
                AND sld_dest.usage = 'customer' 
                THEN sm.product_uom_qty ELSE 0 END) AS sales,
                    ROUND(SUM(CASE
                WHEN sm.date BETWEEN %s AND %s AND sld_src.usage = 'internal' 
                AND sm.state = 'done' THEN sm.product_uom_qty
                ELSE 0
                END) / ((date %s - date %s)+1), 2) AS ads,
                %s AS advance_stock_days
                FROM stock_move sm
                INNER JOIN product_product pp ON pp.id = sm.product_id
                INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
                INNER JOIN res_company company ON company.id = sm.company_id
                INNER JOIN stock_warehouse sw ON sw.company_id = company.id
                INNER JOIN product_category pc ON pc.id = pt.categ_id
                LEFT JOIN (
                    SELECT sm.id AS move_id, usage
                    FROM stock_location sld
                    INNER JOIN stock_move sm ON sld.id = sm.location_dest_id
                ) sld_dest ON sm.id = sld_dest.move_id
                LEFT JOIN (
                    SELECT sm.id AS move_id, usage
                    FROM stock_location sld
                    INNER JOIN stock_move sm ON sld.id = sm.location_id
                ) sld_src ON sm.id = sld_src.move_id
                WHERE pp.active = TRUE
                        AND pt.active = TRUE
                        AND pt.type = 'product'
                        """
        params = [
            start_date, end_date,
            start_date, end_date,
            end_date, start_date,
            inventory_for_next_x_days
        ]
        sub_queries = []
        sub_params = []
        param_count = 0
        if product_ids or category_ids:
            query += " AND ("
        if product_ids:
            product_ids = [product_id for product_id in product_ids]
            query += "pp.id = ANY(%s)"
            params.append(product_ids)
            param_count += 1
        if product_ids and category_ids:
            query += " OR "
        if category_ids:
            category_ids = [category for category in category_ids]
            params.append(category_ids)
            query += "(pt.categ_id = ANY(%s))"
            param_count += 1
        if product_ids or category_ids:
            query += ")"
        if company_ids:
            company_ids = [company for company in company_ids]
            query += " AND (sm.company_id = ANY(%s))"
            sub_params.append(company_ids)
            param_count += 1
        if warehouse_ids:
            warehouse_ids = [warehouse for warehouse in warehouse_ids]
            query += " AND (sw.id = ANY(%s))"
            sub_params.append(warehouse_ids)
            param_count += 1
        if sub_queries:
            query += " AND " + " AND ".join(sub_queries)
        query += """ GROUP BY pp.id, pt.name, pc.id, company.id, sm.product_id, 
        sw.id) AS sub_query """
        self.env.cr.execute(query, tuple(params + sub_params))
        result_data = self.env.cr.dictfetchall()
        for data in result_data:
            product_id = data.get('product_id')
            if product_id not in processed_product_ids:
                processed_product_ids.append(
                    product_id)
                filtered_result_data.append(data)
        # Pre-calculate cost and purchase info in batch to avoid O(n^2) and too many queries
        product_ids = [data.get('product_id') for data in filtered_result_data]
        products = self.env['product.product'].browse(product_ids)
        product_map = {p.id: p for p in products}
        
        # Batch fetch purchase order lines
        confirmed_po_lines = self.env['purchase.order.line'].search([
            ('product_id', 'in', product_ids),
            ('state', '=', 'purchase'),
        ])
        po_line_map = {}
        for line in confirmed_po_lines:
            if line.product_id.id not in po_line_map:
                po_line_map[line.product_id.id] = line
            else:
                if po_line_map[line.product_id.id].date_approve < line.date_approve:
                    po_line_map[line.product_id.id] = line

        total_qty = sum(item.get('over_stock_qty', 0) for item in filtered_result_data)
        start_date_obj = fields.Date.from_string(start_date)
        end_date_obj = fields.Date.from_string(end_date)

        for data in filtered_result_data:
            over_stock_qty = data.get('over_stock_qty', 0)
            product_id = data.get('product_id')
            
            data['over_stock_qty_percentage'] = round((over_stock_qty / total_qty * 100), 2) if total_qty else 0.0
            
            product = product_map.get(product_id)
            cost = product.standard_price if product else 0
            data['cost'] = cost
            data['over_stock_value'] = over_stock_qty * cost
            
            latest_po = po_line_map.get(product_id)
            data.update({
                'po_qty': 0, 'po_price_total': 0, 'po_date': None,
                'po_currency': None, 'po_partner': None
            })
            
            if latest_po and latest_po.date_approve:
                po_date = fields.Datetime.from_string(latest_po.date_approve).date()
                if start_date_obj <= po_date <= end_date_obj:
                    data['po_qty'] = latest_po.product_qty
                    data['po_price_total'] = latest_po.price_total
                    data['po_date'] = latest_po.date_approve
                    data['po_currency'] = latest_po.currency_id.name
                    data['po_partner'] = latest_po.partner_id.name
                else:
                    data.update({'po_price_total': None, 'po_qty': None})
            else:
                data.update({'po_price_total': None, 'po_qty': None})

        total_value = sum(item.get('over_stock_value', 0) for item in filtered_result_data)
        for data in filtered_result_data:
            over_stock_value = data.get('over_stock_value')
            if total_value:
                over_stock_value_percentage = \
                    (over_stock_value / total_value) * 100
            else:
                over_stock_value_percentage = 0.0
            data['over_stock_value_percentage'] = round(
                over_stock_value_percentage, 2)
        if filtered_result_data:
            return {
                'doc_ids': docids,
                'doc_model':
                    'report.custom_reports.'
                    'report_inventory_over_stock',
                'data': values,
                'options': filtered_result_data,
            }
        else:
            raise ValidationError("No se encontraron registros para los criterios dados!")

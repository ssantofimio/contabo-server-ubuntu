# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class PurchaseBlancosWizard(models.TransientModel):
    _name = 'purchase.blancos.wizard'
    _description = 'Wizard para Informe de Blancos'

    def _default_start_date(self):
        return date.today().replace(day=1)

    def _default_end_date(self):
        return date.today() + relativedelta(months=1, day=1, days=-1)

    date_start = fields.Date(string='Fecha Inicio', required=True, default=_default_start_date)
    date_end = fields.Date(string='Fecha Fin', required=True, default=_default_end_date)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Proveedor')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Almacenes', domain="[('company_id', '=', company_id)]")


    def _get_blancos_records(self):
        import pytz
        # 1. Construir dominio base
        domain = [
            ('state', '=', 'purchase'),
            ('receipt_status', '=', 'full'),
            ('invoice_status', '=', 'to invoice'),
            ('company_id', 'in', self.env.companies.ids),
            # 'invoice_state_summary' computed is filtered in python
        ]
        
        # 2. Add wizard filters
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        
        if self.date_start:
            # Convert start date 00:00:00 Local -> UTC
            start_local = user_tz.localize(datetime.combine(self.date_start, time.min))
            start_utc = start_local.astimezone(pytz.UTC).replace(tzinfo=None) # remove tzinfo for Odoo search
            domain.append(('date_order', '>=', start_utc))
            
        if self.date_end:
            # Convert end date 23:59:59 Local -> UTC
            end_local = user_tz.localize(datetime.combine(self.date_end, time.max))
            end_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)
            domain.append(('date_order', '<=', end_utc))
            
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        if self.warehouse_ids:
            picking_types = self.env['stock.picking.type'].search([('warehouse_id', 'in', self.warehouse_ids.ids)])
            domain.append(('picking_type_id', 'in', picking_types.ids))

        # 3. Search
        _logger.info("BLANCOS WIZARD - Start Search")
        _logger.info(f"fechas input: {self.date_start} - {self.date_end}")
        _logger.info(f"Domain: {domain}")
        
        records = self.env['purchase.order'].search(domain)
        
        _logger.info(f"Records found (SQL): {len(records)}")
        
        # 4. Filter computed field
        records = records.filtered(lambda r: not r.invoice_state_summary)
        
        _logger.info(f"Records after summary filter: {len(records)}")
        return records

    def action_print_report(self):
        self.ensure_one()
        records = self._get_blancos_records()
        records = records.exists()
        
        if not records:
            raise UserError('No se encontraron registros para los criterios seleccionados.')

        
        data = {
            'columns': {
                'warehouse': True, 'number': True, 'date': True, 'partner': True, 
                'partner_ref': True, # Nuevo campo
                'buyer': True, 'state': False, 'subtotal': False, 'tax': False, 
                'total': True, 'planned_date': False, 'receipt_status': True, 
                'invoice_status': True, 'invoice_state': False
            },
            'order_ids': records.ids,
            'report_title': 'INFORME DE BLANCOS'
        }
        
        return self.env.ref('custom_reports.action_report_purchase_order').report_action(records, data=data)

    def action_print_excel(self):
        self.ensure_one()
        records = self._get_blancos_records()
        records = records.exists()

        if not records:
            raise UserError('No se encontraron registros para los criterios seleccionados.')


        # Create workbook
        import xlsxwriter
        import io
        import base64
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Informe de Blancos')
        
        # Formats
        header_format = workbook.add_format({'bold': True, 'bg_color': '#f0f0f0', 'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})
        money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        
        # Headers
        headers = [
            'Almacén', 'Número', 'Fecha', 'Proveedor', 'Ref. Prov.', 'Comprador', 
            'Total', 'Estado Entrega', 'Estado Facturación'
        ]
        
        # Track max widths for auto-fit
        col_widths = [len(h) for h in headers]
        
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)
            
        # Data
        row = 1
        for record in records:
            # Prepare row data list for easy iteration
            row_data = [
                record.warehouse_name or '',
                record.name or '',
                str(record.date_order_local or ''),  # Convert date to string for len
                '', # Partner placeholder
                record.partner_ref or '',
                record.user_id.name or '',
                f"{record.amount_total:,.2f}", # Format money string for len
                record.receipt_status_display_es or '',
                record.invoice_status_display_es or ''
            ]
            
            # Formato Proveedor: NOMBRE - NIT (Logic reused)
            partner_name = record.partner_id.name or ''
            if record.partner_id.vat:
                partner_name = f"{partner_name} ‒ {record.partner_id.vat}"
            row_data[3] = partner_name

            # Write data and update widths
            worksheet.write(row, 0, row_data[0], text_format)
            worksheet.write(row, 1, row_data[1], text_format)
            worksheet.write(row, 2, record.date_order_local or '', date_format) # Write actual Date obj
            worksheet.write(row, 3, row_data[3], text_format)
            worksheet.write(row, 4, row_data[4], text_format)
            worksheet.write(row, 5, row_data[5], text_format)
            worksheet.write(row, 6, record.amount_total, money_format) # Write actual Float
            worksheet.write(row, 7, row_data[7], text_format)
            worksheet.write(row, 8, row_data[8], text_format)
            
            # Check widths (heuristic: len * 1.2 for proportional font safety)
            for i, val in enumerate(row_data):
                length = len(val)
                if length > col_widths[i]:
                    col_widths[i] = length
            
            row += 1
            
        # Set Columns Widths
        for i, width in enumerate(col_widths):
            # Add some padding + limit max width to avoid huge columns
            final_width = min(max(width + 2, 10), 60) 
            worksheet.set_column(i, i, final_width)
            
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()
        
        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'Informe_de_Blancos.xlsx',
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


from odoo import http
from odoo.http import request

class PnLController(http.Controller):

    @http.route('/custom_pnl_report/get_data', type='json', auth='user')
    def get_pnl_data(self, date_from, date_to, target_move='posted', comparison='none', journal_ids=None, analytic_account_ids=None):
        company = request.env.company
        report_model = request.env['report.custom_pnl_report.report_pnl_template']
        
        data = {
            'form': {
                'date_from': date_from,
                'date_to': date_to,
                'target_move': target_move,
                'company_id': company.id,
                'comparison': comparison,
                'journal_ids': journal_ids or [],
                'analytic_account_ids': analytic_account_ids or [],
            }
        }
        
        values = report_model._get_report_values(docids=None, data=data)
        
        # Prepare journals and analytics for filters
        journals = request.env['account.journal'].search_read(
            [('company_id', '=', company.id)], 
            ['id', 'name', 'code', 'type']
        )
        analytics = request.env['account.analytic.account'].search_read(
            [('company_id', '=', company.id)], 
            ['id', 'name']
        )
        
        return {
            'categories': values['categories'],
            'grand_totals': values['grand_totals'],
            'date_from': values['date_from'],
            'date_to': values['date_to'],
            'company_name': values['company'].name,
            'currency_symbol': values['company'].currency_id.symbol,
            'journals': journals,
            'analytics': analytics,
            'comparison': values['comparison'],
        }

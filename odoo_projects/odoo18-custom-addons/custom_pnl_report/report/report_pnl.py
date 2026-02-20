from odoo import api, models, _, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class ReportPnL(models.AbstractModel):
    _name = 'report.custom_pnl_report.report_pnl_template'
    _description = 'Report Engine for Estado de Resultados'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        date_from = data['form'].get('date_from')
        date_to = data['form'].get('date_to')
        
        # Validation to prevent SQL error with empty dates
        if not date_from or not date_to:
            today = fields.Date.today()
            date_from = date_from or today.replace(month=1, day=1).strftime('%Y-%m-%d')
            date_to = date_to or today.replace(month=12, day=31).strftime('%Y-%m-%d')
        target_move = data['form'].get('target_move', 'posted')
        company_id = data['form'].get('company_id') or self.env.company.id
        journal_ids = data['form'].get('journal_ids', [])
        analytic_account_ids = data['form'].get('analytic_account_ids', [])
        comparison = data['form'].get('comparison', 'none') # none, previous_period, previous_year

        company = self.env['res.company'].browse(company_id)
        # Domain for account moves
        move_domain = [
            ('company_id', '=', company_id),
        ]
        if target_move == 'posted':
            move_domain.append(('parent_state', '=', 'posted'))

        # Fetch accounts
        accounts = self.env['account.account'].search([
            ('company_ids', 'in', [company_id]),
            '|', '|', '|', 
            ('code', '=like', '4%'), 
            ('code', '=like', '5%'), 
            ('code', '=like', '6%'), 
            ('code', '=like', '7%')
        ])

        report_data = []
        
        # Helper to group and sum
        def get_balances(account, start, end, j_ids=None, a_ids=None):
            domain = move_domain + [('account_id', '=', account.id)]
            if j_ids:
                domain.append(('journal_id', 'in', j_ids))
            if a_ids:
                domain.append(('analytic_account_id', 'in', a_ids))
            
            # Initial balance: all moves before start date
            init_domain = domain + [('date', '<', start)]
            # Period movements: moves between start and end date
            period_domain = domain + [('date', '>=', start), ('date', '<=', end)]
            
            # Optimization: use read_group or search_read? 
            # For simplicity in this P&L, we sum values
            init_moves = self.env['account.move.line'].search(init_domain)
            period_moves = self.env['account.move.line'].search(period_domain)
            
            initial_balance = sum(init_moves.mapped('balance'))
            debit = sum(period_moves.mapped('debit'))
            credit = sum(period_moves.mapped('credit'))
            
            return initial_balance, debit, credit

        # Categories mapping
        categories = [
            {'name': 'Ingresos', 'prefix': '4', 'lines': []},
            {'name': 'Gastos', 'prefix': '5', 'lines': []},
            {'name': 'Costos de ventas', 'prefix': '6', 'lines': []},
            {'name': 'Costos de producción o de operación', 'prefix': '7', 'lines': []},
        ]

        grand_totals = {'initial': 0.0, 'debit': 0.0, 'credit': 0.0, 'final': 0.0}
        grand_totals = {'initial': 0.0, 'debit': 0.0, 'credit': 0.0, 'final': 0.0, 'comp_final': 0.0}

        for cat in categories:
            cat_accounts = accounts.filtered(lambda a: a.code.startswith(cat['prefix']))
            if not cat_accounts:
                continue
            
            cat_total = {'initial': 0.0, 'debit': 0.0, 'credit': 0.0, 'final': 0.0, 'comp_final': 0.0}
            sign = -1 if cat['prefix'] == '4' else 1
            
            for acc in cat_accounts:
                init, deb, cre = get_balances(acc, date_from, date_to, journal_ids, analytic_account_ids)
                if init == 0 and deb == 0 and cre == 0:
                    continue
                
                init_natural = init * sign
                final_natural = (init + deb - cre) * sign
                
                # Comparison logic
                comp_final_natural = 0.0
                if comparison != 'none':
                    # Calculate comparison dates
                    # Previous Period: same duration ending at date_from - 1 day
                    # Previous Year: same dates but year - 1
                    # For simplicity, we implement logic here
                    d_from = datetime.strptime(date_from, "%Y-%m-%d")
                    d_to = datetime.strptime(date_to, "%Y-%m-%d")
                    d_to = datetime.strptime(date_to, "%Y-%m-%d")
                    if comparison == 'previous_period':
                        delta = d_to - d_from
                        comp_to = d_from - timedelta(days=1)
                        comp_from = comp_to - delta
                    else: # previous_year
                        comp_from = d_from.replace(year=d_from.year - 1)
                        comp_to = d_to.replace(year=d_to.year - 1)
                    
                    c_init, c_deb, c_cre = get_balances(acc, comp_from.strftime("%Y-%m-%d"), comp_to.strftime("%Y-%m-%d"), journal_ids, analytic_account_ids)
                    comp_final_natural = (c_init + c_deb - c_cre) * sign

                line = {
                    'code': acc.code,
                    'name': acc.name,
                    'initial': init_natural,
                    'debit': deb,
                    'credit': cre,
                    'final': final_natural,
                    'comp_final': comp_final_natural,
                }
                cat['lines'].append(line)
                cat_total['initial'] += init_natural
                cat_total['debit'] += deb
                cat_total['credit'] += cre
                cat_total['final'] += final_natural
                cat_total['comp_final'] += comp_final_natural

            cat['totals'] = cat_total
            op = 1 if cat['prefix'] == '4' else -1
            grand_totals['initial'] += cat_total['initial'] * op
            grand_totals['debit'] += cat_total['debit'] * op
            grand_totals['credit'] += cat_total['credit'] * op
            grand_totals['final'] += cat_total['final'] * op
            grand_totals['comp_final'] += cat_total.get('comp_final', 0.0) * op

        return {
            'doc_ids': docids,
            'doc_model': 'account.pnl.wizard',
            'company': company,
            'date_from': date_from,
            'date_to': date_to,
            'categories': categories,
            'grand_totals': grand_totals,
            'comparison': comparison,
        }

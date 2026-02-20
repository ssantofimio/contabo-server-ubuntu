from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    it_assignment_count = fields.Integer(
        string='IT Assignments',
        compute='_compute_it_assignment_count'
    )

    def _compute_it_assignment_count(self):
        """Compute the number of active IT assignments for this employee."""
        for employee in self:
            # Count unique products assigned to this employee
            assignment_lines = self.env['it.assignment.line'].search([
                ('assignment_id.employee_id', '=', employee.id),
                ('assignment_id.state', 'in', ['confirmed', 'signed', 'returning'])
            ])
            employee.it_assignment_count = len(assignment_lines.mapped('product_id'))

    def action_view_it_assignments(self):
        """Open the list of IT products assigned to this employee."""
        self.ensure_one()
        
        # Get all products assigned to this employee
        assignment_lines = self.env['it.assignment.line'].search([
            ('assignment_id.employee_id', '=', self.id),
            ('assignment_id.state', 'in', ['confirmed', 'signed', 'returning'])
        ])
        product_ids = assignment_lines.mapped('product_id').ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Equipos TIC Asignados',
            'res_model': 'product.template',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', product_ids)],
            'context': {
                'search_default_filter_available_in_it_inventory': 1,
            },
        }

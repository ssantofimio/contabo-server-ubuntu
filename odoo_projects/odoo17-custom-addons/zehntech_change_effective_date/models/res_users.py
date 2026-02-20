from odoo import models ,fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    change_effective_date = fields.Boolean(
        string='Change Effective Date Privilege',
        help='Enable this option to allow the user to change the effective date on stock transfers and update valuation accordingly.'
    )
    is_admin_settings = fields.Boolean(
        string='Is Admin Settings Group',
        compute='_compute_is_admin_settings',
        store=False
    )

    @api.depends('groups_id')
    def _compute_is_admin_settings(self):
        admin_group = self.env.ref('base.group_system')
        for user in self:
            user.is_admin_settings = admin_group in user.groups_id
            
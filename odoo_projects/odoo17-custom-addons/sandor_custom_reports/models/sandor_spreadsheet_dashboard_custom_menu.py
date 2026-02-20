import json
from odoo import api, fields, models, _

class SandorCustomMenu(models.Model):
    _name = 'sandor.spreadsheet.dashboard.custom.menu'
    _description = 'Custom Dashboard Menu'
    _order = 'sequence'

    name = fields.Char(string="Menu Name", required=True)
    parent_menu_id = fields.Many2one('ir.ui.menu', string="Parent Menu (Module/Section)", required=True)
    sequence = fields.Integer(string="Sequence", default=0, help="Position in the menu. 0 for top.")
    line_ids = fields.One2many('sandor.spreadsheet.dashboard.custom.menu.line', 'menu_config_id', string="Dashboards/Sheets")
    menu_id = fields.Many2one('ir.ui.menu', string="Generated Menu", ondelete='set null', readonly=True)
    action_id = fields.Many2one('ir.actions.client', string="Generated Action", ondelete='set null', readonly=True)

    def action_create_menu(self):
        self.ensure_one()
        if not self.parent_menu_id:
            return
        
        # 1. Create client action
        action_vals = {
            'name': self.name,
            'tag': 'action_sandor_custom_reports',
            'params': {
                'config_id': self.id,
                'hide_side_panel': False, # We show side panel but filtered
            },
            'target': 'current',
        }
        if self.action_id:
            self.action_id.write(action_vals)
        else:
            self.action_id = self.env['ir.actions.client'].create(action_vals)
            
        # 2. Create menu item
        menu_vals = {
            'name': self.name,
            'parent_id': self.parent_menu_id.id,
            'action': f'ir.actions.client,{self.action_id.id}',
            'sequence': self.sequence,
        }
        if self.menu_id:
            self.menu_id.write(menu_vals)
        else:
            self.menu_id = self.env['ir.ui.menu'].create(menu_vals)
            
        return True

    def action_remove_menu(self):
        self.ensure_one()
        if self.menu_id:
            self.menu_id.unlink()
        if self.action_id:
            self.action_id.unlink()
        return True

    def get_config_data(self):
        self.ensure_one()
        
        # Return structured data for the loader
        # We simulate groups based on dashboards if they don't have natural groups or 
        # just follow the dashboard's own groups but filtered.
        # However, the user wants them listed.
        
        # Let's get the dashboards and their current groups
        dashboard_ids = self.line_ids.mapped('dashboard_id').ids
        groups = self.env['sandor.spreadsheet.dashboard.group'].search([
            ('dashboard_ids', 'in', dashboard_ids)
        ])
        
        res_groups = []
        for group in groups:
            # Only dashboards that are in our config
            allowed_dashboards = group.dashboard_ids.filtered(lambda d: d.id in dashboard_ids)
            if allowed_dashboards:
                # Map dashboard ID to its line configuration
                dashboard_lines = self.line_ids.filtered(lambda l: l.dashboard_id.id in allowed_dashboards.ids)
                line_map = {l.dashboard_id.id: l for l in dashboard_lines}
                
                res_groups.append({
                    'id': group.id,
                    'name': group.name,
                    'dashboards': [{
                        'id': d.id,
                        'name': line_map[d.id].display_name or d.name,
                    } for d in allowed_dashboards]
                })
        
        return {
            'groups': res_groups,
        }

class SandorCustomMenuLine(models.Model):
    _name = 'sandor.spreadsheet.dashboard.custom.menu.line'
    _description = 'Custom Dashboard Menu Line'

    menu_config_id = fields.Many2one('sandor.spreadsheet.dashboard.custom.menu', ondelete='cascade')
    dashboard_id = fields.Many2one('sandor.spreadsheet.dashboard', string="Dashboard", required=True)
    display_name = fields.Char(string="Display Name", help="Name to show in the sidebar for this dashboard")

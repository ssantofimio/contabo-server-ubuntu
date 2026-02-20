import json
import base64
from odoo import api, fields, models, _
from odoo.exceptions import AccessError

class SandorSpreadsheetDashboard(models.Model):
    _name = 'sandor.spreadsheet.dashboard'
    _description = 'Sandor Spreadsheet Dashboard'
    _inherit = "spreadsheet.mixin"
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    dashboard_group_id = fields.Many2one('sandor.spreadsheet.dashboard.group', required=True)
    sequence = fields.Integer()
    group_ids = fields.Many2many('res.groups', default=lambda self: self.env.ref('base.group_user'))
    active = fields.Boolean(default=True)
    is_published = fields.Boolean(string="Is Published", default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    spreadsheet_raw = fields.Serialized(
        inverse="_inverse_spreadsheet_raw", compute="_compute_spreadsheet_raw"
    )
    has_spreadsheet_oca = fields.Boolean(compute="_compute_has_spreadsheet_oca")
    
    # Menu integration fields
    parent_menu_id = fields.Many2one('ir.ui.menu', string="Parent Menu (Module or Section)")
    menu_name = fields.Char(string="Menu Name", help="Name that will appear in the target module menu")
    menu_sequence = fields.Integer(string="Sequence", default=0, help="Order in the menu. Use a low number (e.g. 0) to put it at the top.")
    menu_target_sheet = fields.Char(string="Target Sheet Name", help="Enter the exact name of the sheet you want to show (e.g. 'Sales'). Keep empty to show all.")
    menu_id = fields.Many2one('ir.ui.menu', string="Generated Menu", ondelete='set null')
    action_id = fields.Many2one('ir.actions.client', string="Generated Action", ondelete='set null')
    
    custom_menu_line_ids = fields.One2many('sandor.spreadsheet.dashboard.custom.menu.line', 'dashboard_id', string="Appears in External Menus")

    def _compute_has_spreadsheet_oca(self):
        oca_module = self.env['ir.module.module'].sudo().search([
            ('name', '=', 'spreadsheet_oca'),
            ('state', '=', 'installed')
        ], limit=1)
        for dashboard in self:
            dashboard.has_spreadsheet_oca = bool(oca_module)

    def action_create_menu(self):
        self.ensure_one()
        if not self.parent_menu_id:
            return
        
        name = self.menu_name or self.name
        
        # 1. Create client action
        action_vals = {
            'name': name,
            'tag': 'action_sandor_custom_reports',
            'params': {
                'dashboard_id': self.id,
                'target_sheet_name': self.menu_target_sheet,
                'hide_side_panel': bool(self.menu_target_sheet),
            },
            'target': 'current',
        }
        if self.action_id:
            self.action_id.write(action_vals)
        else:
            self.action_id = self.env['ir.actions.client'].create(action_vals)
            
        # 2. Create menu item
        menu_vals = {
            'name': name,
            'parent_id': self.parent_menu_id.id,
            'action': f'ir.actions.client,{self.action_id.id}',
            'sequence': self.menu_sequence,
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
    @api.depends("spreadsheet_binary_data")
    def _compute_spreadsheet_raw(self):
        for dashboard in self:
            if dashboard.spreadsheet_binary_data:
                try:
                    dashboard.spreadsheet_raw = json.loads(
                        base64.b64decode(dashboard.spreadsheet_binary_data).decode(
                            "UTF-8"
                        )
                    )
                except Exception:
                    dashboard.spreadsheet_raw = {}
            else:
                dashboard.spreadsheet_raw = {}

    def _inverse_spreadsheet_raw(self):
        for record in self:
            if record.spreadsheet_raw:
                record.spreadsheet_binary_data = base64.b64encode(
                    json.dumps(record.spreadsheet_raw).encode("UTF-8")
                )
            else:
                record.spreadsheet_binary_data = False

    def action_open_spreadsheet(self):
        self.ensure_one()
        # Direct check in database to see if OCA is installed and active
        oca_module = self.env['ir.module.module'].sudo().search([
            ('name', '=', 'spreadsheet_oca'),
            ('state', '=', 'installed')
        ], limit=1)
        
        if oca_module:
            return {
                "type": "ir.actions.client",
                "tag": "action_spreadsheet_oca",
                "params": {"spreadsheet_id": self.id, "model": self._name},
            }
        return self.get_readonly_dashboard_action()

    def get_readonly_dashboard_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "action_sandor_custom_reports",
            "params": {"dashboard_id": self.id},
        }

    def get_spreadsheet_data(self):
        self.ensure_one()
        mode = "normal"
        try:
            self.check_access_rights("write")
            self.check_access_rule("write")
        except AccessError:
            mode = "readonly"
        
        res = {
            "name": self.name,
            "spreadsheet_raw": self.spreadsheet_raw,
            "revisions": [],
            "mode": mode,
            "default_currency": self.env[
                "res.currency"
            ].get_company_currency_for_spreadsheet(),
            "user_locale": self.env["res.lang"]._get_user_spreadsheet_locale(),
        }

        # Check for OCA revisions dynamically
        RevisionModel = self.env.get("spreadsheet.oca.revision")
        if RevisionModel:
            revisions = RevisionModel.search([
                ("model", "=", self._name),
                ("res_id", "=", self.id)
            ])
            res["revisions"] = [
                dict(
                    json.loads(revision.commands),
                    nextRevisionId=revision.next_revision_id,
                    serverRevisionId=revision.server_revision_id,
                )
                for revision in revisions
            ]
        return res

    def send_spreadsheet_message(self, message):
        self.ensure_one()
        # Only proceed if OCA is installed
        RevisionModel = self.env.get("spreadsheet.oca.revision")
        if not RevisionModel:
            return False

        channel = (self.env.cr.dbname, "spreadsheet_oca", self._name, self.id)
        message.update({"res_model": self._name, "res_id": self.id})
        if message["type"] in ["REVISION_UNDONE", "REMOTE_REVISION", "REVISION_REDONE"]:
            RevisionModel.create(
                {
                    "model": self._name,
                    "res_id": self.id,
                    "type": message["type"],
                    "client_id": message.get("clientId"),
                    "next_revision_id": message["nextRevisionId"],
                    "server_revision_id": message["serverRevisionId"],
                    "commands": json.dumps(
                        self._build_spreadsheet_revision_commands_data(message)
                    ),
                }
            )
        self.env["bus.bus"]._sendone(channel, "spreadsheet_oca", message)
        return True

    @api.model
    def _build_spreadsheet_revision_commands_data(self, message):
        """Prepare spreadsheet revision commands data from the message"""
        commands = dict(message)
        commands.pop("serverRevisionId", None)
        commands.pop("nextRevisionId", None)
        commands.pop("clientId", None)
        return commands

    def write(self, vals):
        if "spreadsheet_raw" in vals:
            RevisionModel = self.env.get("spreadsheet.oca.revision")
            if RevisionModel:
                revisions = RevisionModel.search([
                    ("model", "=", self._name),
                    ("res_id", "=", self.id)
                ])
                revisions.unlink()
        return super().write(vals)

    def get_readonly_dashboard(self):

        self.ensure_one()
        snapshot = json.loads(self.spreadsheet_data)
        user_locale = self.env['res.lang']._get_user_spreadsheet_locale()
        snapshot.setdefault('settings', {})['locale'] = user_locale
        default_currency = self.env['res.currency'].get_company_currency_for_spreadsheet()
        return {
            'snapshot': snapshot,
            'revisions': [],
            'default_currency': default_currency,
        }

    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if 'name' not in default:
            default['name'] = _("%s (copy)") % self.name
        return super().copy(default=default)

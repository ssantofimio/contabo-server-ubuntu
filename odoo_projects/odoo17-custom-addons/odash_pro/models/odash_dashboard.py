import urllib.parse
import string
import random
import uuid
import requests
from datetime import datetime
 
from odoo import models, fields, api
 
REAL_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMTE3IiwicGxhbiI6InBybyIsImlhdCI6MTc2NzEzMTgwOC43NzE3MDgsImV4cCI6MTc2Nzk5NTgwOC43NzE3MDgsImp0aSI6IjAxMTQ4NTE1LTNiMDMtNGJjZC05YjZjLTdjZjAxZjI4Y2MwYiJ9.EcrvbUVpF98i0XpCTN_JGclzHAOes6bMonqFJq58ivriznTltle0bS6MyBz_7Uw1i4Jy7d4_XbIl26wAWGfGRJamcZ04jNzlO8CCIi0cUwu5SJTyF4eu4aAV3_lmp_e4r4ImYG2yCDRNetA08ltoBpbndVYr84pAnj-TQd3bEKtWO43n0Rti7aRppQBTI6SmBM1HTJ_jecKx70kdBVgyNQErf0S_TXmuOqfZ89gUz-u3sKMfWA-5wIJ7rFmM9wRQalvkS5qkULPc9yAX_jKvXDZ639z-KWWeEFoXFNskjSsjAUGuSMzefJy9A0cTpdCRws9m9c5yjACiZlcm0UNuvg"

def generate_random_string(n):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(n))
    return random_string
 
 
def generate_connection_url(connection_url, is_public, token, api_url, user, companies_ids):
    if user:
        user_id = user.id
        partner_id = user.partner_id.id
        editor_viewer = "editor" if user.has_group('odash_pro.group_odash_pro_editor') else "viewer"
        partner_lang = user.lang.split('_')[0]
    else:
        user_id = 0
        partner_id = 0
        editor_viewer = "viewer"
        partner_lang = "en"
    
    if "odash_pro.app" in connection_url:
        connection_url = connection_url.replace("odash_pro.app", "odashboard.app")
        
    base_url = connection_url
    if is_public:
        base_url += "/public"
        
    # LOCAL ENGINE ADAPTATION:
    # Use the new controller route and place #/ at the end so:
    # 1. location.search contains the token
    # 2. HashRouter matches the / route
    if "local_engine" in base_url:
        return f"{base_url}?token={token}|{urllib.parse.quote(f'{api_url}/api', safe='')}|{uuid.uuid4()}|{user_id}|{partner_id}|{editor_viewer}|{','.join(str(id) for id in companies_ids)}&lang={partner_lang}#/"
    else:
        # Original Remote Engine
        return f"{base_url}?token={token}|{urllib.parse.quote(f'{api_url}/api', safe='')}|{uuid.uuid4()}|{user_id}|{partner_id}|{editor_viewer}|{','.join(str(id) for id in companies_ids)}&lang={partner_lang}"
 
 
class Dashboard(models.Model):
    _name = "odash_pro.dashboard"
    _description = "Dashboard accesses"
 
    name = fields.Char(default='Odashboard')
 
    user_id = fields.Many2one("res.users", string="User", index=True)
    allowed_company_ids = fields.Many2many("res.company", string="Companies")
    page_id = fields.Many2one("odash_pro.config", string="Page")
 
    connection_url = fields.Char(string="URL")
    token = fields.Text(string="Token", groups='base.group_no_one')
    config = fields.Json(string="Config")
 
    last_authentication_date = fields.Datetime(string="Last Authentication Date")
 
    @api.model
    def update_auth_token(self):
        """Standalone Bypass: Maintaining real token and local connection"""
        config_params = self.env['ir.config_parameter'].sudo()
        config_params.set_param('odash_pro.api.token', REAL_TOKEN)
        config_params.set_param('odash_pro.plan', 'pro')
        
        # Point to the local engine for total independence
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        if base_url.startswith('http://'):
             base_url = base_url.replace('http://', 'https://')
             config_params.set_param('web.base.url', base_url)

        local_url = f"{base_url}/odash_pro/local_engine"
        config_params.set_param('odash_pro.connection.url', local_url)
        config_params.set_param('odash_pro.api.endpoint', 'https://odashboard.app')
        return True
 
    def _get_public_dashboard(self, page_id=False):
        user_id = self.env.ref('base.public_user').id
        dashboard_id = self.search([('user_id', '=', user_id), ('page_id', '=', page_id)], limit=1)
 
        if not dashboard_id:
            dashboard_id = self.create({
                'user_id': user_id,
                'page_id': page_id,
            })
 
        config_model = self.env['ir.config_parameter'].sudo()
        base_url = config_model.get_param('web.base.url')
        connection_url = config_model.get_param('odash_pro.connection.url', config_model.get_param('odash_pro.connection.url'))
        
        new_token = REAL_TOKEN
        companies_ids = self.env['res.company'].search([])
 
        new_connection_url = generate_connection_url(connection_url, True, new_token, base_url, None, companies_ids.ids)
 
        dashboard_id.sudo().write({
            "token": new_token,
            "connection_url": new_connection_url,
            "last_authentication_date": datetime.now(),
            "allowed_company_ids": [(6, 0, companies_ids.ids)]
        })
        return new_connection_url
 
    def get_dashboard_for_user(self):
        user_id = self.env.user.id
        dashboard_id = self.search([('user_id', '=', user_id)], limit=1)
 
        if not dashboard_id:
            dashboard_id = self.create({
                'user_id': user_id
            })
 
        dashboard_id._refresh()
 
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dashboard Pro',
            'res_model': 'odash_pro.dashboard',
            'view_mode': 'form',
            'res_id': dashboard_id.id,
            'view_id': self.env.ref('odash_pro.view_dashboard_custom_iframe').id,
            'target': 'current',
        }
 
    def _ask_refresh(self, companies_ids):
        config_model = self.env['ir.config_parameter'].sudo()
        base_url = config_model.get_param('web.base.url')
        connection_url = config_model.get_param('odash_pro.connection.url', config_model.get_param('odash_pro.connection.url'))
        
        new_token = REAL_TOKEN
        new_connection_url = generate_connection_url(connection_url, False, new_token, base_url, self.user_id, companies_ids)
        self.sudo().write({
            "token": new_token,
            "connection_url": new_connection_url,
            "last_authentication_date": datetime.now(),
            "allowed_company_ids": [(6, 0, companies_ids)]
        })
 
    def _refresh(self):
        config_model = self.env['ir.config_parameter'].sudo()
        base_url = config_model.get_param('web.base.url')
        connection_url = config_model.get_param('odash_pro.connection.url', config_model.get_param('odash_pro.connection.url'))
        
        new_token = REAL_TOKEN
        new_connection_url = generate_connection_url(connection_url, False, new_token, base_url, self.user_id, self.env.companies.ids)
        self.sudo().write({
            "token": new_token,
            "connection_url": new_connection_url,
            "last_authentication_date": datetime.now(),
            "allowed_company_ids": self.env.companies.ids
        })

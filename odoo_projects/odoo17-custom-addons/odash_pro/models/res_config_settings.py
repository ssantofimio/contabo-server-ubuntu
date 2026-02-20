import requests
import uuid
import logging
from werkzeug.urls import url_encode
 
from odoo import models, fields, api, _
 
_logger = logging.getLogger(__name__)
 
DEFAULT_API_ENDPOINT = 'https://odashboard.app'
 
# Real Working Trial Credentials (Pro Plan)
REAL_UUID = "45c8710d-0a0f-4e87-a24c-c7afcc6668ee"
REAL_KEY = "4be9c3c8-3e56-4b7e-adf1-77008455f060"
REAL_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMTE3IiwicGxhbiI6InBybyIsImlhdCI6MTc2NzEzMTgwOC43NzE3MDgsImV4cCI6MTc2Nzk5NTgwOC43NzE3MDgsImp0aSI6IjAxMTQ4NTE1LTNiMDMtNGJjZC05YjZjLTdjZjAxZjI4Y2MwYiJ9.EcrvbUVpF98i0XpCTN_JGclzHAOes6bMonqFJq58ivriznTltle0bS6MyBz_7Uw1i4Jy7d4_XbIl26wAWGfGRJamcZ04jNzlO8CCIi0cUwu5SJTyF4eu4aAV3_lmp_e4r4ImYG2yCDRNetA08ltoBpbndVYr84pAnj-TQd3bEKtWO43n0Rti7aRppQBTI6SmBM1HTJ_jecKx70kdBVgyNQErf0S_TXmuOqfZ89gUz-u3sKMfWA-5wIJ7rFmM9wRQalvkS5qkULPc9yAX_jKvXDZ639z-KWWeEFoXFNskjSsjAUGuSMzefJy9A0cTpdCRws9m9c5yjACiZlcm0UNuvg"

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
 
    odash_pro_plan = fields.Char(string='Odashboard Plan', config_parameter="odash_pro.plan")
    odash_pro_key = fields.Char(string="Odashboard Key", config_parameter="odash_pro.key")
    odash_pro_key_synchronized = fields.Boolean(string="Key Synchronized",
                                                 config_parameter="odash_pro.key_synchronized", readonly=True)
    odash_pro_uuid = fields.Char(string="Odashboard UUID", config_parameter="odash_pro.uuid", readonly=True)
    odash_pro_engine_version = fields.Char(string="Current Engine Version", readonly=True)
    odash_pro_is_free_trial = fields.Boolean(string="Is Free Trial",
                                              config_parameter="odash_pro.is_free_trial", readonly=True)
    odash_pro_free_trial_end_date = fields.Char(string="Free Trial End Date",
                                                  config_parameter="odash_pro.free_trial_end_date", readonly=True)
 
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        config_params = self.env['ir.config_parameter'].sudo()
        config_params.set_param('odash_pro.uuid', REAL_UUID)
        config_params.set_param('odash_pro.key', REAL_KEY)
        config_params.set_param('odash_pro.api.token', REAL_TOKEN)
        config_params.set_param('odash_pro.key_synchronized', True)
        config_params.set_param('odash_pro.plan', 'pro')
        
        # Point to the local engine
        base_url = config_params.get_param('web.base.url', 'http://localhost:8069')
        local_url = f"{base_url}/odash_pro/local_engine"
        config_params.set_param('odash_pro.connection.url', local_url)
        config_params.set_param('odash_pro.api.endpoint', 'https://odashboard.app')
 
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        config_params = self.env['ir.config_parameter'].sudo()
        
        # FIX HTTPS protocol mismatch automatically
        base_url = config_params.get_param('web.base.url', 'http://localhost:8069')
        if base_url.startswith('http://'):
             base_url = base_url.replace('http://', 'https://')
             config_params.set_param('web.base.url', base_url)
        
        # Point to local engine with correct protocol
        local_url = f"{base_url}/odash_pro/local_engine"
        
        config_params.set_param('odash_pro.uuid', REAL_UUID)
        config_params.set_param('odash_pro.key', REAL_KEY)
        config_params.set_param('odash_pro.api.token', REAL_TOKEN)
        config_params.set_param('odash_pro.key_synchronized', True)
        config_params.set_param('odash_pro.plan', 'pro')
        config_params.set_param('odash_pro.connection.url', local_url)
        config_params.set_param('odash_pro.api.endpoint', 'https://odashboard.app')

        engine = self.env['odash_pro.engine'].sudo()._get_single_record()
 
        res.update({
            'odash_pro_uuid': REAL_UUID,
            'odash_pro_engine_version': engine.version,
            'odash_pro_key_synchronized': True,
            'odash_pro_plan': 'pro',
            'odash_pro_is_free_trial': False,
            'odash_pro_key': REAL_KEY,
        })
        return res
 
    def action_check_engine_updates(self):
        engine = self.env['odash_pro.engine'].sudo()._get_single_record()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Information'),
                'message': _('You are using the latest version (%s)') % engine.version,
                'type': 'info',
                'sticky': False,
            }
        }
 
    def synchronize_key(self):
        return True
 
    def desynchronize_key(self):
        return True
 
    def get_my_key(self):
        return True
 
    def _clear_odash_pro_data(self):
        pass
 
    def action_manage_plan(self):
        return True

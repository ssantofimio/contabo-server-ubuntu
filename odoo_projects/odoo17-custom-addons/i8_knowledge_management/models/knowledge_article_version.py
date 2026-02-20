from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class KnowledgeArticleVersion(models.Model):
    _name = 'knowledge.article.version'
    _description = 'Knowledge Article Version'
    _order = 'create_date desc'

    article_id = fields.Many2one('knowledge.article', string='Article', required=True, ondelete="cascade")
    version_number = fields.Integer(string="Version", required=True)
    name = fields.Char(string="Title")
    content = fields.Html(string="Content Snapshot")
    
    # Metadata for the snapshot
    icon = fields.Char(string="Icon")
    cover_image_type = fields.Selection([
        ('none', 'None'),
        ('url', 'URL'),
        ('binary', 'Uploaded Image')
    ], string="Cover Type", default='none')
    cover_image_url = fields.Char(string="Cover URL")
    cover_image_binary = fields.Binary(string="Cover Image")
    cover_position = fields.Integer(string="Cover Position", default=50)

    create_date = fields.Datetime(string='Saved On', readonly=True)
    user_id = fields.Many2one('res.users', string="Saved By", default=lambda self: self.env.user, readonly=True)
    display_name = fields.Char(string="Name", compute="_compute_display_name", store=False)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.article_id.name} v{rec.version_number}"

    def action_compare_with_current(self):
        self.ensure_one()
        article = self.article_id

        current_version = self.env['knowledge.article.version'].search([
            ('article_id', '=', article.id),
        ], order='version_number desc', limit=1)

        if not current_version:
            raise UserError("Current version record not found.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Compare Versions',
            'res_model': 'knowledge.version.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_old_version_id': self.id,
                'default_current_version_id': current_version.id,
            }
        }

    @api.model
    def action_compare_selected_versions(self, records):
        if len(records) != 2:
            raise UserError("Please select exactly 2 versions to compare.")

        versions = sorted(records, key=lambda v: v.version_number)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'knowledge.version.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_article_id': versions[0].article_id.id,
                'default_old_version_id': versions[0].id,
                'default_current_version_id': versions[1].id,
            }
        }

class KnowledgeVersionCompareWizard(models.TransientModel):
    _name = 'knowledge.version.compare.wizard'
    _description = 'Compare Article Versions'

    article_id = fields.Many2one('knowledge.article', string='Current Article', required=True)
    old_version_id = fields.Many2one('knowledge.article.version', string='Old Version', required=True)
    current_version_id = fields.Many2one('knowledge.article.version', string="Current Version", required=False)
    current_content = fields.Html(string="Current Content", readonly=True)
    old_content = fields.Html(string="Previous Content", readonly=True)
    diff_html = fields.Html(string="Difference")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            old = self.env['knowledge.article.version'].browse(vals.get('old_version_id'))
            current_id = vals.get('current_version_id')
            article = self.env['knowledge.article'].browse(vals.get('article_id'))
            
            if current_id:
                current = self.env['knowledge.article.version'].browse(current_id)
                new_content = current.content or ''
                new_version_num = current.version_number
            else:
                new_content = article.content or ''
                new_version_num = _("Actual")

            vals.update({
                'old_content': old.content or '',
                'current_content': new_content,
                'diff_html': self._generate_diff_html(
                    old.content or '',
                    new_content,
                    old.version_number,
                    new_version_num
                ),
            })
        return super().create(vals_list)

    def _generate_diff_html(self, old, new, old_num=None, new_num=None):
        try:
            from lxml.html import diff
            from lxml.html import fromstring, tostring

            # lxml.html.diff.htmldiff expect strings
            diff_html = diff.htmldiff(old or '', new or '')
            
            return f'<div class="o_diff_visual_content pt-3">{diff_html}</div>'
        except Exception as e:
            # Fallback a difflib si lxml falla
            import difflib
            return f"<p class='alert alert-warning'><strong>No se pudo generar la comparación visual:</strong> {str(e)}</p>"

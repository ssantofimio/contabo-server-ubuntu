from odoo import http
from odoo.http import request

class KnowledgeController(http.Controller):

    @http.route('/knowledge/article/<int:article_id>/messages', type='json', auth='user')
    def get_article_messages(self, article_id):
        article = request.env['knowledge.article'].browse(article_id).exists()
        if not article:
            return []

        messages = article.message_ids.filtered(lambda m: m.message_type == 'comment').sorted('date')
        return [{
            'id': msg.id,
            'parent_id': msg.parent_id.id if msg.parent_id and msg.parent_id.id in messages.ids else None,
            'author': msg.author_id.name,
            'body': msg.body,
            'date': msg.date.strftime('%Y-%m-%d %H:%M:%S'),
        } for msg in messages]

    @http.route(['/knowledge/article/<string:token>'], type='http', auth='public', website=True)
    def article_public_view(self, token, **kwargs):
        article = request.env['knowledge.article'].sudo().search([('share_token', '=', token)], limit=1)
        if not article or not article.is_published:
            return request.not_found()

        # Find Public Root (Top-most published ancestor)
        current = article
        while current.parent_id and current.parent_id.is_published:
            current = current.parent_id
        public_root = current

        return request.render('i8_knowledge_management.article_public_template', {
            'article': article,
            'public_root': public_root,
        })

    @http.route('/knowledge/article/increment_view', type='json', auth='public')
    def increment_view(self, article_id):
        article = request.env['knowledge.article'].sudo().browse(article_id)
        if article.exists() and (article.is_published or request.env.user.has_group('base.group_user')):
            article.views_count += 1
            request.env['knowledge.article.view.log'].sudo().create({
                'article_id': article.id,
                'user_id': request.env.user.id if request.env.user.id else None
            })

    @http.route('/knowledge/public/search', type='json', auth='public')
    def search_public(self, token, query):
        if not query:
            return []
        
        # Identify the context article by token
        context_article = request.env['knowledge.article'].sudo().search([('share_token', '=', token)], limit=1)
        if not context_article or not context_article.is_published:
            return []

        # Find the public root (top-most published ancestor)
        current = context_article
        while current.parent_id and current.parent_id.is_published:
            current = current.parent_id
        public_root = current

        # Search within descendants of public_root (including itself)
        # Only published articles
        # Hierarchy check: all published descendants
        # Note: We use sudo() because this is a public route
        
        # Optimization: search for name or content
        domain = [
            ('is_published', '=', True),
            '|', ('name', 'ilike', query), ('content', 'ilike', query)
        ]
        
        # We need to filter further to ensure they belong to the same 'tree' or at least are reachable
        # For simplicity in this module, we usually consider that if an article is published, 
        # it's searchable IF it's part of the same public hierarchy.
        # But Odoo Knowledge public view often allows searching ALL published articles if you have a valid token.
        # Let's stick to the current hierarchy for safety.
        
        all_published = request.env['knowledge.article'].sudo().search(domain)
        
        # Filter: Is the article a descendant of public_root?
        # We can do this more efficiently with a child_of if we want, but name search is first.
        results = []
        for article in all_published:
            # Check if this article is under the public_root
            # We can use paths if we had them, otherwise check ancestors
            is_valid = False
            temp = article
            while temp:
                if temp.id == public_root.id:
                    is_valid = True
                    break
                temp = temp.parent_id
            
            if is_valid:
                results.append({
                    'id': article.id,
                    'name': article.name,
                    'icon': article.icon,
                    'share_token': article.share_token,
                    'has_children': bool(article.child_ids.filtered('is_published'))
                })
        
        return results

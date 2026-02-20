from odoo import http
from odoo.http import request
import os

class LocalEngineController(http.Controller):

    @http.route('/odash_pro/local_engine', type='http', auth='user', website=False)
    def serve_local_engine(self, **kwargs):
        """
        Serves the local engine HTML via a controller route.
        This helps React Router handle paths correctly compared to serving as a static file.
        """
        # We can either read the file and return it, or render a template
        # Reading the file for simplicity as it's already prepared
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static/src/html/local_engine.html')
        
        if not os.path.exists(file_path):
            return request.not_found()
            
        with open(file_path, 'r') as f:
            content = f.read()
            
        return request.make_response(content, [('Content-Type', 'text/html')])

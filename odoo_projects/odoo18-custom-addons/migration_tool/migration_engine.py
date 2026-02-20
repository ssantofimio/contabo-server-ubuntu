import xmlrpc.client
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OdooInstance:
    def __init__(self, config):
        self.url = config['url']
        self.db = config['db']
        self.username = config['username']
        self.password = config['api_key']
        self.uid = None
        self.context = {}
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)

    def authenticate(self):
        try:
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                logger.info(f"Authenticated with {self.url} (UID: {self.uid})")
            else:
                logger.error(f"Authentication failed for {self.url}")
            return self.uid
        except Exception as e:
            logger.error(f"Error authenticating with {self.url}: {str(e)}")
            return None

    def execute(self, model, method, *args, **kwargs):
        # Merge global context into kwargs
        if self.context:
            context = kwargs.get('context')
            if context is None:
                context = self.context.copy()
            else:
                context = context.copy()
                context.update(self.context)
            kwargs['context'] = context
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs)

    def search_read(self, model, domain=None, fields=None, offset=0, limit=None, order=None, **kwargs):
        domain = domain or []
        fields = fields or []
        return self.execute(model, 'search_read', domain, fields=fields, offset=offset, limit=limit, order=order, **kwargs)

    def create(self, model, values, **kwargs):
        return self.execute(model, 'create', values, **kwargs)

    def write(self, model, res_id, values, **kwargs):
        return self.execute(model, 'write', [res_id], values, **kwargs)

    def get_fields(self, model):
        return self.execute(model, 'fields_get', [], attributes=['string', 'help', 'type', 'required', 'relation'])

class MigrationEngine:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.source = OdooInstance(self.config['source'])
        self.destination = OdooInstance(self.config['destination'])

    def connect(self):
        return self.source.authenticate() and self.destination.authenticate()

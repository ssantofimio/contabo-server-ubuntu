{
    'name': 'Product Brand Inventory (minimal)',
    'version': '17.0.1.0.0',
    'summary': 'Minimal product.brand model + brand_id fields for products',
    'category': 'Inventory',
    'author': 'Automated install',
    'license': 'AGPL-3',
    'depends': ['product'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_brand_views.xml',
    ],
    'installable': True,
    'application': False,
}

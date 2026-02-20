{
    'name': 'Stock Picking Change Partner',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Permite cambiar el contacto (partner) de un picking y documentos asociados desde un wizard.',
    'author': 'Tu Nombre',
    'website': 'https://www.tu_sitio_web.com',
    'license': 'LGPL-3',
    'depends': ['stock', 'sale_management', 'purchase', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/change_partner_groups.xml',
        'wizards/change_partner_wizard_view.xml',
        'views/picking_button.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

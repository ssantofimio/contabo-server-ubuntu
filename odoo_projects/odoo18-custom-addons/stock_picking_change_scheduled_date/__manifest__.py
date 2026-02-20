{
    'name': 'Stock Picking Change Scheduled Date',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Module to change the state of a picking from a wizard.',
    'author': 'Tu Nombre',
    'website': 'https://www.tu_sitio_web.com',
    'license': 'LGPL-3',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'security/edit_picking_date_groups.xml',
        'wizards/picking_change_state_wizard_view.xml',
        'views/picking_button.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

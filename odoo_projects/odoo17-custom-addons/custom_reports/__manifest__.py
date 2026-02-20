# -*- coding: utf-8 -*-
{
    'name': 'Reportes',
    'version': '17.0.1.0.0',
    'category': 'Reporting',
    'summary': 'Reportes personalizados centralizados de Compras, Inventarios y otros módulos',
    'description': """
Reportes Personalizados
=======================
Este módulo centraliza reportes personalizados de diferentes módulos estándar de Odoo.

Reportes incluidos:
-------------------
* Compras por Estado: Reporte detallado de órdenes de compra con estados traducidos
* (Más reportes próximamente: Existencias, Inventarios Físicos, etc.)

Características:
---------------
* No modifica módulos estándar de Odoo
* Usa herencia de modelos para extender funcionalidad
* Interfaz en español para mejor usabilidad
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': [
        'purchase',
        'stock',
        'account',
        'sale_management',
        'purchase_stock',  # Needed for receipt_status field
    ],
    'data': [
        'views/menu_parents.xml',
        'wizard/purchase_report_wizard_views.xml',
        'wizard/purchase_blancos_wizard_views.xml',
        'views/purchase_status_views.xml',
        'views/purchase_participation_views.xml',
        'wizard/purchase_warehouse_wizard_views.xml',
        'views/purchase_warehouse_views.xml',
        'views/purchase_price_history_views.xml',
        'wizard/purchase_price_history_wizard_views.xml',
        'views/stock_available_views.xml',
        'wizard/stock_phys_count_wizard_views.xml',
        'views/stock_phys_count_report_views.xml',
        'wizard/stock_balance_wizard_views.xml',
        'views/stock_balance_views.xml',
        # Reportes Avanzados de Inventario
        'report/aging_report_views.xml',
        'report/fsn_report_views.xml',
        'report/xyz_report_views.xml',
        'report/fsn_xyz_report_views.xml',
        'report/out_of_stock_report_views.xml',
        'report/over_stock_report_views.xml',
        'report/age_breakdown_report_views.xml',
        'report/stock_movement_report_views.xml',
        'wizard/inventory_aging_report_views.xml',
        'wizard/inventory_aging_data_report_views.xml',
        'wizard/inventory_fsn_report_views.xml',
        'wizard/inventory_fsn_data_report_views.xml',
        'wizard/inventory_xyz_report_views.xml',
        'wizard/inventory_xyz_data_report_views.xml',
        'wizard/inventory_fsn_xyz_report_views.xml',
        'wizard/inventory_fsn_xyz_data_report_views.xml',
        'wizard/inventory_out_of_stock_report_views.xml',
        'wizard/inventory_out_of_stock_data_report_views.xml',
        'wizard/inventory_age_breakdown_report_views.xml',
        'wizard/inventory_over_stock_report_views.xml',
        'wizard/inventory_over_stock_data_report_views.xml',
        'wizard/inventory_stock_movement_report_views.xml',
        'wizard/stock_available_report_wizard_views.xml',
        'wizard/stock_available_data_report_views.xml',
        'report/stock_available_report_views.xml',
        'report/purchase_order_report.xml',
        'report/report_price_history.xml',
        'report/report_stock_phys_count.xml',
        'security/purchase_participation_security.xml',
        'security/stock_available_security.xml',
        'security/multi_company_security.xml',
        'security/ir.model.access.csv',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_reports/static/src/js/price_history_cog_menu.js',
            'custom_reports/static/src/xml/price_history_cog_menu.xml',
            'custom_reports/static/src/js/stock_phys_count_cog_menu.js',
            'custom_reports/static/src/xml/stock_phys_count_cog_menu.xml',
            'custom_reports/static/src/js/inventory_report_handler.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

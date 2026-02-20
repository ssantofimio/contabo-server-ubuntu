{
    'name': "Odashboard Pro Standalone",
    'version': '17.0.1.0.0',
    'category': 'Dashboard',
    'summary': 'Advanced business intelligence dashboards - Standalone Pro Version',
    'description': """
       Advanced Dashboard Solution for Odoo - Standalone Pro Version
       No license key required.
    """,
    'author': "Antigravity (Standalone)",
    'website': 'https://odashboard.app',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'data': [
        # Security
        'security/odash_security.xml',
        'security/ir.model.access.csv',
        'security/odash_dashboard_rules.xml',

        # Data
        'data/ir_config_parameter.xml',
        'data/ir_cron.xml',
        'data/ir_cron_pdf_reports.xml',
        'data/mail_template_pdf_report.xml',

        # Views
        'views/res_config_settings_views.xml',
        'views/dashboard_views.xml',
        'views/odash_security_group_views.xml',
        'views/odash_config_views.xml',
        'views/odash_category_views.xml',
        'views/dashboard_public_views.xml',
        'views/odash_dashboard_views.xml',
        'views/odash_pdf_report_views.xml',
        # Wizards
        'wizards/odash_config_import_wizard_views.xml',
        'wizards/odash_config_export_wizard_views.xml',
        # Menu
        'views/menu_items.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odash_pro/static/src/css/odash_iframe_widget.css',
            'odash_pro/static/src/js/odash_iframe_widget.js',
            'odash_pro/static/src/xml/odash_iframe_widget.xml'
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
        'static/description/youtube-link.png',
    ],
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
    'auto_install': False,
}

{
    'name': 'Estado de Resultados Personalizado (Colombia)',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Reporting',
    'summary': 'Informe de Estado de Resultados con Saldo Inicial, Débitos, Créditos y Saldo Final.',
    'description': """
        Este módulo añade un informe de Estado de Resultados personalizado para el mercado colombiano.
        Incluye agrupamiento por prefijos de cuenta (4, 5, 6, 7) y columnas de saldos detalladas.
    """,
    'author': 'Antigravity',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_pnl_wizard_view.xml',
        'report/report_pnl_templates.xml',
        'report/report_pnl_action.xml',
        'views/client_actions.xml',
        'views/menu_items.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_pnl_report/static/src/components/pnl_report/pnl_report.js',
            'custom_pnl_report/static/src/components/pnl_report/pnl_report.xml',
            'custom_pnl_report/static/src/components/pnl_report/pnl_report.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

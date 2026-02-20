{
    "name" : "Change Effective Date",
    "version":"17.0.1.0.0",
    "author" : "Zehntech Technologies Inc.",
    'summary': "Manage and adjust effective dates for sales, purchase, and inventory records. Change Effective Date Odoo module enables accurate historical data representation for currency rates, stock valuation, and financial reporting. Features configurable access control for data integrity.",
    "desription" : """Change Effective Date Odoo App enables precise adjustment of effective dates on sales, purchase, invoice, and stock documents. It ensures historical data accuracy for currency rates and stock valuation, leading to reliable financial reporting. With role-based access control, it enhances data security and auditability, proving essential for managing historical data, correcting errors, and ensuring compliance.""",
    "category" : "Accounting" ,
    "company": "Zehntech Technologies Inc.",
    "maintainer": "Zehntech Technologies Inc.",
    "contributor": "Zehntech Technologies Inc.",
    "website": "https://www.zehntech.com/",
    "support": "odoo-support@zehntech.com",
    "depends" : ["account", "stock", "sale_management","purchase"],
   
    "data" : [  
        'security/ir.model.access.csv',
         'views/stockpickingform.xml',
         'views/res_users_view_change_effective_date.xml',
        #  'views/change_effective_date_wizard.xml',
         'views/change_effective_date_wizard_view.xml',
        #  'security/security.xml',
    ], 
    'i18n': [
            'i18n/es.po',
            'i18n/fr.po',
            'i18n/de.po',
            'i18n/ja_JP.po',
    ],
    "images": [
            "static/description/banner.png",
    ],
    'license': 'OPL-1',
    "installable" : True,
    "application" : True,
    'price': 00.00,
    'currency': 'USD'
}
# Copyright 2018-2022 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

{
    "name": "Restrict Pickings and Stock Moves Delete",
    "summary": """
        This module helps to restrict the delete option for pickings and stock moves.""",
    "version": "17.0.1.0.0",
    "category": "Uncategorized",
    "website": "https://sodexis.com/",
    "author": "Sodexis",
    "license": "OPL-1",
    "installable": True,
    "application": False,
    "depends": [
        "stock",
    ],
    "data": [
        "security/security.xml",
    ],
    "images": ["images/main_screenshot.png"],
    "live_test_url": "https://sodexis.com/odoo-apps-store-demo",
}

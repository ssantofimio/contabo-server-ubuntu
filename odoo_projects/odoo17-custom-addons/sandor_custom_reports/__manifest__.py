# -*- coding: utf-8 -*-
{
    "name": "Sandor Custom Reports (Independent)",
    "version": "17.0.1.0.0",
    "category": "Reporting",
    "summary": "Independent copy of Spreadsheet Dashboard for custom reports",
    "description": "This module provides a standalone dashboard system based on Odoo Spreadsheet, completely independent of the standard spreadsheet_dashboard module.",
    "author": "Sandor",
    "license": "LGPL-3",
    "depends": ["spreadsheet", "purchase", "stock", "sale", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/dashboard.xml",
        "views/sandor_spreadsheet_dashboard_views.xml",
        "views/menu_views.xml",
        "views/sandor_spreadsheet_dashboard_custom_menu_views.xml",
    ],
    "assets": {
        "spreadsheet.o_spreadsheet": [
            "sandor_custom_reports/static/src/bundle/**/*.js",
            "sandor_custom_reports/static/src/bundle/**/*.xml",
        ],
        "web.assets_backend": [
            "sandor_custom_reports/static/src/assets/**/*.js",
            "sandor_custom_reports/static/src/**/*.scss",
        ],
    },
    "installable": True,
    "application": True,
}

/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadSpreadsheetAction } from "@spreadsheet/assets_backend/spreadsheet_action_loader";

const actionRegistry = registry.category("actions");

const loadDashboardAction = async (env, context) => {
    await loadSpreadsheetAction(env, "action_sandor_custom_reports", loadDashboardAction);
    return {
        ...context,
        target: "current",
        tag: "action_sandor_custom_reports",
        type: "ir.actions.client",
    };
};

actionRegistry.add("action_sandor_custom_reports", loadDashboardAction);

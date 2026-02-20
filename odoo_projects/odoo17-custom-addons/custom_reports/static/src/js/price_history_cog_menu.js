/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class PriceHistoryCogMenu extends Component {
    static template = "custom_reports.PriceHistoryCogMenu";
    static components = { DropdownItem };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
    }

    async onClick() {
        console.log("PriceHistoryCogMenu onClick");
        const domain = this.env.searchModel ? this.env.searchModel.domain : [];
        console.log("PriceHistoryCogMenu domain", domain);

        this.actionService.doAction({
            type: 'ir.actions.report',
            report_name: 'custom_reports.report_price_history_document',
            report_type: 'qweb-pdf',
            data: { active_domain: domain },
        });

        this.env.services.notification.add("Generando reporte resumido...", {
            type: "info",
        });
    }
}

export const priceHistoryCogMenuItem = {
    Component: PriceHistoryCogMenu,
    groupNumber: 20,
    isDisplayed: (env) => {
        const resModel = env.config && env.config.resModel;
        const searchResModel = env.searchModel && env.searchModel.resModel;
        const targetModel = "purchase.report.price.history";
        const isMatch = resModel === targetModel || searchResModel === targetModel;
        console.log("PriceHistoryCogMenu isDisplayed check", { resModel, searchResModel, isMatch });
        return isMatch;
    },
};

registry.category("cogMenu").add("price-history-print", priceHistoryCogMenuItem, { sequence: 10 });

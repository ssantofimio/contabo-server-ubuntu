/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class StockPhysCountCogMenu extends Component {
    static template = "custom_reports.StockPhysCountCogMenu";
    static components = { DropdownItem };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async onClick() {
        console.log("StockPhysCountCogMenu onClick");
        const domain = this.env.searchModel ? this.env.searchModel.domain : [];
        const context = this.env.searchModel ? this.env.searchModel.context : {};
        console.log("StockPhysCountCogMenu domain", domain);

        this.actionService.doAction({
            type: 'ir.actions.report',
            report_name: 'custom_reports.report_stock_phys_count_document',
            report_type: 'qweb-pdf',
            data: {
                active_domain: domain,
                valuation_method: context.valuation_method
            },
            context: context,
        });

        this.notification.add("Generando reporte de detalles...", {
            type: "info",
        });
    }

    async onSummaryClick() {
        console.log("StockPhysCountCogMenu onSummaryClick");
        const domain = this.env.searchModel ? this.env.searchModel.domain : [];
        const context = this.env.searchModel ? this.env.searchModel.context : {};

        this.actionService.doAction({
            type: 'ir.actions.report',
            report_name: 'custom_reports.report_stock_phys_summary_document',
            report_type: 'qweb-pdf',
            data: {
                active_domain: domain,
                valuation_method: context.valuation_method
            },
            context: context,
        });

        this.notification.add("Generando resumen por categoría...", {
            type: "info",
        });
    }

    async onExcelClick() {
        const domain = this.env.searchModel ? this.env.searchModel.domain : [];
        const context = this.env.searchModel ? this.env.searchModel.context : {};

        const data = {
            active_domain: domain,
            valuation_method: context.valuation_method || 'avg',
        };

        const queryParams = new URLSearchParams({
            model: "stock.report.phys.count",
            options: JSON.stringify(data),
            output_format: "xlsx",
            report_name: "Reporte_Conteos_Fisicos",
        });

        const url = "/xlsx_reports?" + queryParams.toString();

        this.notification.add("Generando archivo Excel por almacén...", {
            type: "info",
            sticky: false,
        });

        window.location.assign(url);
    }
}

export const stockPhysCountCogMenuItem = {
    Component: StockPhysCountCogMenu,
    groupNumber: 20,
    isDisplayed: (env) => {
        const resModel = env.config && env.config.resModel;
        const searchResModel = env.searchModel && env.searchModel.resModel;
        const targetModel = "stock.report.phys.count";
        return resModel === targetModel || searchResModel === targetModel;
    },
};

registry.category("cogMenu").add("stock-phys-count-print", stockPhysCountCogMenuItem, { sequence: 11 });

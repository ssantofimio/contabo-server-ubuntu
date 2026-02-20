/** @odoo-module */

import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(OrderWidget.prototype, {
    get buttonToShow() {
        const result = super.buttonToShow;

        // Passive check: Only modify if our custom module flow is enabled AND customer is NOT identified
        const isIdentified = this.selfOrder.currentOrder && this.selfOrder.currentOrder.partner_id;

        if (this.selfOrder.customIdentificationEnabled && !isIdentified && result.label === _t("Pay")) {
            return {
                ...result,
                label: _t("Confirm"),
            };
        }
        return result;
    }
});

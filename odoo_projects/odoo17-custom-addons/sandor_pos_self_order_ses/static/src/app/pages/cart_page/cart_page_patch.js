/** @odoo-module */

import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { patch } from "@web/core/utils/patch";

patch(CartPage.prototype, {
    get linesToDisplay() {
        const lines = super.linesToDisplay;
        // Filter out lines that refer to products not present in the current POS config
        // This prevents "Cannot read property 'name' of undefined" in the template
        return lines.filter(line => this.selfOrder.productByIds[line.product_id]);
    },

    getChildLines(line) {
        return super.getChildLines(line).filter(l => this.selfOrder.productByIds[l.product_id]);
    }
});

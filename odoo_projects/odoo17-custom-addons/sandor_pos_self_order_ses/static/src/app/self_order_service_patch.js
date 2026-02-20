/** @odoo-module */

import { SelfOrder } from "@pos_self_order/app/self_order_service";
import { patch } from "@web/core/utils/patch";

patch(SelfOrder.prototype, {
    get customIdentificationEnabled() {
        return this.config?.self_order_custom_identification || false;
    },

    async addToCart(product, qty, customer_note, selectedValues, customValues) {
        // If the order is already confirmed (assigned to a customer), don't allow adding more items
        if (this.currentOrder && this.currentOrder.partner_id) {
            return;
        }

        // Call the original method using super with ...arguments
        return super.addToCart(...arguments);
    },

    async rpc(route, params) {
        return await super.rpc(...arguments);
    },

    initData() {
        super.initData(...arguments);
        // Global cleanup for categories
        if (this.categoryList) {
            const clean = Array.from(this.categoryList).filter(c => c && typeof c.id !== 'undefined');
            if (clean.length !== this.categoryList.size) {
                this.categoryList = new Set(clean);
            }
        }
        if (!this.currentCategory && this.categoryList && this.categoryList.size > 0) {
            this.currentCategory = Array.from(this.categoryList)[0];
        }
    },

    async confirmOrder() {
        const order = this.currentOrder;

        // NEW: Only use custom identification flow if enabled in POS configuration
        const isCustomEnabled = this.config.self_order_custom_identification;

        // If no partner is assigned AND custom flow is enabled, redirect to the custom identification page
        if (isCustomEnabled && order && !order.partner_id) {
            this.router.navigate("customer_info");
            return;
        }

        return await super.confirmOrder(...arguments);
    }
});

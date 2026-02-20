/** @odoo-module */

import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { patch } from "@web/core/utils/patch";

patch(ProductListPage.prototype, {
    setup() {
        // CLEANUP categoryList if it has undefined/null BEFORE super.setup
        if (this.selfOrder && this.selfOrder.categoryList) {
            const arr = Array.from(this.selfOrder.categoryList).filter(c => c && typeof c.id !== 'undefined');
            if (arr.length !== this.selfOrder.categoryList.size) {
                this.selfOrder.categoryList = new Set(arr);
            }
        }

        // Ensure a valid currentCategory BEFORE super.setup
        if (this.selfOrder && !this.selfOrder.currentCategory && this.selfOrder.categoryList && this.selfOrder.categoryList.size > 0) {
            this.selfOrder.currentCategory = Array.from(this.selfOrder.categoryList)[0];
        }

        super.setup(...arguments);

        // Final fallback safeguard AFTER super.setup
        if (this.selfOrder && !this.selfOrder.currentCategory && this.selfOrder.categoryList && this.selfOrder.categoryList.size > 0) {
            this.selfOrder.currentCategory = Array.from(this.selfOrder.categoryList)[0];
        }
    },
});

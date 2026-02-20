/** @odoo-module */

import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";
import { patch } from "@web/core/utils/patch";

patch(ConfirmationPage.prototype, {
    async setup() {
        super.setup(...arguments);
    },

    async initOrder() {
        await super.initOrder(...arguments);
    },

    viewDetail() {
        this.router.navigate("cart");
    },

    backToHome() {
        sessionStorage.setItem("pos_self_stay_on_home", "true");
        super.backToHome();
    }
});

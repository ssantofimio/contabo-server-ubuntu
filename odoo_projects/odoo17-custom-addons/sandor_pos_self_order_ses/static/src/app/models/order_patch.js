/** @odoo-module */

import { Order } from "@pos_self_order/app/models/order";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup(vals) {
        super.setup(...arguments);
        // Ensure partner_id is correctly set during recovery/init
        if (vals && vals.partner_id) {
            this.partner_id = vals.partner_id;
        }
    },

    updateDataFromServer(data) {
        const partnerIdBackup = this.partner_id;
        super.updateDataFromServer(data);

        // Restore if server wiped it out with False but we had it locally
        // This handles the case where process_new_order returns partner_id=False
        if (partnerIdBackup && !this.partner_id && data.partner_id === false) {
            this.partner_id = partnerIdBackup;
        }
    }
});

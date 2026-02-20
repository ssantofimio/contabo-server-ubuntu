/** @odoo-module */

import { selfOrderIndex } from "@pos_self_order/app/self_order_index";
import { CustomerInfoPage } from "@sandor_pos_self_order_ses/app/pages/customer_info_page/customer_info_page";

if (!selfOrderIndex.components) {
    selfOrderIndex.components = {};
}
Object.assign(selfOrderIndex.components, { CustomerInfoPage });


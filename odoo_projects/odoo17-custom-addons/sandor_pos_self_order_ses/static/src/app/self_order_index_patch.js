/** @odoo-module */

import selfOrderIndexModule from "@pos_self_order/app/self_order_index";
import { CustomerInfoPage } from "@sandor_pos_self_order_ses/app/pages/customer_info_page/customer_info_page";

Object.assign(selfOrderIndexModule.selfOrderIndex.components, { CustomerInfoPage });

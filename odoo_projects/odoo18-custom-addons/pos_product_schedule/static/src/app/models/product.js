/** @odoo-module **/
import { Product } from "@pos_self_order/app/models/product";
import { patch } from "@web/core/utils/patch";

patch(Product.prototype, {
    setup(product, showPriceTaxIncluded) {
        super.setup(...arguments);
        this.pos_weekday_ids = product.pos_weekday_ids || [];
        this.pos_time_start = product.pos_time_start;
        this.pos_time_end = product.pos_time_end;
    },
});
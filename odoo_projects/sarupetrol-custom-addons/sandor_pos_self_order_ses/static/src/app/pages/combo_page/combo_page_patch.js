/** @odoo-module */

import { ComboPage } from "@pos_self_order/app/pages/combo_page/combo_page";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ComboPage.prototype, {
    /**
     * @override
     */
    next() {
        if (this._validateSelection()) {
            super.next(...arguments);
        }
    },

    /**
     * @override
     */
    async addToCart() {
        if (this._validateSelection()) {
            return super.addToCart(...arguments);
        }
    },

    /**
     * Validates that the currently selected product has all its required attributes populated.
     * @returns {boolean}
     */
    _validateSelection() {
        const product = this.state.selectedProduct;
        if (!product || !product.attributes || product.attributes.length === 0) {
            return true;
        }

        for (const attr of product.attributes) {
            const value = this.env.selectedValues[attr.id];

            let isSelected = false;
            if (attr.display_type === 'multi') {
                isSelected = value && Object.values(value).some(v => v);
            } else {
                isSelected = !!value;
            }

            if (!isSelected) {
                this.selfOrder.notification.add(_t("Por favor seleccione una opción para %s", attr.name), {
                    type: "danger",
                });
                return false;
            }
        }

        return true;
    }
});

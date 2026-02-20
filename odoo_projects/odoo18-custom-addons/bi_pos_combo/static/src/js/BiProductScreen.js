/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { SelectComboProductPopupWidget } from "@bi_pos_combo/js/SelectComboProductPopupWidget";


patch(ProductScreen.prototype, {
   	setup() {
		super.setup();
	}, 

	async addProductToOrder(product) {
		var self = this;
    	let order = this.pos.get_order();
    	if(product.is_pack){
    		var required_products = [];
			var optional_products = [];
			var combo_products = this.pos.models["product.pack"].filter((p) => p.raw.bi_product_product === product.id)
			combo_products.forEach((combo) =>{
				if(combo.product_ids){
					combo.product_ids.forEach((prod) => {
						if(combo.is_required){
							prod.combo_qty = 1
							required_products.push(prod)
						}
						else{
							prod.combo_qty = 0;
							if(prod.combo_limitation === 0){
								prod.combo_limitation = product.combo_limitation;
							}
							optional_products.push(prod)
						}
					})
				}
				else{
					alert("Please set the category to the combo products.")
				}
			})
			if(required_products.length > 0 || optional_products.length > 0){
					self.dialog.add(SelectComboProductPopupWidget, {'product': product,'required_products':required_products,'optional_products':optional_products , 'update_line' : false });
			}
			else{
				super.addProductToOrder(...arguments);
			}
    	}
    	else{
    		super.addProductToOrder(...arguments);
    	}
	}, 

});
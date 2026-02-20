/** @odoo-module */

import { ProductsWidget } from "@point_of_sale/app/screens/product_screen/product_list/product_list";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(ProductsWidget.prototype,{

    setup() {
        super.setup();
        this.pos = usePos();
    },
    _updateSearch(event) {
    	this.state.searchWord = event.detail;
	},
	get productsToDisplay() {
		let self = this;
		let prods = super.productsToDisplay;
		let use_combo = self.pos.config.use_combo;
		if (this.searchWord !== '') {
            let products =  this.pos.db.search_product_in_category(
                this.selectedCategoryId,
                this.searchWord
            );
            var product_list = []
                for (let product in products){
                	if(products[product].is_pack == true){
                		if(use_combo){
                			product_list.push(products[product])
                		}

                	}else{
                		product_list.push(products[product])
                	}

                }
               	return product_list
        } else {
           	let products =  this.pos.db.get_product_by_category(this.selectedCategoryId);
        	
            var product_list = []
                for (let product in products){
                	if(products[product].is_pack == true){
                		if(use_combo){
                			product_list.push(products[product])
                		}

                	}else{
                		product_list.push(products[product])
                	}

                }
               	return product_list
        }
		
	}


});
/** @odoo-module */

import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { SelectComboProductPopupWidget } from "@bi_pos_combo/js/SelectComboProductPopupWidget";


patch(OrderWidget.prototype, {
   	setup() {
		super.setup();
	},
	get addedClasses() {	
        return {
            selected: this.props.line.selected,
        };
	},
	
    on_click(){

        var pack_product = this.env.services.pos
        var product = this.props.line.product

        var optional_products_list = this.props.line.get_combo_products()

        var required_products = [];
        var optional_products = [];

        var combo_products = pack_product.product_pack;

        if(product)
        {
            for (var i = 0; i < combo_products.length; i++) {
                if(combo_products[i]['bi_product_product'][0] == product['id'])
                {
                    if(combo_products[i]['is_required'])
                    {
                        combo_products[i]['product_ids'].forEach(function (prod) {

                            var sub_product = optional_products_list.filter(function(item) {
                                return item.id == prod;
                            });

                            if(sub_product != undefined && sub_product.length > 0){
                                required_products.push(sub_product[0])
                            }else{
                                var sub_product_cust = product.pos.db.get_product_by_id(prod);
                                required_products.push(sub_product_cust)

                            }
                        });
                    }
                    else{
                        combo_products[i]['product_ids'].forEach(function (prod) {
                            var sub_product = optional_products_list.filter(function(item) {
                                return item.id == prod;
                            });

                            if(sub_product != undefined && sub_product.length > 0){
                                optional_products.push(sub_product[0])
                            }else{
                                var sub_product_cust = product.pos.db.get_product_by_id(prod);
                                optional_products.push(sub_product_cust)

                            }
                        });
                    }
                }
            }
        }
        this.env.services.pos.popup.add(SelectComboProductPopupWidget, {'product': product,'required_products':required_products,'optional_products':optional_products , 'update_line' : true });
    },

	selectLine() {
    this.trigger('select-line', { orderline: this.props.line });
    },

    lotIconClicked() {
        this.trigger('edit-pack-lot-lines', { orderline: this.props.line });
    } 
    
});

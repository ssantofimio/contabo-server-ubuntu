import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { roundDecimals, roundPrecision, floatIsZero } from "@web/core/utils/numbers";
import { PosStore } from "@point_of_sale/app/store/pos_store";


patch(OrderSummary.prototype, {
	_setValue(val) {
    	const { numpadMode } = this.pos;
    	let self = this;
		let selectedLine = this.currentOrder.get_selected_orderline();
        if (selectedLine) {
			if(selectedLine.product_id.is_pack){
				if(numpadMode==='quantity'){
					
					if (val === "remove" || val === null) {
	                    this.currentOrder.removeOrderline(selectedLine);
	                }else{
	                	selectedLine.set_quantity(val,'keep_price')
	                } 

				}else{
					super._setValue(val);
				}
			}	
			else{
				super._setValue(val);
			}
		} 
    }

});

patch(PosOrderline.prototype, {
	setup(vals) {
        super.setup(vals);
    },


	set_combo_price(price){
		var self = this;
		var prods = this.combo_prod_ids;
		var total = price;
		prods.forEach(function (prod) {
			if(prod)
			{
				total += prod.lst_price	* prod.combo_qty
			}	
		});
		if(self.config.combo_pack_price== 'all_product'){
			this.set_unit_price(total);
		}
		else{
			this.set_unit_price(price);
		}
	},

	// set_is_pack(is_pack){
	// 	this.is_pack = is_pack
	// },

	get_combo_products(){
		if(this.combo_prod_ids.length > 0){
			let combo_list = []
			combo_list = this.combo_prod_ids.map((p) => [{'id':p.id, 'display_name':p.display_name, 'qty':p.combo_qty}]);
			
			const unique = Array.from(
			  new Set(combo_list.map(JSON.stringify)),
			  JSON.parse
			);
			return unique
		}
		else{
			return [];
		}
	},

	getDisplayData() {
        return {
            ...super.getDisplayData(),
            is_pack : this.is_pack,
			combo_products : this.get_combo_products(),
        };
    },
});

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                is_pack: { type: Boolean, optional: true },
                combo_products: {type: Array, optional: true},
            },
        },
    },
});






// patch(Order.prototype, {
// 	setup() {
//         super.setup(...arguments);
// 		this.barcode = this.barcode || "";
// 	},
// 	// set_partner(partner) {
//     //     this.assert_editable();
//     //     this.partner = partner;
//     // }

// });

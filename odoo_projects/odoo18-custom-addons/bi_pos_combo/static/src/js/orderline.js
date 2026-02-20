import { patch } from "@web/core/utils/patch";
import { roundDecimals as round_di } from "@web/core/utils/numbers";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { SelectComboProductPopupWidget } from "@bi_pos_combo/js/SelectComboProductPopupWidget";
import { useService } from "@web/core/utils/hooks";


patch(Orderline.prototype, {
    
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    },
    
    on_click(){

	    var pack_product = this.env.services.pos
        var pos_line = this.props.slots['product-name']['__ctx']['line']
        pos_line.order_id.select_orderline(pos_line)
        var product = pos_line.product_id

		var required_products = [];
		var optional_products = [];
		var combo_products = pack_product.models["product.pack"].filter((p) => p.raw.bi_product_product === product.id)

        if(product)
		{
			combo_products.forEach((combo) =>{
				if(combo.product_ids){
					combo.product_ids.forEach((prod) => {
						if(combo.is_required){
							// prod.combo_qty = 1
							required_products.push(prod)
						}
						else{
							// prod.combo_qty = 0;
							if(prod.combo_limitation === 0){
								prod.combo_limitation = product.combo_limitation;
							}
							optional_products.push(prod)
						}
					})
				}
			})
		}
		this.dialog.add(SelectComboProductPopupWidget, {'product': product,'required_products':required_products,'optional_products':optional_products , 'update_line' : true });
	},
});
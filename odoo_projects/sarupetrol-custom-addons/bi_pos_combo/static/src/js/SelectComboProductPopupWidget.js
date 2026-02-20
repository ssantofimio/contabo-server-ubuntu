import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class SelectComboProductPopupWidget extends Component {
    static template = "bi_pos_combo.SelectComboProductPopupWidget";
    static components = {
        Dialog,
    };
    static props = [
    	"close",
    	"product",
    	"required_products",
    	"optional_products",
    	"update_line"
    ];

    setup() {
		super.setup();
		this.pos = usePos();
		onMounted(() =>{
			var self = this;
			var order = self.pos.get_order();
			if(order){
				var orderlines = order.get_orderlines();
				this.product = self.props.product;
				this.update_line = self.props.update_line;
				this.required_products = self.props.required_products;
				this.optional_products = self.props.optional_products;
				// this.combo_products = self.pos.pos_product_pack;

				let optional_products = document.getElementsByClassName('optional-product')
				for(var value of optional_products) {
					if(self.update_line){
	                    var selectedprod = parseInt(value.dataset.productId);
	                    var order = self.pos.get_order();
	                    var selected_orderline = order.get_selected_orderline()
	                        if (selected_orderline) {
	                            if(selected_orderline.product_id.id == self.product.id){

	                                var selected_product = selected_orderline.combo_prod_ids
	                                for (var i = 0; i < selected_product.length; i++){

	                                    if(selected_product[i] == selectedprod){
	                                        var prod = document.getElementById(id)
	                                        prod.classList.add('selected-product');
	                                   }
	                               };
	                            }
	                        }
	                    // }
	                }
				};
			}
		});
	}
	go_back_screen() {
		this.props.close()
	}
	RemoveProd(event){
		var self = this;
		var currentProductId = event.target.getAttribute("data-product-id")
		var prod = document.getElementById(currentProductId)
		prod.remove();
		for (var i = 0; i < self.props.optional_products.length; i++)
		{
			if(self.props.optional_products[i].id == currentProductId)
			{
				self.props.optional_products.splice(i, 1);
			}
		}

	}
	update_produc(id,qty){
		var prod = document.getElementById(id)
		
		if(self.update_line){
            var selectedprod = parseInt(prod.dataset.productId);
            var order = self.pos.get_order();
            if(order){
            	var selected_orderline = order.get_selected_orderline()
                if (selected_orderline) {
                    if(selected_orderline.product.id == self.props.product.id){
                        var selected_product = selected_orderline.combo_prod_ids
                        for (var i = 0; i < selected_product.length; i++){

                            if(selected_product[i] == selectedprod){
                                prod.classList.add('selected-product');
                            }
                        };
                    }
                 }
             }
        }
        else{
			if(qty > 0){
				if(! prod.classList.contains('selected-product') ){
                	prod.classList.add('selected-product');
                }
			}else{
				if(prod.classList.contains('selected-product') ){
                	prod.classList.remove('selected-product');
                }
			}

        }
	}

	update_optional_product_by_id(id,qty){
		var self = this
		this.props.optional_products.forEach((prd) => {
			if(prd.id == id){
				if(qty > prd.combo_limitation ){
					alert("product limit exceeded")
				}else{
					prd.combo_qty = qty
					self.update_produc(id,qty)
				}
			}
		});
	}

	AddQty(event) {
		var self = this;
		var currentProductId = event.target.getAttribute("data-product-id")
		var label_ele = document.getElementsByClassName('qty-label');

		for(var label of label_ele){
			var product_id =  parseInt(label.getAttribute('product-id'))
			let product = self.pos.models["product.product"].getBy("id", product_id);
			if (currentProductId == product_id){
				let added_qty = parseInt(label.textContent) + 1
				if(added_qty <= product.combo_qty){
					label.textContent = added_qty
				}
				self.update_optional_product_by_id(product_id,added_qty)
			}
		}
	}

	MinusQty(event) {
		var self = this;
		var currentProductId = event.target.getAttribute("data-product-id")
		var label_ele = document.getElementsByClassName('qty-label');
		for(var label of label_ele){
			var product_id =  parseInt(label.getAttribute('product-id'))
			let product = self.pos.models["product.product"].getBy("id", product_id);
			if (currentProductId == product_id){
				if (parseInt(label.textContent) > 0){
					let removed_qty = parseInt(label.textContent) - 1
					label.textContent = removed_qty
					self.update_optional_product_by_id(product_id,removed_qty)
				}
			}
		};
	}

	get req_product() {
		let req_product = [];
		this.props.required_products.forEach((prd) => {
			prd['product_image_url'] = `/web/image?model=product.product&field=image_128&id=${prd.id}&write_date=${prd.write_date}&unique=1`;
			req_product.push(prd)
		});
		return req_product;
	}

	get optional_product(){
		let optional_product = [];
		this.props.optional_products.forEach((prd) => {
			prd['product_image_url'] = `/web/image?model=product.product&field=image_128&id=${prd.id}&write_date=${prd.write_date}&unique=1`;
			optional_product.push(prd)
		});
		return optional_product;
	}


		
	renderElement(event) {
		var self = this;
		var rm_id = event.target.getAttribute('data-product-id');
		var rm_prod = document.getElementById(rm_id);
		if(rm_prod){
			if(rm_prod.classList.contains('selected-product')){
	        	rm_prod.classList.remove('selected-product');
	        }else{
	        	rm_prod.classList.add('selected-product');
	        }
		}
	}

	async add_confirm(ev){
		var final_products = this.props.required_products;
		var combo_lines = []
		var order = this.pos.get_order();
		var selected_orderline = order.get_selected_orderline();
		ev.stopPropagation();
		ev.preventDefault();
		var self = this   
		var selected_prods = document.getElementsByClassName('selected-product')
		for (var prods of selected_prods){
			var prod_id = parseInt(prods.getAttribute('data-product-id'));
			for (var i = 0; i < self.props.optional_products.length; i++) 
			{
				if(self.props.optional_products[i].id == prod_id)
				{
					final_products.push(self.props.optional_products[i]); 
					
				}
			}
			
		};
		
		if(self.props.update_line){
		
            if(selected_orderline == null){
            	
			
                const newLineValues = {
	                product_id: self.props.product,
	                price_unit: self.props.product.lst_price,
	                description: self.props.product.display_name,
	                is_pack: self.props.product.is_pack,
	            };
	            const newLine = await this.pos.addLineToCurrentOrder(newLineValues, {}, false);

            final_products.forEach((f_p) => {
				newLine.combo_prod_ids.push(f_p)
				const combo_line  = {
	            		combo_product_id : f_p.id,
	            		combo_qty : f_p.combo_qty,
	            		line_uuid : newLine.uuid,
	            	}
	            combo_lines.push(combo_line)
			});
			self.env.services.orm.call("pos.orderline.comboproduct","create", [combo_lines])
			
			newLine.set_combo_price(newLine.price_unit)
		}
		}else{
			const newLineValues = {
                product_id: self.props.product,
                price_unit: self.props.product.lst_price,
                description: self.props.product.display_name,
                is_pack: self.props.product.is_pack,
            };
            const newLine = await this.pos.addLineToCurrentOrder(newLineValues, {}, false);
			final_products.forEach((f_p) => {
				newLine.combo_prod_ids.push(f_p)
				const combo_line  = {
	            		combo_product_id : f_p.id,
	            		combo_qty : f_p.combo_qty,
	            		line_uuid : newLine.uuid,
	            	}
	            combo_lines.push(combo_line)

			});
				const cline  = self.env.services.orm.call("pos.orderline.comboproduct","create", [combo_lines])
			newLine.set_combo_price(newLine.price_unit)
		}
		self.props.close();
	}
}


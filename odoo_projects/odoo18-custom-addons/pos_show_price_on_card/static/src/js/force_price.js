cat <<'EOF' > ~/odoo18/custom-addons/pos_show_price_on_card/static/src/js/force_price.js
odoo.define('pos_show_price_on_card.force_price', function (require) {
    const ProductCard = require('point_of_sale.ProductCard');
    const Registries = require('point_of_sale.Registries');

    const PriceInjector = (ProductCard) =>
        class extends ProductCard {
            mounted() {
                super.mounted && super.mounted();
                try {
                    const nameEl = this.el.querySelector('.product-name');
                    if (nameEl) {
                        let priceText = "";
                        if (this.props.displayedPrice) {
                            priceText = this.props.displayedPrice;
                        } else if (this.props.product && this.props.product.pricelist_price) {
                            priceText = this.env.pos.format_currency(this.props.product.pricelist_price);
                        } else if (this.props.product && this.props.product.lst_price) {
                            priceText = this.env.pos.format_currency(this.props.product.lst_price);
                        }
                        if (priceText) {
                            const priceDiv = document.createElement('div');
                            priceDiv.style.fontSize = '0.85em';
                            priceDiv.style.marginTop = '3px';
                            priceDiv.textContent = priceDiv.textContent = priceText;
                            nameEl.insertAdjacentElement('afterend', priceDiv);
                        }
                    }
                } catch (e) {
                    console.warn('PriceInjector error', e);
                }
            }
        };

    Registries.Component.extend(ProductCard, PriceInjector);
});
EOF

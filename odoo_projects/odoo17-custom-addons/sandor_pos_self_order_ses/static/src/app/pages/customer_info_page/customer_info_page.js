/** @odoo-module */

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { _t } from "@web/core/l10n/translation";
import { Order } from "@pos_self_order/app/models/order";

export class CustomerInfoPage extends Component {
    static template = "sandor_pos_self_order_ses.CustomerInfoPage";

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
        this.state = useState({
            isSearching: true,
            email: "",
            name: "",
            phone: "",
            mobile: "",
            id_type_id: null,
            vat: "",
            street: "",
            street2: "",
            city: "",
            zip: "",
            country_id: null,
            state_id: null,
            partner: null,
            showForm: false,
            searched: false,
        });

        onWillStart(async () => {
            try {
                // Set default country from company if available
                if (this.selfOrder.company && this.selfOrder.company.country_id && !this.state.country_id) {
                    this.state.country_id = this.selfOrder.company.country_id;
                }

                if (!this.selfOrder.countries || !this.selfOrder.states || !this.selfOrder.identification_types) {
                    const data = await this.selfOrder.rpc("/pos-self-order/get-customer-form-data", {
                        access_token: this.selfOrder.access_token,
                    });

                    if (data) {
                        this.selfOrder.countries = data.countries || [];
                        this.selfOrder.states = data.states || [];
                        this.selfOrder.identification_types = data.identification_types || [];
                    }
                }
            } catch (err) {
                console.error("[CustomerInfoPage] Error in onWillStart:", err);
            }
        });
    }

    getStates() {
        if (!this.state.country_id || !this.selfOrder.states) {
            return [];
        }
        const countryId = Array.isArray(this.state.country_id) ? this.state.country_id[0] : parseInt(this.state.country_id);
        return this.selfOrder.states.filter(s => s.country_id[0] === countryId);
    }

    async searchPartner() {
        if (!this.state.vat) return;

        this.selfOrder.rpcLoading = true;
        try {
            const partner = await this.selfOrder.rpc("/pos-self-order/search-partner-by-nif", {
                nif: this.state.vat,
                access_token: this.selfOrder.access_token,
            });

            if (partner) {
                // STRICT VALIDATION FOR BUSY TABLES
                if (this.selfOrder.table && this.selfOrder.table.is_busy) {
                    const ownsOrderAtThisTable = partner.active_orders && partner.active_orders.some(o => {
                        return Number(o.table_id) === Number(this.selfOrder.table.id);
                    });

                    if (!ownsOrderAtThisTable) {
                        this.selfOrder.notification.add(_t("No eres el titular del pedido de esta mesa. Verifica tu identificación."), { type: "danger" });
                        this.state.isSearching = true; // KEEP SEARCHING
                        this.state.searched = true;
                        return;
                    }
                }

                // SAVE SESSION IN LOCALSTORAGE (PERSISTENCE)
                const expiry = new Date().getTime() + (2 * 60 * 60 * 1000); // 2 hours
                const sessionData = {
                    nif: this.state.vat,
                    tableId: this.selfOrder.table ? this.selfOrder.table.id : null,
                    expiresAt: expiry
                };
                localStorage.setItem("pos_self_session_cust", JSON.stringify(sessionData));

                this.state.partner = partner;
                this.state.name = partner.name || "";
                this.state.street = partner.street || "";
                this.state.zip = partner.zip || "";
                this.state.city = partner.city || "";
                this.state.email = partner.email || "";
                this.state.phone = partner.phone || "";
                this.state.mobile = partner.mobile || "";
                this.state.country_id = partner.country_id?.[0] || partner.country_id || null;
                this.state.state_id = partner.state_id?.[0] || partner.state_id || null;
                this.state.id_type_id = partner.l10n_latam_identification_type_id?.[0] || null;

                // MULTI-DEVICE RECOVERY LOGIC
                if (partner.active_orders && partner.active_orders.length > 0) {
                    partner.active_orders.forEach(o => {
                        const existing = this.selfOrder.orders.find(eo => eo.access_token === o.access_token);
                        if (!existing) {
                            this.selfOrder.orders.push(new Order(o));
                        }
                    });

                    // Get full data for these orders
                    await this.selfOrder.getOrdersFromServer();

                    // If it's a busy table, we MUST navigate to the order belonging to THIS table
                    let targetOrder = null;
                    if (this.selfOrder.table && this.selfOrder.table.is_busy) {
                        targetOrder = this.selfOrder.orders.find(o =>
                            o && o.partner_id && o.state !== 'paid' && o.state !== 'cancel' &&
                            (o.table_id === this.selfOrder.table.id)
                        );
                    }

                    // Fallback to latest if no specific table match or not busy table
                    if (!targetOrder) {
                        targetOrder = this.selfOrder.orders
                            .filter(o => o && o.partner_id && o.state !== 'paid' && o.state !== 'cancel')
                            .sort((a, b) => (b.id || 0) - (a.id || 0))[0];
                    }

                    if (targetOrder) {
                        this.router.navigate("confirmation", {
                            orderAccessToken: targetOrder.access_token,
                            screenMode: "order",
                        });
                        return;
                    }
                }

                this.state.isSearching = true;
            } else {
                if (this.selfOrder.table && this.selfOrder.table.is_busy) {
                    this.selfOrder.notification.add(_t("Mesa ocupada. No se encontró un pedido activo para esta identificación."), { type: "danger" });
                    this.state.isSearching = true;
                } else {
                    this.state.partner = null;
                    this.state.showForm = true;
                    this.state.isSearching = false;
                }
            }
            this.state.searched = true;
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
        } finally {
            this.selfOrder.rpcLoading = false;
        }
    }

    canSaveForm() {
        return !!(this.state.name && this.state.vat && this.state.id_type_id && this.state.mobile);
    }

    saveForm() {
        if (!this.canSaveForm()) return;

        if (!this.state.partner) {
            this.state.partner = {
                name: this.state.name,
                vat: this.state.vat,
                mobile: this.state.mobile,
                phone: this.state.phone,
                email: this.state.email,
            };
        } else {
            this.state.partner.name = this.state.name;
            this.state.partner.vat = this.state.vat;
            this.state.partner.mobile = this.state.mobile;
            this.state.partner.phone = this.state.phone;
            this.state.partner.email = this.state.email;
        }

        this.state.showForm = false;
        this.state.isSearching = true;
    }

    canConfirm() {
        return !!this.state.partner;
    }

    async confirmAndPay() {
        if (!this.canConfirm()) return;

        let partnerId = this.state.partner?.id;
        const partnerData = {
            name: this.state.name,
            vat: this.state.vat,
            street: this.state.street,
            street2: this.state.street2,
            city: this.state.city,
            zip: this.state.zip,
            email: this.state.email,
            phone: this.state.phone,
            mobile: this.state.mobile,
            country_id: this.state.country_id ? (Array.isArray(this.state.country_id) ? this.state.country_id[0] : parseInt(this.state.country_id)) : false,
            state_id: this.state.state_id ? (Array.isArray(this.state.state_id) ? this.state.state_id[0] : parseInt(this.state.state_id)) : false,
            l10n_latam_identification_type_id: this.state.id_type_id ? parseInt(this.state.id_type_id) : false,
        };

        this.selfOrder.rpcLoading = true;
        try {
            if (!partnerId) {
                const response = await this.selfOrder.rpc("/pos-self-order/create-partner-custom", {
                    partner_data: partnerData,
                    access_token: this.selfOrder.access_token,
                });

                if (response.error) {
                    this.selfOrder.notification.add(response.error, { type: "danger" });
                    this.selfOrder.rpcLoading = false;
                    return;
                }
                partnerId = response.id;
            } else {
                const response = await this.selfOrder.rpc("/pos-self-order/update-partner-custom", {
                    partner_id: partnerId,
                    partner_data: partnerData,
                    access_token: this.selfOrder.access_token,
                });

                if (response.error) {
                    console.error("Error updating partner:", response.error);
                }
            }
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
            this.selfOrder.rpcLoading = false;
            return;
        }

        const expiry = new Date().getTime() + (2 * 60 * 60 * 1000); // 2 hours
        const sessionData = {
            nif: this.state.vat,
            tableId: this.selfOrder.table ? this.selfOrder.table.id : null,
            expiresAt: expiry
        };
        localStorage.setItem("pos_self_session_cust", JSON.stringify(sessionData));

        this.selfOrder.currentOrder.partner_id = partnerId;
        this.selfOrder.currentOrder.force_partner_update = true;

        this.selfOrder.rpcLoading = true;
        try {
            await this.selfOrder.confirmOrder();
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
        } finally {
            this.selfOrder.rpcLoading = false;
            if (this.selfOrder.currentOrder) {
                this.selfOrder.currentOrder.force_partner_update = false;
            }
        }
    }

    get primaryButtonLabel() {
        return this.state.partner ? _t("Confirmar") : _t("Guardar");
    }
}

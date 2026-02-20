/** @odoo-module */

import { LandingPage } from "@pos_self_order/app/pages/landing_page/landing_page";
import { patch } from "@web/core/utils/patch";
import { onWillStart, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { Order } from "@pos_self_order/app/models/order";
import { _t } from "@web/core/l10n/translation";

patch(LandingPage.prototype, {
    setup() {
        super.setup(...arguments);

        // Use local variable for better scope isolation
        const selfOrder = this.selfOrder;

        // Safeguard for table access
        const isTableBusy = selfOrder.table ? selfOrder.table.is_busy : false;

        this.state = useState({
            showBusyWarning: isTableBusy
        });

        onWillStart(async () => {
            // In Kiosk mode, we only want to persist orders that are still active (preparing)
            const activeOrders = selfOrder.orders.filter(o => o.partner_id && o.state !== 'paid' && o.state !== 'cancel');

            if (activeOrders.length > 0 && selfOrder.config.self_ordering_mode === "kiosk") {
                // Use splice to keep the same reactive proxy object
                selfOrder.orders.splice(0, selfOrder.orders.length, ...activeOrders);
            }

            // AUTO-RECOVERY LOGIC FOR BUSY TABLES
            if (selfOrder.table && selfOrder.table.is_busy) {
                const sessionStr = localStorage.getItem("pos_self_session_cust");
                if (sessionStr) {
                    try {
                        const sessionData = JSON.parse(sessionStr);
                        const now = new Date().getTime();

                        if (sessionData.nif && sessionData.expiresAt > now && sessionData.tableId === this.selfOrder.table.id) {
                            const partner = await this.selfOrder.rpc("/pos-self-order/search-partner-by-nif", {
                                nif: sessionData.nif,
                                access_token: this.selfOrder.access_token,
                            });

                            if (partner && partner.active_orders) {
                                // WE ARE IDENTIFIED -> Hide the overlay
                                this.state.showBusyWarning = false;

                                // Sync orders so "Mi Orden" button shows up
                                // Manual order recovery for identified partner
                                if (partner.active_orders && partner.active_orders.length > 0) {
                                    partner.active_orders.forEach(o => {
                                        const existing = this.selfOrder.orders.find(eo => eo.access_token === o.access_token);
                                        if (!existing) {
                                            this.selfOrder.orders.push(new Order(o));
                                        }
                                    });
                                }

                                // Now sync so the "Mi Orden" button logic can find them
                                await this.selfOrder.getOrdersFromServer();

                                const stayOnHome = sessionStorage.getItem("pos_self_stay_on_home");
                                if (stayOnHome) {
                                    sessionStorage.removeItem("pos_self_stay_on_home");
                                    return;
                                }

                                const targetOrder = partner.active_orders.find(o => Number(o.table_id) === Number(this.selfOrder.table.id));
                                if (targetOrder) {
                                    this.router.navigate("confirmation", {
                                        orderAccessToken: targetOrder.access_token,
                                        screenMode: "order",
                                    });
                                    return;
                                }
                            }
                        }
                    } catch (e) {
                        console.error("[LandingPage] Error during auto-recovery:", e);
                    }
                }
            }
        });
    },

    clickMyOrder() {
        // Find the LATEST order that has been confirmed AND is still active (not paid/cancelled)
        const confirmedOrders = this.selfOrder.orders.filter(o => o.partner_id && o.state !== 'paid' && o.state !== 'cancel');
        const latestOrder = confirmedOrders.length > 0 ? confirmedOrders[confirmedOrders.length - 1] : null;

        // If there's an active confirmed order, show the confirmation screen
        if (latestOrder) {
            this.router.navigate("confirmation", {
                orderAccessToken: latestOrder.access_token,
                screenMode: "order",
            });
        } else {
            // No active confirmed order, show the cart/menu as usual
            super.clickMyOrder();
        }
    }
});

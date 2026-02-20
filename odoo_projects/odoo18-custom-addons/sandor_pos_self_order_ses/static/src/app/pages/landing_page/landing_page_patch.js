/** @odoo-module */

import { LandingPage } from "@pos_self_order/app/pages/landing_page/landing_page";
import { patch } from "@web/core/utils/patch";
import { onWillStart, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
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
            const activeOrders = selfOrder.models['pos.order'].filter(o => o.partner_id && o.state !== 'paid' && o.state !== 'cancel');

            if (activeOrders.length > 0 && selfOrder.config.self_ordering_mode === "kiosk") {
                // In v18, models are managed by the data service. 
                // We shouldn't manually splice the internal collections usually, 
                // but if we want to "cleanup" old orders:
                const allOrders = selfOrder.models['pos.order'].getAll();
                for (const o of allOrders) {
                    if (!activeOrders.includes(o)) {
                        o.delete();
                    }
                }
            }

            // AUTO-RECOVERY LOGIC FOR BUSY TABLES
            if (selfOrder.table && selfOrder.table.is_busy) {
                const sessionStr = localStorage.getItem("pos_self_session_cust");
                if (sessionStr) {
                    try {
                        const sessionData = JSON.parse(sessionStr);
                        const now = new Date().getTime();

                        if (sessionData.nif && sessionData.expiresAt > now && sessionData.tableId === selfOrder.table.id) {
                            const partner = await selfOrder.rpc("/pos-self-order/search-partner-by-nif", {
                                nif: sessionData.nif,
                                access_token: selfOrder.access_token,
                            });

                            if (partner && partner.active_orders) {
                                // WE ARE IDENTIFIED -> Hide the overlay
                                this.state.showBusyWarning = false;

                                // Sync orders so "Mi Orden" button shows up
                                // Manual order recovery for identified partner
                                if (partner.active_orders && partner.active_orders.length > 0) {
                                    selfOrder.models.loadData({ 'pos.order': partner.active_orders });
                                }

                                // Now sync so the "Mi Orden" button logic can find them
                                await selfOrder.getOrdersFromServer();

                                const stayOnHome = sessionStorage.getItem("pos_self_stay_on_home");
                                if (stayOnHome) {
                                    sessionStorage.removeItem("pos_self_stay_on_home");
                                    return;
                                }

                                const targetOrder = selfOrder.models['pos.order'].find(o => Number(o.table_id) === Number(selfOrder.table.id));
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
        const confirmedOrders = this.selfOrder.models['pos.order'].filter(o => o.partner_id && o.state !== 'paid' && o.state !== 'cancel');
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

/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
const { DateTime } = luxon;

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (!this.last_order_preparation_change || !this.last_order_preparation_change.lines) {
            this.last_order_preparation_change = {
                metadata: {},
                lines: {},
                generalNote: "",
                sittingMode: "dine in",
            };
        }
    },
});

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.pos_product_schedules = null;
        this.pos_product_schedules_by_id = {};
    },

    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);
        try {
            let schedules = (this.models['pos.session'].getAll()[0]?.pos_product_schedules) || null;
            if (!schedules) {
                try {
                    schedules = await this.data.searchRead('pos.product.schedule', [], ['id', 'name', 'code', 'bit', 'sequence']);
                } catch (err) {
                    schedules = null;
                }
            }
            this.pos_product_schedules = schedules;
            this.pos_product_schedules_by_id = {};
            if (schedules) {
                for (const s of schedules) {
                    this.pos_product_schedules_by_id[s.id] = s;
                }
            }
        } catch (e) {
            console.error("Error loading pos_product_schedule data", e);
        }
    },

    async addLineToCurrentOrder(vals, opts) {
        const product = vals.product_id;
        if (product && !this._isProductAvailableNow(product)) {
            this.env.services.notification.add("Producto no disponible en este horario/día", {
                type: "danger",
            });
            return;
        }
        return await super.addLineToCurrentOrder(...arguments);
    },

    _isProductAvailableNow(product) {
        // Obtener el día actual (Luxon)
        let now;
        try {
            let timezone = luxon.Settings.defaultZoneName;
            if (this.config && this.config.tz) {
                timezone = this.config.tz;
            }
            now = DateTime.now().setZone(timezone);
        } catch (e) {
            now = DateTime.now();
        }
        const today = now.weekday; // 1=Lunes, 7=Domingo

        const weekdayIds = product.pos_weekday_ids || [];
        let allowedIds = [];
        if (weekdayIds.length > 0) {
            if (typeof weekdayIds[0] === 'object') {
                allowedIds = weekdayIds.map(w => w.id);
            } else {
                allowedIds = weekdayIds;
            }
        }

        let schedulesById = this.pos_product_schedules_by_id || {};
        let todaySchedule = Object.values(schedulesById).find(s => Number(s.sequence) === Number(today));

        const dayAllowed = (weekdayIds.length === 0) || (todaySchedule && allowedIds.includes(Number(todaySchedule.id)));

        // Verificar hora
        const timeStart = product.pos_time_start;
        const timeEnd = product.pos_time_end;
        let timeAllowed = true;

        if (timeStart || timeEnd) {
            const currentHour = now.hour + now.minute / 60.0;
            if (timeStart && timeEnd) {
                timeAllowed = currentHour >= timeStart && currentHour <= timeEnd;
            } else if (timeStart) {
                timeAllowed = currentHour >= timeStart;
            } else if (timeEnd) {
                timeAllowed = currentHour <= timeEnd;
            }
        }

        return dayAllowed && timeAllowed;
    }
});

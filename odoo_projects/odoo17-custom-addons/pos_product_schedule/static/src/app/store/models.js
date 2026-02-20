/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosDB } from "@point_of_sale/app/store/db";
import { PosStore } from "@point_of_sale/app/store/pos_store";
const { DateTime } = luxon;

patch(PosDB.prototype, {
    shouldAddProduct(product, list) {
        const superResult = super.shouldAddProduct ? super.shouldAddProduct(product, list) : true;
        if (!superResult) {
            return false;
        }
        // Obtener el día actual (Luxon: 1=Lunes, 2=Martes, ..., 7=Domingo)
        let now;
        try {
            let timezone = luxon.Settings.defaultZoneName;
            if (this && this.pos && this.pos.config && this.pos.config.tz) {
                timezone = this.pos.config.tz;
            } else if (typeof window !== 'undefined' && window.pos && window.pos.config && window.pos.config.tz) {
                timezone = window.pos.config.tz;
            }
            now = DateTime.now().setZone(timezone);
        } catch (e) {
            now = DateTime.now();
        }
        const today = now.weekday; // 1=Lunes, 2=Martes, ..., 7=Domingo

        // If field not present in the product record, assume no restriction (available all days).
        const weekdayIds = product.pos_weekday_ids || [];
        // Buscar si el producto tiene el día actual en sus días permitidos
        let allowedIds = [];
        if (typeof weekdayIds[0] === 'object' && !Array.isArray(weekdayIds[0])) {
            allowedIds = weekdayIds.map(w => w.id);
        } else if (Array.isArray(weekdayIds[0])) {
            allowedIds = weekdayIds.map(arr => arr[0]);
        } else {
            allowedIds = weekdayIds;
        }
        // Buscar el id de schedule que corresponde al día actual
        let schedulesById = this.pos_product_schedules_by_id || {};
        let todaySchedule = Object.values(schedulesById).find(s => {
            // s.code: 'MON', 'TUE', ...
            // s.bit: 1, 2, 4, ...
            // s.sequence: 1=Lunes, 2=Martes, ...
            return Number(s.sequence) === Number(today);
        });
        if (!todaySchedule) {
            // fallback: buscar por nombre
            const nombres = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'];
            todaySchedule = Object.values(schedulesById).find(s => s.name === nombres[today-1]);
        }
        // Si no hay restricciones por día, permitir; de lo contrario, verificar si incluye hoy
        const dayAllowed = (weekdayIds.length === 0) || (todaySchedule && allowedIds.includes(Number(todaySchedule.id)));


        // Verificar hora del día
        const timeStart = product.pos_time_start;
        const timeEnd = product.pos_time_end;
        let timeAllowed = true;  // Por defecto, permitir

        if (timeStart !== undefined && timeStart !== null && timeEnd !== undefined && timeEnd !== null) {
            // Ambos tienen valores: aplicar rango normal
            if (timeStart > 0 || timeEnd > 0) {
                const currentHour = now.hour + now.minute / 60.0;
                timeAllowed = currentHour >= timeStart && currentHour <= timeEnd;
            }
        } else if (timeStart !== undefined && timeStart !== null && timeStart > 0) {
            // Solo start válido: de start a 24
            const currentHour = now.hour + now.minute / 60.0;
            timeAllowed = currentHour >= timeStart;
        } else if (timeEnd !== undefined && timeEnd !== null && timeEnd > 0) {
            // Solo end válido: de 0 a end
            const currentHour = now.hour + now.minute / 60.0;
            timeAllowed = currentHour <= timeEnd;
        }

        // No debug logging here in production

        return dayAllowed && timeAllowed;
    },
});

patch(PosStore.prototype, {
    async after_load_server_data() {
        await super.after_load_server_data(...arguments);
        // ensure the POS has the list of weekdays available for UI if needed
        try {
            // Prefer schedules attached to the pos session (loaded during initial load)
            let schedules = (this.pos_session && this.pos_session.pos_product_schedules) || null;
            if (!schedules) {
                try {
                    // Use the POS ORM service when available; some contexts don't
                    // expose `this.data` on PosStore, so fallback to this.orm.silent.call
                    if (this.orm && this.orm.silent && typeof this.orm.silent.call === 'function') {
                        schedules = await this.orm.silent.call('pos.product.schedule', 'search_read', [[], ['id', 'name', 'code', 'bit', 'sequence']]);
                    } else if (this.data && typeof this.data.call === 'function') {
                        schedules = await this.data.call('pos.product.schedule', 'search_read', [[], ['id', 'name', 'code', 'bit', 'sequence']]);
                    } else {
                        throw new Error('No RPC mechanism available (this.orm or this.data)');
                    }
                } catch (err) {
                    // RPC failed -> silently ignore; schedules will be null and handled below
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
            // Also expose mapping on DB for PosDB consumers (this in PosDB is DB instance)
            if (this.db) {
                this.db.pos_product_schedules_by_id = this.pos_product_schedules_by_id;
            }
        } catch (e) {
            // model may not exist if not installed; ignore
        }
        // Debugging removed: do not print diagnostic report in production
    },
});

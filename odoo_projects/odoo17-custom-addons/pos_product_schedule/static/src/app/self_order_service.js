/** @odoo-module **/
import { SelfOrder } from "@pos_self_order/app/self_order_service";
import { patch } from "@web/core/utils/patch";
const { DateTime } = luxon;

patch(SelfOrder.prototype, {
    shouldAddProduct(product) {
        // If field not present in the product record, assume no restriction (available all days).
        const weekdayIds = product.pos_weekday_ids || [];
        if (!weekdayIds.length) {
            return true;
        }
        // Obtener el día actual (Luxon: 1=Lunes, 2=Martes, ..., 7=Domingo)
        let now;
        try {
            let timezone = this.config.tz;
            if (!timezone && typeof window !== 'undefined' && window.self_order && window.self_order.config && window.self_order.config.tz) {
                timezone = window.self_order.config.tz;
            }
            now = DateTime.now().setZone(timezone);
        } catch (e) {
            now = DateTime.now();
        }
        const today = now.weekday; // 1=Lunes, 2=Martes, ..., 7=Domingo
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
        if (!todaySchedule) {
            // Si no se encuentra, permitir por defecto
            return true;
        }
        // Normalize types to numbers for robust comparison
        allowedIds = allowedIds.map(id => Number(id));

        // Verificar día de la semana
        const dayAllowed = allowedIds.includes(Number(todaySchedule.id));

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

    async setup(env, { rpc, notification, router, printer, barcode }) {
        await super.setup(...arguments);
        // ensure the self order has the list of weekdays available for UI if needed
        try {
            const schedules = env.session.pos_self_order_data?.pos_product_schedules || [];
            this.pos_product_schedules = schedules;
            this.pos_product_schedules_by_id = {};
            for (const s of schedules) {
                this.pos_product_schedules_by_id[s.id] = s;
            }
            // Set timezone for filtering
            this.config.tz = env.session.pos_self_order_data?.config?.tz;
        } catch (e) {
            // model may not exist if not installed; ignore
        }
    },

    initData() {
        super.initData(...arguments);
        // Setup schedules for filtering
        this.pos_product_schedules = this.pos_product_schedules || [];
        this.pos_product_schedules_by_id = {};
        for (const s of this.pos_product_schedules) {
            this.pos_product_schedules_by_id[s.id] = s;
        }
        // Filter products based on schedule availability
        this.products = this.products.filter(product => this.shouldAddProduct(product));
        // Rebuild grouped products after filtering
        this.productsGroupedByCategory = this.products.reduce((acc, product) => {
            product.pos_categ_ids.map((categ) => {
                acc[categ.id] = acc[categ.id] || [];
                acc[categ.id].push(product);
            });
            return acc;
        }, {});
    },
});
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PnLReport extends Component {
    static template = "custom_pnl_report.PnLReport";

    setup() {
        this.action = useService("action");
        const today = new Date();
        const year = today.getFullYear();

        this.state = useState({
            date_from: `${year}-01-01`,
            date_to: `${year}-12-31`,
            date_label: `A partir del 01/01/${year}`,
            target_move: 'posted',
            comparison: 'none',
            selected_journals: [],
            selected_analytics: [],
            data: null,
            master_data: { journals: [], analytics: [] },
            expanded: {},
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        const result = await rpc("/custom_pnl_report/get_data", {
            date_from: this.state.date_from,
            date_to: this.state.date_to,
            target_move: this.state.target_move,
            comparison: this.state.comparison,
            journal_ids: this.state.selected_journals,
            analytic_account_ids: this.state.selected_analytics,
        });
        this.state.data = result;
        this.state.master_data = {
            journals: result.journals,
            analytics: result.analytics,
        };
        // Re-expand what was expanded or all by default
        result.categories.forEach((cat, index) => {
            if (this.state.expanded[index] === undefined) {
                this.state.expanded[index] = true;
            }
        });
    }

    async onDateChange() {
        if (!this.state.date_from || !this.state.date_to) return;
        this.state.date_label = `Desde ${this.state.date_from} al ${this.state.date_to}`;
        await this.loadData();
    }

    async setDatePreset(preset) {
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth(); // 0-indexed

        if (preset === 'today') {
            const d = today.toISOString().split('T')[0];
            this.state.date_from = d;
            this.state.date_to = d;
            this.state.date_label = "Hoy";
        } else if (preset === 'this_month') {
            const first = new Date(year, month, 1).toISOString().split('T')[0];
            const last = new Date(year, month + 1, 0).toISOString().split('T')[0];
            this.state.date_from = first;
            this.state.date_to = last;
            this.state.date_label = "Este mes";
        } else if (preset === 'this_quarter') {
            const q = Math.floor(month / 3);
            const first = new Date(year, q * 3, 1).toISOString().split('T')[0];
            const last = new Date(year, (q + 1) * 3, 0).toISOString().split('T')[0];
            this.state.date_from = first;
            this.state.date_to = last;
            this.state.date_label = "Este trimestre";
        } else if (preset === 'this_year') {
            this.state.date_from = `${year}-01-01`;
            this.state.date_to = `${year}-12-31`;
            this.state.date_label = "Este año";
        }
        await this.loadData();
    }

    async setComparison(type) {
        this.state.comparison = type;
        await this.loadData();
    }

    async setTargetMove(state) {
        this.state.target_move = state;
        await this.loadData();
    }

    async toggleJournal(id) {
        const idx = this.state.selected_journals.indexOf(id);
        if (idx > -1) {
            this.state.selected_journals.splice(idx, 1);
        } else {
            this.state.selected_journals.push(id);
        }
        await this.loadData();
    }

    async toggleAnalytic(id) {
        const idx = this.state.selected_analytics.indexOf(id);
        if (idx > -1) {
            this.state.selected_analytics.splice(idx, 1);
        } else {
            this.state.selected_analytics.push(id);
        }
        await this.loadData();
    }

    toggleCategory(index) {
        this.state.expanded[index] = !this.state.expanded[index];
    }

    printPdf() {
        return this.action.doAction('custom_pnl_report.action_report_pnl', {
            additional_context: {
                active_ids: [],
            },
            data: {
                form: {
                    date_from: this.state.date_from,
                    date_to: this.state.date_to,
                    target_move: this.state.target_move,
                    comparison: this.state.comparison,
                    journal_ids: this.state.selected_journals,
                    analytic_account_ids: this.state.selected_analytics,
                }
            }
        });
    }
}

registry.category("actions").add("custom_pnl_report.report_pnl_action", PnLReport);

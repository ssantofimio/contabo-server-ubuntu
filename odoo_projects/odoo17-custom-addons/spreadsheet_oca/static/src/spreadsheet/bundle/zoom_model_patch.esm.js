/** @odoo-module **/

import * as spreadsheet from "@odoo/o-spreadsheet";

const originalModel = spreadsheet.Model;
if (originalModel && !originalModel._isZoomPatched) {
    spreadsheet.Model = class extends originalModel {
        constructor() {
            super(...arguments);
            const getters = this.getters;
            const patchGetter = (getterName, clientCoord, rectProp) => {
                const originalGetter = getters[getterName];
                if (!originalGetter) return;
                getters[getterName] = function (coord) {
                    // We only want to patch if the call comes from a mouse/touch event interaction
                    // and if we have a zoom factor active.
                    if (
                        typeof window !== "undefined" &&
                        window.event &&
                        ["mousemove", "mousedown", "mouseup", "click", "touchstart", "touchmove"].includes(window.event.type)
                    ) {
                        const overlay = document.querySelector(".o-grid-overlay");
                        if (overlay) {
                            const rect = overlay.getBoundingClientRect();
                            // Calculate real zoom factor from screen vs CSS pixels
                            const zoomFactor = rect.width / overlay.offsetWidth;
                            if (Math.abs(zoomFactor - 1) > 0.01) {
                                const expectedCoord = window.event[clientCoord] - rect[rectProp];
                                // If the coordinate passed matches the raw mouse coordinate, we scale it.
                                // We use a slightly larger epsilon to handle browser variations.
                                if (Math.abs(coord - expectedCoord) < 2) {
                                    return originalGetter.call(this, coord / zoomFactor);
                                }
                            }
                        }
                    }
                    return originalGetter.call(this, coord);
                };
            };
            patchGetter("getColIndex", "clientX", "left");
            patchGetter("getRowIndex", "clientY", "top");
        }
    };
    spreadsheet.Model._isZoomPatched = true;
}

/** @odoo-module **/

import * as spreadsheet from "@odoo/o-spreadsheet";
import {
  makeDynamicCols,
  makeDynamicRows,
} from "../utils/dynamic_generators.esm";
import { ListDataSource } from "@spreadsheet/list/list_data_source";
import { PivotDataSource } from "@spreadsheet/pivot/pivot_data_source";
import { SpreadsheetControlPanel } from "./spreadsheet_controlpanel.esm";
import { SpreadsheetRenderer } from "./spreadsheet_renderer.esm";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { Component, onMounted, onWillStart, useSubEnv, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

const uuidGenerator = new spreadsheet.helpers.UuidGenerator();
const actionRegistry = registry.category("actions");

export class ActionSpreadsheetOca extends Component {
  setup() {
    this.router = useService("router");
    this.orm = useService("orm");
    this.notification = useService("notification");
    const params = this.props.action.params || this.props.action.context.params;
    this.spreadsheetId = params.spreadsheet_id;
    this.model = params.model || "spreadsheet.spreadsheet";
    this.import_data = params.import_data || {};
    this.state = useState({
      zoom: 100,
    });
    onMounted(() => {
      this.router.pushState({
        spreadsheet_id: this.spreadsheetId,
        model: this.model,
      });
    });
    onWillStart(async () => {
      // We need to load in case the data comes from an XLSX
      this.record =
        spreadsheet.load(
          await this.orm.call(
            this.model,
            "get_spreadsheet_data",
            [[this.spreadsheetId]],
            { context: { bin_size: false } }
          )
        ) || {};
    });
    useSubEnv({
      saveRecord: this.saveRecord.bind(this),
      importData: this.importData.bind(this),
      notifyUser: this.notifyUser.bind(this),
      zoomFactor: () => this.state.zoom / 100,
      zoom: () => this.state.zoom,
      setZoom: (zoom) => (this.state.zoom = zoom),
    });
  }
  notifyUser(notification) {
    this.notification.add(notification.text, {
      type: notification.type,
      sticky: notification.sticky,
    });
  }
  async saveRecord(data) {
    if (this.record.mode === "readonly") {
      return;
    }
    if (this.spreadsheetId) {
      this.orm.call(this.model, "write", [this.spreadsheetId, data]);
    } else {
      this.spreadsheetId = await this.orm.call(this.model, "create", [data]);
      this.router.pushState({ spreadsheet_id: this.spreadsheetId });
    }
  }
  /**
   * Clean SearchParams of conflictive keys.
   *
   * 1. Removed from context pivot conflictive keys.
   * 2. Removed from context graph conflictive keys.
   *
   * @returns {Object}       Formated searchParams.
   */
  cleanSearchParams() {
    const searchParams = this.import_data.searchParams;
    const context = {};
    for (var key of Object.keys(searchParams.context)) {
      if (key.startsWith("pivot_") || key.startsWith("graph_")) {
        continue;
      }
      context[key] = searchParams.context[key];
    }
    return { ...searchParams, context };
  }
  async importDataGraph(spreadsheet_model) {
    var sheetId = spreadsheet_model.getters.getActiveSheetId();
    var y = 0;
    if (this.import_data.new === undefined && this.import_data.new_sheet) {
      sheetId = uuidGenerator.uuidv4();
      spreadsheet_model.dispatch("CREATE_SHEET", {
        sheetId,
        position: spreadsheet_model.getters.getSheetIds().length,
      });
      // We want to open the new sheet
      const sheetIdFrom = spreadsheet_model.getters.getActiveSheetId();
      spreadsheet_model.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom,
        sheetIdTo: sheetId,
      });
    } else if (this.import_data.new === undefined) {
      // TODO: Add a way to detect the last row total height
    }
    const dataSourceId = uuidGenerator.uuidv4();
    const definition = {
      title: this.import_data.name,
      type: "odoo_" + this.import_data.metaData.mode,
      background: "#FFFFFF",
      stacked: this.import_data.metaData.stacked,
      metaData: this.import_data.metaData,
      searchParams: this.cleanSearchParams(),
      dataSourceId: dataSourceId,
      legendPosition: "top",
      verticalAxisPosition: "left",
    };
    spreadsheet_model.dispatch("CREATE_CHART", {
      sheetId,
      id: dataSourceId,
      position: {
        x: 0,
        y: y,
      },
      definition,
    });
  }
  importCreateOrReuseSheet(spreadsheet_model) {
    var sheetId = spreadsheet_model.getters.getActiveSheetId();
    var row = 0;
    if (this.import_data.new === undefined && this.import_data.new_sheet) {
      sheetId = uuidGenerator.uuidv4();
      spreadsheet_model.dispatch("CREATE_SHEET", {
        sheetId,
        position: spreadsheet_model.getters.getSheetIds().length,
      });
      // We want to open the new sheet
      const sheetIdFrom = spreadsheet_model.getters.getActiveSheetId();
      spreadsheet_model.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom,
        sheetIdTo: sheetId,
      });
    } else if (this.import_data.new === undefined) {
      row = spreadsheet_model.getters.getNumberRows(sheetId);
      var maxcols = spreadsheet_model.getters.getNumberCols(sheetId);
      var filled = false;
      while (row >= 0) {
        for (var col = maxcols; col >= 0; col--) {
          if (
            spreadsheet_model.getters.getCell({ sheetId, col, row }) !==
            undefined &&
            spreadsheet_model.getters.getCell({ sheetId, col, row }).content
          ) {
            filled = true;
            break;
          }
        }
        if (filled) {
          break;
        }
        row -= 1;
      }
      row += 1;
    }
    return { sheetId, row };
  }
  async importDataList(spreadsheet_model) {
    var { sheetId, row } = this.importCreateOrReuseSheet(spreadsheet_model);
    const dataSourceId = uuidGenerator.uuidv4();
    var list_info = {
      metaData: {
        resModel: this.import_data.metaData.model,
        columns: this.import_data.metaData.columns.map((column) => column.name),
        fields: this.import_data.metaData.fields,
      },
      searchParams: {
        domain: this.import_data.metaData.domain,
        context: this.import_data.metaData.context,
        orderBy: this.import_data.metaData.orderBy,
      },
      name: this.import_data.name,
    };
    const dataSource = spreadsheet_model.config.custom.dataSources.add(
      dataSourceId,
      ListDataSource,
      list_info
    );
    await dataSource.load();
    spreadsheet_model.dispatch("INSERT_ODOO_LIST", {
      sheetId,
      col: 0,
      row: row,
      id: spreadsheet_model.getters.getNextListId(),
      dataSourceId,
      definition: list_info,
      linesNumber: this.import_data.dyn_number_of_rows,
      columns: this.import_data.metaData.columns,
    });
    const columns = [];
    for (let col = 0; col < this.import_data.metaData.columns.length; col++) {
      columns.push(col);
    }
    spreadsheet_model.dispatch("AUTORESIZE_COLUMNS", {
      sheetId,
      cols: columns,
    });
  }
  async importDataPivot(spreadsheet_model) {
    var { sheetId, row } = this.importCreateOrReuseSheet(spreadsheet_model);
    const dataSourceId = uuidGenerator.uuidv4();
    const colGroupBys = this.import_data.metaData.colGroupBys.concat(
      this.import_data.metaData.expandedColGroupBys
    );
    const rowGroupBys = this.import_data.metaData.rowGroupBys.concat(
      this.import_data.metaData.expandedRowGroupBys
    );
    const pivot_info = {
      metaData: {
        colGroupBys,
        rowGroupBys,
        activeMeasures: this.import_data.metaData.activeMeasures,
        resModel: this.import_data.metaData.resModel,
        sortedColumn: this.import_data.metaData.sortedColumn,
      },
      searchParams: this.cleanSearchParams(),
      name: this.import_data.name,
    };
    const dataSource = spreadsheet_model.config.custom.dataSources.add(
      dataSourceId,
      PivotDataSource,
      pivot_info
    );
    await dataSource.load();
    var { cols, rows, measures } = dataSource.getTableStructure().export();
    if (this.import_data.dyn_number_of_rows) {
      const indentations = rows.map((r) => r.indent);
      const max_indentation = Math.max(...indentations);
      rows = makeDynamicRows(
        rowGroupBys,
        this.import_data.dyn_number_of_rows,
        1,
        max_indentation
      );
    }
    if (this.import_data.dyn_number_of_cols) {
      cols = makeDynamicCols(
        colGroupBys,
        this.import_data.dyn_number_of_cols,
        this.import_data.metaData.activeMeasures
      );
    }
    const table = {
      cols,
      rows,
      measures,
    };
    spreadsheet_model.dispatch("INSERT_PIVOT", {
      sheetId,
      col: 0,
      row: row,
      id: spreadsheet_model.getters.getNextPivotId(),
      table,
      dataSourceId,
      definition: pivot_info,
    });
    const columns = [];
    for (let col = 0; col < table.cols[table.cols.length - 1].length; col++) {
      columns.push(col);
    }
    spreadsheet_model.dispatch("AUTORESIZE_COLUMNS", {
      sheetId,
      cols: columns,
    });
  }
  async importData(spreadsheet_model) {
    if (this.import_data.mode === "pivot") {
      await this.importDataPivot(spreadsheet_model);
    }
    if (this.import_data.mode === "graph") {
      await this.importDataGraph(spreadsheet_model);
    }
    if (this.import_data.mode === "list") {
      await this.importDataList(spreadsheet_model);
    }
  }
}
ActionSpreadsheetOca.template = "spreadsheet_oca.ActionSpreadsheetOca";
ActionSpreadsheetOca.components = {
  SpreadsheetRenderer,
  SpreadsheetControlPanel,
};
// Patches for zoom support
const { Grid, GridOverlay } = spreadsheet.components;
const ColResizer = Grid.components.HeadersOverlay.components.ColResizer;
const RowResizer = Grid.components.HeadersOverlay.components.RowResizer;
const VerticalScrollBar = Grid.components.VerticalScrollBar;
const HorizontalScrollBar = Grid.components.HorizontalScrollBar;

const getScrollbarWidth = (env) => {
  const zoomFactor = env.zoomFactor ? env.zoomFactor() : 1;
  return 15 / zoomFactor;
};

patch(Grid.prototype, {
  get gridOverlayDimensions() {
    const sw = getScrollbarWidth(this.env);
    return `top: 26px; left: 46px; height: calc(100% - ${26 + sw}px); width: calc(100% - ${46 + sw}px);`;
  },
});

patch(GridOverlay.prototype, {
  getCartesianCoordinates(ev) {
    const zoomFactor = this.env.zoomFactor ? this.env.zoomFactor() : 1;
    const x = (ev.clientX - this.gridOverlayRect.x) / zoomFactor;
    const y = (ev.clientY - this.gridOverlayRect.y) / zoomFactor;
    const colIndex = this.env.model.getters.getColIndex(x);
    const rowIndex = this.env.model.getters.getRowIndex(y);
    return [colIndex, rowIndex];
  },
});

patch(ColResizer.prototype, {
  _getEvOffset(ev) {
    const zoomFactor = this.env.zoomFactor ? this.env.zoomFactor() : 1;
    const rect = this.colResizerRef.el.getBoundingClientRect();
    return (ev.clientX - rect.left) / zoomFactor;
  },
  _getClientPosition(ev) {
    const zoomFactor = this.env.zoomFactor ? this.env.zoomFactor() : 1;
    return ev.clientX / zoomFactor;
  },
});

patch(RowResizer.prototype, {
  _getEvOffset(ev) {
    const zoomFactor = this.env.zoomFactor ? this.env.zoomFactor() : 1;
    const rect = this.rowResizerRef.el.getBoundingClientRect();
    return (ev.clientY - rect.top) / zoomFactor;
  },
  _getClientPosition(ev) {
    const zoomFactor = this.env.zoomFactor ? this.env.zoomFactor() : 1;
    return ev.clientY / zoomFactor;
  },
});

patch(VerticalScrollBar.prototype, {
  get position() {
    const sw = getScrollbarWidth(this.env);
    const { y } = this.env.model.getters.getMainViewportRect();
    return {
      top: `${this.props.topOffset + y}px`,
      right: "0px",
      width: `${sw}px`,
      bottom: `0px`,
    };
  },
});

patch(HorizontalScrollBar.prototype, {
  get position() {
    const sw = getScrollbarWidth(this.env);
    const { x } = this.env.model.getters.getMainViewportRect();
    return {
      left: `${this.props.leftOffset + x}px`,
      bottom: "0px",
      height: `${sw}px`,
      right: `0px`,
    };
  },
});

const BottomBarStatistic =
  spreadsheet.Spreadsheet.components.BottomBar.components.BottomBarStatistic;
patch(BottomBarStatistic.prototype, {
  getComposedFnName(fnName, fnValue) {
    const locale = this.env.model.getters.getLocale();
    const sheetId = this.env.model.getters.getActiveSheetId();
    const zones = this.env.model.getters.getSelectedZones();
    // If it's a count function, we don't need to look for a format (it's always a plain number)
    const isCount =
      fnName.includes("Count") ||
      fnName.includes("Contar") ||
      fnName.includes("Núm");

    let format = undefined;
    if (!isCount) {
      // Look for a format in the active selection (limit to first 10 for maximum performance)
      let count = 0;
      const MAX_SEARCH = 10;
      for (const zone of zones) {
        for (let col = zone.left; col <= zone.right; col++) {
          for (let row = zone.top; row <= zone.bottom; row++) {
            const cell = this.env.model.getters.getEvaluatedCell({
              sheetId,
              col,
              row,
            });
            if (cell && cell.format) {
              format = cell.format;
              break;
            }
            if (++count > MAX_SEARCH) break;
          }
          if (format || count > MAX_SEARCH) break;
        }
        if (format || count > MAX_SEARCH) break;
      }
    }

    return (
      fnName +
      ": " +
      (fnValue !== undefined
        ? spreadsheet.helpers.formatValue(fnValue, {
          locale,
          format: isCount ? undefined : format,
        })
        : "__")
    );
  },
});

const BottomBar = spreadsheet.Spreadsheet.components.BottomBar;
patch(BottomBar.prototype, {
  onZoomChanged(ev) {
    this.env.setZoom(parseInt(ev.target.value));
  },
});

actionRegistry.add("action_spreadsheet_oca", ActionSpreadsheetOca, {
  force: true,
});

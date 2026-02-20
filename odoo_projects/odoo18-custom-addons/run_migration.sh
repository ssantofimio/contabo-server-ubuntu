#!/bin/bash

# Script de Migración Odoo 17 -> 18
# Autor: Agentic AI
# Fecha: 2026-02-10

LOG_FILE="/opt/odoo/odoo18/custom-addons/migration.log"
DB_DEST="sarupetrol_mig"
PYTHON_BIN="/opt/odoo/odoo18/odoo-venv/bin/python3"
# Nota: Usamos sudo -u odoo, así que rutas deben ser accesibles por odoo
ODOO_BIN="/opt/odoo/odoo18/odoo-bin"
OPENUPGRADE_DIR="/opt/odoo/odoo18/openupgrade"
# Addons path: Solo OPENUPGRADE_DIR contiene los módulos (framework y scripts)
ADDONS_PATH="/opt/odoo/odoo18/addons,/opt/odoo/odoo18/custom-addons,$OPENUPGRADE_DIR"

echo "=== Iniciando Proceso de Migración (Intento 5 - ruta corregida) ===" | tee -a $LOG_FILE
date | tee -a $LOG_FILE

# 3. Ejecutar Migración
echo "Ejecutando OpenUpgrade..." | tee -a $LOG_FILE
# Nota: OpenUpgrade necesita cargar openupgrade_framework y openupgrade_scripts
CMD="sudo -u odoo $PYTHON_BIN $ODOO_BIN -d $DB_DEST -u all --stop-after-init --addons-path=$ADDONS_PATH --load=base,web,openupgrade_framework"

echo "Comando: $CMD" | tee -a $LOG_FILE

$CMD 2>&1 | tee -a $LOG_FILE

echo "=== Migración Finalizada ===" | tee -a $LOG_FILE
date | tee -a $LOG_FILE

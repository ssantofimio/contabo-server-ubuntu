-- Migration: drop pos_weekday_mask columns introduced previously.
-- WARNING: Run these commands on a backup / maintenance window. Test before applying.

ALTER TABLE product_product DROP COLUMN IF EXISTS pos_weekday_mask;
ALTER TABLE product_template DROP COLUMN IF EXISTS pos_weekday_mask;

-- After dropping, you might want to refresh Odoo models and upgrade the module.
-- Example (from server):
-- ./odoo-bin -d <db> -u pos_product_schedule --stop-after-init

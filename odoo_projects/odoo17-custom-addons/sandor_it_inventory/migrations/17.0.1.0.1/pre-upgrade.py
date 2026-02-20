def migrate(cr, version):
    """ Rename model names in ir_model_data and tables to avoid KeyError during upgrade """
    # 1. Rename tables if they exist
    for old_table, new_table in [
        ('dashboard_block', 'it_dashboard_block'),
        ('dashboard_menu', 'it_dashboard_menu'),
        ('dashboard_theme', 'it_dashboard_theme')
    ]:
        cr.execute(f"SELECT count(*) FROM information_schema.tables WHERE table_name = '{old_table}'")
        if cr.fetchone()[0] > 0:
            cr.execute(f"ALTER TABLE {old_table} RENAME TO {new_table}")

    # 2. Update ir_model_data
    cr.execute("""
        UPDATE ir_model_data 
        SET model = 'it_dashboard.block' 
        WHERE module = 'sandor_it_inventory' AND model = 'dashboard.block'
    """)
    cr.execute("""
        UPDATE ir_model_data 
        SET model = 'it_dashboard.menu' 
        WHERE module = 'sandor_it_inventory' AND model = 'dashboard.menu'
    """)
    cr.execute("""
        UPDATE ir_model_data 
        SET model = 'it_dashboard.theme' 
        WHERE module = 'sandor_it_inventory' AND model = 'dashboard.theme'
    """)

    # 3. Cleanup orphaned Synconics menus and actions
    cr.execute("""
        DELETE FROM ir_ui_menu 
        WHERE action LIKE 'ir.actions.client,%' 
        AND action IN (
            SELECT 'ir.actions.client,' || id FROM ir_act_client WHERE tag = 'dashboard_amcharts'
        )
    """)
    cr.execute("DELETE FROM ir_act_client WHERE tag = 'dashboard_amcharts'")

    # 4. Remove duplicate "Asignación TIC" menus created by Synconics
    cr.execute("""
        DELETE FROM ir_ui_menu 
        WHERE name = 'Asignación TIC' 
        AND id NOT IN (
            SELECT res_id FROM ir_model_data 
            WHERE module = 'sandor_it_inventory' 
            AND name = 'menu_it_assignment'
        )
    """)

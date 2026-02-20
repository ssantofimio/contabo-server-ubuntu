import sqlite3
import os

class MappingDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS id_mappings (
                model_name TEXT,
                source_id INTEGER,
                dest_id INTEGER,
                PRIMARY KEY (model_name, source_id)
            )
        ''')
        self.conn.commit()

    def add_mapping(self, model_name, source_id, dest_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO id_mappings (model_name, source_id, dest_id)
            VALUES (?, ?, ?)
        ''', (model_name, source_id, dest_id))
        self.conn.commit()

    def get_dest_id(self, model_name, source_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT dest_id FROM id_mappings WHERE model_name = ? AND source_id = ?
        ''', (model_name, source_id))
        result = cursor.fetchone()
        return result[0] if result else None

    def close(self):
        self.conn.close()

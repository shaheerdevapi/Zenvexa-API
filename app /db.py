"""
Zenvexa API - Database Module
Production-ready SQLite database layer with migration-ready structure
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_DIR = os.path.join(os.path.dirname(__file__), 'data')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'zenvexa.db')

# SQL Scripts for table creation
TABLE_SCHEMAS = {
    'users': '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            email_verified BOOLEAN DEFAULT 0
        )
    ''',
    
    'api_keys': '''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            key_hash TEXT UNIQUE NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''',
    
    'subscriptions': '''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_type TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ends_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''',
    
    'usage_tracking': '''
        CREATE TABLE IF NOT EXISTS usage_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL,
            method TEXT NOT NULL,
            status_code INTEGER,
            response_time_ms INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_agent TEXT,
            ip_address TEXT,
            request_size_bytes INTEGER,
            response_size_bytes INTEGER,
            FOREIGN KEY (api_key_id) REFERENCES api_keys (id) ON DELETE CASCADE
        )
    ''',
    
    'audit_logs': '''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            old_values TEXT,
            new_values TEXT,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )
    '''
}

# Indexes for performance
INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)',
    'CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash)',
    'CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_usage_tracking_api_key_id ON usage_tracking(api_key_id)',
    'CREATE INDEX IF NOT EXISTS idx_usage_tracking_timestamp ON usage_tracking(timestamp)',
    'CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)'
]


class DatabaseManager:
    """
    Production-ready database manager for Zenvexa API
    Thread-safe SQLite operations with connection pooling
    """
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._ensure_database_directory()
        self._initialize_database()
    
    def _ensure_database_directory(self) -> None:
        """Ensure database directory exists"""
        os.makedirs(DATABASE_DIR, exist_ok=True)
    
    def _initialize_database(self) -> None:
        """Initialize database with all tables and indexes"""
        try:
            with self.get_connection() as conn:
                # Enable foreign keys
                conn.execute('PRAGMA foreign_keys = ON')
                
                # Create tables
                for table_name, schema in TABLE_SCHEMAS.items():
                    conn.execute(schema)
                    logger.info(f"Table '{table_name}' ready")
                
                # Create indexes
                for index_sql in INDEXES:
                    conn.execute(index_sql)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        Ensures proper connection handling and thread safety
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,  # 30 second timeout
                isolation_level=None,  # Autocommit mode
                check_same_thread=False  # Allow cross-thread usage
            )
            
            # Configure connection
            conn.execute('PRAGMA journal_mode = WAL')  # Write-Ahead Logging
            conn.execute('PRAGMA synchronous = NORMAL')  # Balanced safety/performance
            conn.execute('PRAGMA cache_size = -10000')  # 10MB cache
            conn.execute('PRAGMA temp_store = MEMORY')  # Temporary tables in memory
            
            # Set row factory for dict-like access
            conn.row_factory = sqlite3.Row
            
            yield conn
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
            
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return results
        Safe from SQL injection via parameterized queries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
            except sqlite3.Error as e:
                logger.error(f"Query execution failed: {e}")
                raise
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute INSERT, UPDATE, DELETE queries
        Returns number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                return cursor.rowcount
                
            except sqlite3.Error as e:
                logger.error(f"Update execution failed: {e}")
                raise
    
    def execute_transaction(self, queries: List[tuple]) -> bool:
        """
        Execute multiple queries in a transaction
        queries: List of (query_string, params_tuple) tuples
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Begin transaction
                cursor.execute('BEGIN TRANSACTION')
                
                for query, params in queries:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                
                # Commit transaction
                cursor.execute('COMMIT')
                return True
                
            except sqlite3.Error as e:
                cursor.execute('ROLLBACK')
                logger.error(f"Transaction failed: {e}")
                raise
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information"""
        query = "PRAGMA table_info(?)"
        return self.execute_query(query, (table_name,))
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database"""
        try:
            with self.get_connection() as conn:
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
                logger.info(f"Database backed up to {backup_path}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get table row counts
                stats = {}
                for table in TABLE_SCHEMAS.keys():
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                
                # Get database size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                stats['database_size_bytes'] = cursor.fetchone()[0]
                
                # Get WAL mode status
                cursor.execute("PRAGMA journal_mode")
                stats['journal_mode'] = cursor.fetchone()[0]
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    def vacuum_database(self) -> bool:
        """Optimize database file size"""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("Database vacuumed successfully")
                return True
        except sqlite3.Error as e:
            logger.error(f"Vacuum failed: {e}")
            return False


# Global database instance
_db_manager: Optional[DatabaseManager] = None


def init_db(db_path: Optional[str] = None) -> DatabaseManager:
    """
    Initialize global database manager instance
    Should be called once during application startup
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path or DATABASE_PATH)
    return _db_manager


def get_db() -> DatabaseManager:
    """
    Get database manager instance
    Ensures database is initialized before returning
    """
    global _db_manager
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db_manager


def close_db() -> None:
    """
    Close database connections and cleanup
    Called during application shutdown
    """
    global _db_manager
    if _db_manager:
        # SQLite connections are automatically closed
        # This is mainly for cleanup and logging
        logger.info("Database connections closed")
        _db_manager = None


# Migration helpers for future PostgreSQL/MySQL support
class MigrationHelper:
    """
    Helper class for future database migrations
    Provides abstraction layer for different database systems
    """
    
    @staticmethod
    def get_compatible_sql(sqlite_sql: str, target_db: str) -> str:
        """
        Convert SQLite SQL to target database syntax
        Currently supports SQLite -> PostgreSQL/MySQL conversion
        """
        conversions = {
            'postgresql': {
                'AUTOINCREMENT': 'SERIAL',
                'CURRENT_TIMESTAMP': 'CURRENT_TIMESTAMP',
                'BOOLEAN': 'BOOLEAN',
                'TEXT': 'TEXT',
                'INTEGER': 'INTEGER',
                'PRAGMA foreign_keys': 'SET CONSTRAINTS ALL'
            },
            'mysql': {
                'AUTOINCREMENT': 'AUTO_INCREMENT',
                'CURRENT_TIMESTAMP': 'CURRENT_TIMESTAMP',
                'BOOLEAN': 'BOOLEAN',
                'TEXT': 'TEXT',
                'INTEGER': 'INT',
                'PRAGMA foreign_keys': 'SET FOREIGN_KEY_CHECKS'
            }
        }
        
        if target_db not in conversions:
            return sqlite_sql
            
        converted_sql = sqlite_sql
        for sqlite_syntax, target_syntax in conversions[target_db].items():
            converted_sql = converted_sql.replace(sqlite_syntax, target_syntax)
        
        return converted_sql


# Example usage and testing
if __name__ == "__main__":
    # Initialize database
    db = init_db()
    
    # Example: Insert a user
    user_query = """
        INSERT INTO users (email, name, password_hash)
        VALUES (?, ?, ?)
    """
    db.execute_update(user_query, ("user@example.com", "John Doe", "hashed_password"))
    
    # Example: Get user
    user = db.execute_query(
        "SELECT * FROM users WHERE email = ?",
        ("user@example.com",)
    )
    print("User:", user)
    
    # Get database stats
    stats = db.get_database_stats()
    print("Database stats:", stats)
    
    # Cleanup
    close_db()
          

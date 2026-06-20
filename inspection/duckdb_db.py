import duckdb
from django.conf import settings
import threading
import time
from datetime import datetime, timedelta

_db_lock = threading.RLock()
_connection = None
_initialized = False

_CONNECT_MAX_RETRIES = 10
_CONNECT_RETRY_INTERVAL = 0.5


def _safe_connect():
    last_error = None
    for i in range(_CONNECT_MAX_RETRIES):
        try:
            conn = duckdb.connect(str(settings.DUCKDB_PATH))
            return conn
        except (duckdb.IOException, OSError) as e:
            last_error = e
            time.sleep(_CONNECT_RETRY_INTERVAL * (i + 1))
    raise RuntimeError(f"无法连接到 DuckDB 数据库（文件可能被占用）: {last_error}")


def get_connection():
    global _connection
    if _connection is None:
        _connection = _safe_connect()
        ensure_duckdb_initialized()
    return _connection


def ensure_duckdb_initialized():
    global _initialized
    if _initialized:
        return
    with _db_lock:
        if _initialized:
            return
        _init_tables()
        _migrate_tables()
        _initialized = True


def _column_exists(table_name, column_name):
    conn = get_connection()
    try:
        result = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = [row[1] for row in result]
        return column_name in columns
    except Exception:
        return False


def _add_column_if_not_exists(table_name, column_def):
    conn = get_connection()
    column_name = column_def.strip().split()[0]
    if not _column_exists(table_name, column_name):
        try:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
        except Exception:
            pass


def _migrate_tables():
    global _connection
    if _connection is None:
        _connection = _safe_connect()
    conn = _connection

    try:
        conn.execute("CREATE SEQUENCE IF NOT EXISTS fault_progress_log_seq START 1")
    except Exception:
        pass

    _add_column_if_not_exists("fault_records", "processing_status VARCHAR DEFAULT 'pending'")
    _add_column_if_not_exists("fault_records", "assigned_to_id INTEGER")
    _add_column_if_not_exists("fault_records", "assigned_to_name VARCHAR")
    _add_column_if_not_exists("fault_records", "latest_progress VARCHAR")
    _add_column_if_not_exists("fault_records", "temp_solution_updated VARCHAR")
    _add_column_if_not_exists("fault_records", "reviewer_id INTEGER")
    _add_column_if_not_exists("fault_records", "reviewer_name VARCHAR")
    _add_column_if_not_exists("fault_records", "review_result VARCHAR")
    _add_column_if_not_exists("fault_records", "final_conclusion VARCHAR")
    _add_column_if_not_exists("fault_records", "reviewed_at TIMESTAMP")
    _add_column_if_not_exists("fault_records", "closed_by_id INTEGER")
    _add_column_if_not_exists("fault_records", "closed_by_name VARCHAR")
    _add_column_if_not_exists("fault_records", "closed_at TIMESTAMP")
    _add_column_if_not_exists("fault_records", "is_closed BOOLEAN DEFAULT FALSE")
    _add_column_if_not_exists("fault_records", "closed_loop BOOLEAN DEFAULT FALSE")
    _add_column_if_not_exists("fault_records", "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fault_progress_logs (
                id INTEGER PRIMARY KEY DEFAULT nextval('fault_progress_log_seq'),
                fault_id INTEGER NOT NULL,
                operator_id INTEGER,
                operator_name VARCHAR,
                operator_role VARCHAR,
                action_type VARCHAR NOT NULL,
                action_detail VARCHAR,
                from_status VARCHAR,
                to_status VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except Exception:
        pass


def next_val(seq_name):
    conn = get_connection()
    with _db_lock:
        result = conn.execute(f"SELECT nextval('{seq_name}')").fetchone()
        return result[0]


def _init_tables():
    global _connection
    if _connection is None:
        _connection = _safe_connect()
    conn = _connection
    
    conn.execute("CREATE SEQUENCE IF NOT EXISTS hall_seq START 1")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS halls (
            id INTEGER PRIMARY KEY DEFAULT nextval('hall_seq'),
            hall_code VARCHAR NOT NULL,
            hall_name VARCHAR,
            projector_model VARCHAR NOT NULL,
            server_code VARCHAR NOT NULL,
            responsible_person VARCHAR,
            review_time_limit INTEGER DEFAULT 24,
            status VARCHAR DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("CREATE SEQUENCE IF NOT EXISTS template_seq START 1")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inspection_templates (
            id INTEGER PRIMARY KEY DEFAULT nextval('template_seq'),
            template_name VARCHAR NOT NULL,
            template_type VARCHAR NOT NULL,
            check_items VARCHAR,
            brightness_min INTEGER DEFAULT 80,
            sound_channels VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("CREATE SEQUENCE IF NOT EXISTS inspection_order_seq START 1")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inspection_orders (
            id INTEGER PRIMARY KEY DEFAULT nextval('inspection_order_seq'),
            hall_id INTEGER NOT NULL,
            hall_code VARCHAR NOT NULL,
            session_no VARCHAR NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'pending_check',
            template_id INTEGER,
            projectionist_id INTEGER,
            projectionist_name VARCHAR,
            reviewer_id INTEGER,
            reviewer_name VARCHAR,
            self_check_result BOOLEAN,
            brightness INTEGER,
            sound_channels VARCHAR,
            film_source_verified BOOLEAN,
            cooling_status VARCHAR,
            fault_description VARCHAR,
            fault_level VARCHAR,
            temp_solution VARCHAR,
            recheck_result BOOLEAN,
            problem_cause VARCHAR,
            final_conclusion VARCHAR,
            submitted_at TIMESTAMP,
            review_deadline TIMESTAMP,
            reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("CREATE SEQUENCE IF NOT EXISTS fault_record_seq START 1")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fault_records (
            id INTEGER PRIMARY KEY DEFAULT nextval('fault_record_seq'),
            order_id INTEGER NOT NULL,
            hall_id INTEGER NOT NULL,
            projector_model VARCHAR,
            fault_type VARCHAR,
            fault_level VARCHAR,
            description VARCHAR,
            solution VARCHAR,
            handler_id INTEGER,
            handler_name VARCHAR,
            processing_status VARCHAR DEFAULT 'pending',
            assigned_to_id INTEGER,
            assigned_to_name VARCHAR,
            latest_progress VARCHAR,
            temp_solution_updated VARCHAR,
            reviewer_id INTEGER,
            reviewer_name VARCHAR,
            review_result VARCHAR,
            final_conclusion VARCHAR,
            reviewed_at TIMESTAMP,
            closed_by_id INTEGER,
            closed_by_name VARCHAR,
            closed_at TIMESTAMP,
            is_closed BOOLEAN DEFAULT FALSE,
            closed_loop BOOLEAN DEFAULT FALSE,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("CREATE SEQUENCE IF NOT EXISTS fault_progress_log_seq START 1")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fault_progress_logs (
            id INTEGER PRIMARY KEY DEFAULT nextval('fault_progress_log_seq'),
            fault_id INTEGER NOT NULL,
            operator_id INTEGER,
            operator_name VARCHAR,
            operator_role VARCHAR,
            action_type VARCHAR NOT NULL,
            action_detail VARCHAR,
            from_status VARCHAR,
            to_status VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def execute_query(sql, params=None):
    conn = get_connection()
    with _db_lock:
        if params:
            return conn.execute(sql, params).fetchall()
        return conn.execute(sql).fetchall()


def execute_update(sql, params=None):
    conn = get_connection()
    with _db_lock:
        if params:
            conn.execute(sql, params)
        else:
            conn.execute(sql)
        return True


def fetch_one(sql, params=None):
    result = execute_query(sql, params)
    return result[0] if result else None


def fetch_all(sql, params=None):
    return execute_query(sql, params)


def dict_fetch_one(sql, params=None):
    conn = get_connection()
    with _db_lock:
        if params:
            result = conn.execute(sql, params).fetchone()
            description = conn.description
        else:
            result = conn.execute(sql).fetchone()
            description = conn.description
    if not result:
        return None
    columns = [desc[0] for desc in description]
    return dict(zip(columns, result))


def dict_fetch_all(sql, params=None):
    conn = get_connection()
    with _db_lock:
        if params:
            results = conn.execute(sql, params).fetchall()
            description = conn.description
        else:
            results = conn.execute(sql).fetchall()
            description = conn.description
    columns = [desc[0] for desc in description]
    return [dict(zip(columns, row)) for row in results]


def insert_returning_id(sql, params=None):
    conn = get_connection()
    with _db_lock:
        if params:
            result = conn.execute(sql, params).fetchone()
        else:
            result = conn.execute(sql).fetchone()
    return result[0] if result else None

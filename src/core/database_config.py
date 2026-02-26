import os
import sqlite3
import shutil
import logging

logger = logging.getLogger(__name__)

def _sqlite_has_tables(db_path, required_tables, app_base_dir):
    """تحقق سريع أن ملف SQLite يحتوي الجداول المطلوبة."""
    try:
        normalized_path = db_path
        if not os.path.isabs(normalized_path):
            normalized_path = os.path.abspath(os.path.join(app_base_dir, normalized_path))
        conn = sqlite3.connect(normalized_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        return all(table in existing_tables for table in required_tables)
    except Exception:
        return False

def _sqlite_uri_to_path(sqlite_uri, app_base_dir):
    """تحويل URI من شكل sqlite:///path.db إلى مسار ملف محلي."""
    if not sqlite_uri.startswith("sqlite:///"):
        return None
    path = sqlite_uri.replace("sqlite:///", "", 1).replace('/', os.sep)
    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(app_base_dir, path))
    return path

def _build_sqlite_uri(file_path, app_base_dir):
    absolute_path = file_path
    if not os.path.isabs(absolute_path):
        absolute_path = os.path.abspath(os.path.join(app_base_dir, absolute_path))
    return f"sqlite:///{absolute_path.replace(os.sep, '/')}"

def _try_repair_sqlite(target_db_path, source_db_path):
    """نسخ قاعدة SQLite صالحة إلى المسار المستهدف عند الحاجة."""
    try:
        if not target_db_path or not source_db_path:
            return False

        if not os.path.exists(source_db_path):
            return False

        target_dir = os.path.dirname(target_db_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        shutil.copy2(source_db_path, target_db_path)
        return True
    except Exception as copy_error:
        logger.warning(f"SQLite repair copy failed: {copy_error}")
        return False

def init_db_config(app):
    """إعداد قاعدة البيانات وخيارات المحرك."""
    database_url = os.environ.get("DATABASE_URL")
    app_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # If no DATABASE_URL is provided, use SQLite as fallback
    if not database_url:
        required_tables = ['employee', 'user']
        candidate_sqlite_files = [
            os.path.join('instance', 'nuzum_local.db'),
            os.path.join('database', 'nuzum.db'),
            os.path.join('instance', 'nuzm_dev.db'),
        ]

        selected_sqlite = None
        for sqlite_file in candidate_sqlite_files:
            if os.path.exists(sqlite_file) and _sqlite_has_tables(sqlite_file, required_tables, app_base_dir):
                selected_sqlite = sqlite_file
                break

        if not selected_sqlite:
            for sqlite_file in candidate_sqlite_files:
                if os.path.exists(sqlite_file):
                    selected_sqlite = sqlite_file
                    break

        if not selected_sqlite:
            os.makedirs('database', exist_ok=True)
            selected_sqlite = os.path.join('database', 'nuzum.db')

        database_url = _build_sqlite_uri(selected_sqlite, app_base_dir)
        logger.info(f"Using SQLite database: {selected_sqlite}")
    else:
        logger.info(f"Using database: {database_url.split('@')[0]}@***")

        # حماية إضافية: إذا كان DATABASE_URL يشير إلى SQLite غير صالح، نعيد التوجيه لملف SQLite صالح.
        if database_url.startswith("sqlite:///"):
            required_tables = ['employee', 'user']
            configured_sqlite_path = _sqlite_uri_to_path(database_url, app_base_dir)

            if configured_sqlite_path and not _sqlite_has_tables(configured_sqlite_path, required_tables, app_base_dir):
                instance_db_path = os.path.join('instance', 'nuzum_local.db')
                if _sqlite_has_tables(instance_db_path, required_tables, app_base_dir):
                    if _try_repair_sqlite(configured_sqlite_path, instance_db_path):
                        database_url = _build_sqlite_uri(configured_sqlite_path, app_base_dir)
                        logger.warning(
                            f"Configured SQLite database '{configured_sqlite_path}' missing required tables; "
                            f"synced from '{instance_db_path}'"
                        )
                    else:
                        logger.warning(
                            f"Configured SQLite database '{configured_sqlite_path}' missing required tables; "
                            "sync attempt failed"
                        )

                fallback_candidates = [
                    configured_sqlite_path,
                    os.path.join('instance', 'nuzum_local.db'),
                    os.path.join('database', 'nuzum.db'),
                    os.path.join('instance', 'nuzm_dev.db'),
                ]

                repaired_sqlite = None
                for sqlite_file in fallback_candidates:
                    if os.path.exists(sqlite_file) and _sqlite_has_tables(sqlite_file, required_tables, app_base_dir):
                        repaired_sqlite = sqlite_file
                        break

                if repaired_sqlite:
                    database_url = _build_sqlite_uri(repaired_sqlite, app_base_dir)
                    logger.warning(
                        f"Configured SQLite database '{configured_sqlite_path}' missing required tables; "
                        f"switched to '{repaired_sqlite}'"
                    )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    # Configure engine options based on database type
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        # PostgreSQL optimized settings
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_timeout": 30,
            "pool_size": 10,
            "max_overflow": 5,
            "pool_reset_on_return": "rollback",
            "connect_args": {
                "connect_timeout": 10,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            }
        }
    elif database_url.startswith("mysql://"):
        # MySQL optimized settings
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_timeout": 30,
            "pool_size": 5,
            "max_overflow": 3,
            "connect_args": {
                "connect_timeout": 10,
                "charset": "utf8mb4",
            }
        }
    else:
        # SQLite settings (minimal connection pooling)
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_timeout": 20,
            "pool_recycle": -1,
            "pool_pre_ping": True,
            "connect_args": {
                "check_same_thread": False,
                "timeout": 20,
            }
        }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Add execution options only for PostgreSQL/MySQL
    if not database_url.startswith("sqlite"):
        if "execution_options" not in app.config["SQLALCHEMY_ENGINE_OPTIONS"]:
            app.config["SQLALCHEMY_ENGINE_OPTIONS"]["execution_options"] = {}
        app.config["SQLALCHEMY_ENGINE_OPTIONS"]["execution_options"]["isolation_level"] = "READ COMMITTED"

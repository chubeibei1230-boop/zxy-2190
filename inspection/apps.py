import os
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class InspectionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inspection'

    def ready(self):
        import sys
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            return
        try:
            from inspection.duckdb_db import ensure_duckdb_initialized
            ensure_duckdb_initialized()
        except Exception as e:
            logger.warning(f"DuckDB 初始化延迟到首次请求时执行: {e}")

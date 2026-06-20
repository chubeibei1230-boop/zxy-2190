import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema_inspection.settings')
django.setup()

from inspection.duckdb_db import execute_update, dict_fetch_one, get_connection

print("=== 测试 UPDATE 语句 ===")

try:
    execute_update(
        """UPDATE inspection_orders SET 
           status = ?, self_check_result = ?, brightness = ?, sound_channels = ?,
           film_source_verified = ?, cooling_status = ?, submitted_at = CURRENT_TIMESTAMP,
           updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        ['pending_review', True, 85, 'left,right,center', True, 'normal', 1]
    )
    print("UPDATE 成功！")
    
    order = dict_fetch_one("SELECT * FROM inspection_orders WHERE id = 1")
    print(f"更新后状态: {order['status']}")
    print(f"亮度: {order['brightness']}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

print("\n=== 测试 INSERT fault_records ===")
try:
    execute_update(
        """INSERT INTO fault_records (order_id, hall_id, projector_model, fault_type, fault_level, description, solution)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [1, 1, 'Barco DP2K-20C', 'test', 'high', 'test fault', 'test solution']
    )
    print("INSERT 成功！")
except Exception as e:
    print(f"INSERT 失败: {e}")

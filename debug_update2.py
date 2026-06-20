import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema_inspection.settings')
django.setup()

from inspection.duckdb_db import execute_update, dict_fetch_one, execute_query, get_connection

print("=== 测试简单 UPDATE ===")

# 测试1：只更新一个非索引字段
try:
    execute_update("UPDATE inspection_orders SET brightness = ? WHERE id = ?", [90, 1])
    print("测试1 - 更新 brightness: 成功！")
    order = dict_fetch_one("SELECT id, brightness, status FROM inspection_orders WHERE id = 1")
    print(f"  brightness = {order['brightness']}")
except Exception as e:
    print(f"测试1 - 更新 brightness: 失败: {e}")

# 测试2：更新 status 字段（有索引的字段）
try:
    execute_update("UPDATE inspection_orders SET status = ? WHERE id = ?", ['checking', 1])
    print("测试2 - 更新 status: 成功！")
    order = dict_fetch_one("SELECT id, status FROM inspection_orders WHERE id = 1")
    print(f"  status = {order['status']}")
except Exception as e:
    print(f"测试2 - 更新 status: 失败: {e}")

# 测试3：更新多个字段
try:
    execute_update(
        "UPDATE inspection_orders SET status = ?, brightness = ?, self_check_result = ? WHERE id = ?",
        ['pending_review', 85, True, 1]
    )
    print("测试3 - 更新多个字段: 成功！")
    order = dict_fetch_one("SELECT id, status, brightness, self_check_result FROM inspection_orders WHERE id = 1")
    print(f"  status={order['status']}, brightness={order['brightness']}, result={order['self_check_result']}")
except Exception as e:
    print(f"测试3 - 更新多个字段: 失败: {e}")

print("\n=== 检查索引 ===")
indexes = execute_query("SELECT index_name, table_name FROM duckdb_indexes() WHERE table_name = 'inspection_orders'")
for idx in indexes:
    print(f"  {idx[0]} on {idx[1]}")

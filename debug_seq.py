import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema_inspection.settings')
django.setup()

from inspection.duckdb_db import dict_fetch_all, dict_fetch_one, next_val

print("=== 检查 inspection_orders 表 ===")
orders = dict_fetch_all("SELECT * FROM inspection_orders ORDER BY id")
print(f"巡检单数量: {len(orders)}")
for o in orders:
    print(f"  id={o['id']}, hall={o['hall_code']}, session={o['session_no']}, status={o['status']}")

print("\n=== 检查序列 ===")
try:
    seqs = dict_fetch_all("SELECT sequence_name, start_value, last_value, min_value, max_value FROM duckdb_sequences()")
    for s in seqs:
        print(f"  {s['sequence_name']}: start={s['start_value']}, last={s['last_value']}")
except Exception as e:
    print(f"  查询序列失败: {e}")

print("\n=== 测试 next_val ===")
print(f"  inspection_order_seq next: {next_val('inspection_order_seq')}")
print(f"  inspection_order_seq next: {next_val('inspection_order_seq')}")
print(f"  hall_seq next: {next_val('hall_seq')}")

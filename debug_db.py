import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema_inspection.settings')
django.setup()

from inspection.duckdb_db import dict_fetch_all, dict_fetch_one

print("=== 检查 halls 表 ===")
halls = dict_fetch_all("SELECT * FROM halls")
print(f"影厅数量: {len(halls)}")
for h in halls:
    print(f"  id={h['id']}, code={h['hall_code']}, name={h['hall_name']}")

print("\n=== 检查 inspection_templates 表 ===")
templates = dict_fetch_all("SELECT * FROM inspection_templates")
print(f"模板数量: {len(templates)}")
for t in templates:
    print(f"  id={t['id']}, name={t['template_name']}")

print("\n=== 检查 inspection_orders 表 ===")
orders = dict_fetch_all("SELECT * FROM inspection_orders")
print(f"巡检单数量: {len(orders)}")
for o in orders:
    print(f"  id={o['id']}, hall={o['hall_code']}, session={o['session_no']}, status={o['status']}")

print("\n=== 检查 fault_records 表 ===")
faults = dict_fetch_all("SELECT * FROM fault_records")
print(f"故障记录数量: {len(faults)}")
for f in faults:
    print(f"  id={f['id']}, order_id={f['order_id']}, hall_id={f['hall_id']}")

print("\n=== 检查序列 ===")
seqs = dict_fetch_all("SELECT sequence_name, start_value, last_value FROM duckdb_sequences()")
for s in seqs:
    print(f"  {s['sequence_name']}: start={s['start_value']}, last={s['last_value']}")

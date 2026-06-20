import duckdb

conn = duckdb.connect('e:\\solocode\\0620\\zxy-2190-1\\cinema_inspection.duckdb')

print("=== 所有表 ===")
tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
for t in tables:
    print(f"  {t[0]}")

print("\n=== 所有序列 ===")
seqs = conn.execute("SELECT sequence_name, start_value, last_value FROM duckdb_sequences()").fetchall()
for s in seqs:
    print(f"  {s[0]}: start={s[1]}, last={s[2]}")

print("\n=== inspection_orders 数据 ===")
orders = conn.execute("SELECT id, hall_code, session_no, status, created_at FROM inspection_orders").fetchall()
for o in orders:
    print(f"  id={o[0]}, hall={o[1]}, session={o[2]}, status={o[3]}, created={o[4]}")

print("\n=== 测试 nextval ===")
for i in range(3):
    val = conn.execute("SELECT nextval('inspection_order_seq')").fetchone()[0]
    print(f"  nextval: {val}")

print("\n=== 再查序列 ===")
seqs = conn.execute("SELECT sequence_name, start_value, last_value FROM duckdb_sequences()").fetchall()
for s in seqs:
    print(f"  {s[0]}: start={s[1]}, last={s[2]}")

conn.close()

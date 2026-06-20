import duckdb
import tempfile
import os

db_path = os.path.join(tempfile.gettempdir(), 'test_duckdb_update2.duckdb')
if os.path.exists(db_path):
    os.remove(db_path)

conn = duckdb.connect(db_path)

print("=== 测试A：有索引，主键手动赋值 ===")
conn.execute("""
    CREATE TABLE testa (
        id INTEGER PRIMARY KEY,
        status VARCHAR,
        value INTEGER
    )
""")
conn.execute("CREATE INDEX idxa_status ON testa(status)")
conn.execute("INSERT INTO testa (id, status, value) VALUES (1, 'pending', 100)")
try:
    conn.execute("UPDATE testa SET status = 'done', value = 200 WHERE id = 1")
    result = conn.execute("SELECT * FROM testa WHERE id = 1").fetchone()
    print(f"UPDATE 成功: status = {result[1]}, value = {result[2]}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

print("\n=== 测试B：多索引，主键手动赋值 ===")
conn.execute("""
    CREATE TABLE testb (
        id INTEGER PRIMARY KEY,
        hall_id INTEGER NOT NULL,
        session_no VARCHAR NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'pending',
        brightness INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.execute("CREATE INDEX idxb_hall_session ON testb(hall_id, session_no, status)")
conn.execute("CREATE INDEX idxb_status ON testb(status)")
conn.execute("CREATE INDEX idxb_created ON testb(created_at)")
conn.execute("INSERT INTO testb (id, hall_id, session_no, status, brightness) VALUES (1, 1, 'S001', 'pending', 80)")
try:
    conn.execute("UPDATE testb SET status = 'done', brightness = 90 WHERE id = 1")
    result = conn.execute("SELECT * FROM testb WHERE id = 1").fetchone()
    print(f"UPDATE 成功: status = {result[3]}, brightness = {result[4]}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

print("\n=== 测试C：多索引，仅更新非索引字段 ===")
try:
    conn.execute("UPDATE testb SET brightness = 95 WHERE id = 1")
    result = conn.execute("SELECT * FROM testb WHERE id = 1").fetchone()
    print(f"UPDATE 成功: brightness = {result[4]}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

print("\n=== 测试D：多索引，仅更新索引字段 ===")
try:
    conn.execute("UPDATE testb SET status = 'checking' WHERE id = 1")
    result = conn.execute("SELECT * FROM testb WHERE id = 1").fetchone()
    print(f"UPDATE 成功: status = {result[3]}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

print("\n=== 测试E：无索引，多字段更新 ===")
conn.execute("""
    CREATE TABLE teste (
        id INTEGER PRIMARY KEY,
        status VARCHAR,
        brightness INTEGER,
        cooling VARCHAR
    )
""")
conn.execute("INSERT INTO teste (id, status, brightness, cooling) VALUES (1, 'pending', 80, 'normal')")
try:
    conn.execute("UPDATE teste SET status = 'done', brightness = 90, cooling = 'high' WHERE id = 1")
    result = conn.execute("SELECT * FROM teste WHERE id = 1").fetchone()
    print(f"UPDATE 成功: status = {result[1]}, brightness = {result[2]}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

conn.close()
os.remove(db_path)
print("\n所有测试完成")

import duckdb
import tempfile
import os

db_path = os.path.join(tempfile.gettempdir(), 'test_duckdb_update.duckdb')
if os.path.exists(db_path):
    os.remove(db_path)

conn = duckdb.connect(db_path)

print("=== 测试1：没有索引的表 ===")
conn.execute("""
    CREATE TABLE test1 (
        id INTEGER PRIMARY KEY,
        name VARCHAR,
        value INTEGER
    )
""")
conn.execute("INSERT INTO test1 VALUES (1, 'test', 100)")
try:
    conn.execute("UPDATE test1 SET value = 200 WHERE id = 1")
    result = conn.execute("SELECT * FROM test1 WHERE id = 1").fetchone()
    print(f"UPDATE 成功: value = {result[2]}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

print("\n=== 测试2：有索引的表 ===")
conn.execute("CREATE SEQUENCE test2_seq START 1")
conn.execute("""
    CREATE TABLE test2 (
        id INTEGER PRIMARY KEY DEFAULT nextval('test2_seq'),
        name VARCHAR,
        status VARCHAR,
        value INTEGER
    )
""")
conn.execute("CREATE INDEX idx_test2_status ON test2(status)")
conn.execute("INSERT INTO test2 (name, status, value) VALUES ('test', 'active', 100)")
try:
    conn.execute("UPDATE test2 SET status = 'inactive', value = 200 WHERE id = 1")
    result = conn.execute("SELECT * FROM test2 WHERE id = 1").fetchone()
    print(f"UPDATE 成功: status = {result[2]}, value = {result[3]}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

print("\n=== 测试3：带序列的主键 ===")
conn.execute("CREATE SEQUENCE test3_seq START 1")
conn.execute("""
    CREATE TABLE test3 (
        id INTEGER PRIMARY KEY DEFAULT nextval('test3_seq'),
        name VARCHAR,
        value INTEGER
    )
""")
conn.execute("INSERT INTO test3 (name, value) VALUES ('test', 100)")
try:
    conn.execute("UPDATE test3 SET value = 200 WHERE id = 1")
    result = conn.execute("SELECT * FROM test3 WHERE id = 1").fetchone()
    print(f"UPDATE 成功: value = {result[2]}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

print("\n=== 测试4：多索引的表 ===")
conn.execute("CREATE SEQUENCE test4_seq START 1")
conn.execute("""
    CREATE TABLE test4 (
        id INTEGER PRIMARY KEY DEFAULT nextval('test4_seq'),
        hall_id INTEGER NOT NULL,
        session_no VARCHAR NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'pending',
        brightness INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.execute("CREATE INDEX idx4_hall_session ON test4(hall_id, session_no, status)")
conn.execute("CREATE INDEX idx4_status ON test4(status)")
conn.execute("CREATE INDEX idx4_created ON test4(created_at)")

conn.execute("INSERT INTO test4 (hall_id, session_no, status, brightness) VALUES (1, 'S001', 'pending', 80)")
try:
    conn.execute("UPDATE test4 SET status = 'done', brightness = 90 WHERE id = 1")
    result = conn.execute("SELECT * FROM test4 WHERE id = 1").fetchone()
    print(f"UPDATE 成功: status = {result[3]}, brightness = {result[4]}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

print("\n=== 测试5：复合唯一索引 ===")
conn.execute("CREATE SEQUENCE test5_seq START 1")
conn.execute("""
    CREATE TABLE test5 (
        id INTEGER PRIMARY KEY DEFAULT nextval('test5_seq'),
        hall_id INTEGER NOT NULL,
        session_no VARCHAR NOT NULL,
        status VARCHAR NOT NULL
    )
""")
conn.execute("CREATE UNIQUE INDEX idx5_hall_session_status ON test5(hall_id, session_no, status)")
conn.execute("INSERT INTO test5 (hall_id, session_no, status) VALUES (1, 'S001', 'pending')")
try:
    conn.execute("UPDATE test5 SET status = 'done' WHERE id = 1")
    result = conn.execute("SELECT * FROM test5 WHERE id = 1").fetchone()
    print(f"UPDATE 成功: status = {result[3]}")
except Exception as e:
    print(f"UPDATE 失败: {e}")

conn.close()
os.remove(db_path)
print("\n所有测试完成")

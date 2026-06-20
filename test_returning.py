import duckdb

conn = duckdb.connect(':memory:')

conn.execute("CREATE SEQUENCE test_seq START 1")
conn.execute("""
    CREATE TABLE test_tbl (
        id INTEGER PRIMARY KEY DEFAULT nextval('test_seq'),
        name VARCHAR
    )
""")

result = conn.execute("INSERT INTO test_tbl (name) VALUES ('hello') RETURNING id").fetchone()
print(f"Inserted id: {result[0]}")

result = conn.execute("INSERT INTO test_tbl (name) VALUES ('world') RETURNING id").fetchone()
print(f"Inserted id: {result[0]}")

rows = conn.execute("SELECT * FROM test_tbl").fetchall()
print(f"All rows: {rows}")

seq = conn.execute("SELECT sequence_name, start_value, last_value FROM duckdb_sequences()").fetchall()
print(f"Sequence: {seq}")

conn.close()

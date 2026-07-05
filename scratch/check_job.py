import sqlite3

conn = sqlite3.connect('job_platform.db')
conn.row_factory = sqlite3.Row
r = conn.execute("SELECT * FROM jobs WHERE id = 'b1336ef4e9a04a6b988adf89c6fddb2a'").fetchone()
if r:
    print(dict(r))
else:
    print("Not found")
conn.close()

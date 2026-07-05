import sqlite3
conn = sqlite3.connect('job_platform.db')
for col, defval in [('name', 'job'), ('job_type', 'immediate')]:
    try:
        conn.execute(f'ALTER TABLE jobs ADD COLUMN {col} TEXT NOT NULL DEFAULT "{defval}"')
        conn.commit()
        print(f'Added column: {col}')
    except sqlite3.OperationalError as e:
        print(f'{col}: {e}')
conn.close()
print('Done')

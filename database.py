import sqlite3

DB_PATH = "counter.db"
NUM_SHARDS = 3  # We simulate 3 distributed shards


def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database and create the sharded_counters table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sharded_counters (
            item_id  TEXT    NOT NULL,
            shard_id INTEGER NOT NULL,
            count    INTEGER DEFAULT 0,
            PRIMARY KEY (item_id, shard_id)
        )
    ''')
    conn.commit()
    conn.close()
    print(f"[DB] Initialized with {NUM_SHARDS} shards.")


def increment_shard(item_id, shard_id):
    """
    Increment the counter for a specific item on a specific shard.
    Uses INSERT ... ON CONFLICT so it works for both new and existing rows.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sharded_counters (item_id, shard_id, count)
        VALUES (?, ?, 1)
        ON CONFLICT(item_id, shard_id)
        DO UPDATE SET count = count + 1
    ''', (item_id, shard_id))
    conn.commit()
    conn.close()


def get_all_shards(item_id):
    """Return all shard rows for a given item_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT shard_id, count FROM sharded_counters WHERE item_id = ?',
        (item_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_items():
    """Return every row in the table (used for the stats endpoint)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT item_id, shard_id, count FROM sharded_counters ORDER BY item_id, shard_id'
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def reset_item(item_id):
    """Reset all shard counts for an item (for demo resets)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sharded_counters WHERE item_id = ?', (item_id,))
    conn.commit()
    conn.close()

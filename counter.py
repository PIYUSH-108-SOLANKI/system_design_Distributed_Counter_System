import random
import threading

from database import init_db, increment_shard, get_all_shards, get_all_items, reset_item, NUM_SHARDS
from cache import InMemoryCache


class CounterService:
    """
    Core business logic for the Distributed Counter.

    Responsibilities:
    1. Select which shard gets the write (write distribution)
    2. Write to that shard in the database
    3. Invalidate the cache on every write
    4. On reads: check cache first, else aggregate all shards
    """

    def __init__(self):
        init_db()
        self.cache = InMemoryCache(ttl=5)   # cache expires after 5 seconds
        self.lock = threading.Lock()

        # Runtime stats (in-memory, resets on server restart)
        self.stats = {
            "total_increments": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "shard_distribution": {i: 0 for i in range(NUM_SHARDS)}
        }

    # ------------------------------------------------------------------
    # WRITE PATH
    # ------------------------------------------------------------------

    def _select_shard(self, item_id):
        """
        Choose which shard to write to.
        Using random selection → evenly distributes load across all shards.
        (Alternative: hash(item_id) % NUM_SHARDS for consistent mapping)
        """
        return random.randint(0, NUM_SHARDS - 1)

    def increment(self, item_id):
        """
        Increment the counter for item_id.
        Steps:
          1. Pick a random shard
          2. Write +1 to that shard in the DB
          3. Invalidate cache so next read is fresh
        """
        shard_id = self._select_shard(item_id)

        increment_shard(item_id, shard_id)   # write to DB shard

        with self.lock:
            self.stats["total_increments"] += 1
            self.stats["shard_distribution"][shard_id] += 1

        self.cache.invalidate(item_id)   # invalidate stale cache

        return shard_id

    # ------------------------------------------------------------------
    # READ PATH
    # ------------------------------------------------------------------

    def get_count(self, item_id):
        """
        Return total count for item_id.
        Steps:
          1. Check cache → return immediately if hit
          2. Cache miss → query all shards and SUM them
          3. Store result in cache for next read
        """
        # Step 1: Cache lookup
        cached_value = self.cache.get(item_id)
        if cached_value is not None:
            with self.lock:
                self.stats["cache_hits"] += 1
            return cached_value, "cache"

        # Step 2: Aggregate from all shards
        with self.lock:
            self.stats["cache_misses"] += 1

        rows = get_all_shards(item_id)
        total = sum(row["count"] for row in rows)

        # Shard breakdown for the response
        shard_breakdown = {row["shard_id"]: row["count"] for row in rows}

        # Step 3: Write to cache
        self.cache.set(item_id, total)

        return total, "database", shard_breakdown

    # ------------------------------------------------------------------
    # STATS & ADMIN
    # ------------------------------------------------------------------

    def get_stats(self):
        """Return system stats and shard data for the dashboard."""
        items = get_all_items()
        shard_data = {}
        for row in items:
            key = f"{row['item_id']}__shard_{row['shard_id']}"
            shard_data[key] = row["count"]

        total_reads = self.stats["cache_hits"] + self.stats["cache_misses"]
        hit_rate = (
            round(self.stats["cache_hits"] / total_reads * 100, 1)
            if total_reads > 0 else 0
        )

        return {
            "num_shards": NUM_SHARDS,
            "total_increments": self.stats["total_increments"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "cache_hit_rate": f"{hit_rate}%",
            "cache_size": self.cache.size(),
            "shard_distribution": self.stats["shard_distribution"],
            "shard_data": shard_data,
        }

    def reset_item(self, item_id):
        """Reset counter for an item (for demo purposes)."""
        reset_item(item_id)
        self.cache.invalidate(item_id)

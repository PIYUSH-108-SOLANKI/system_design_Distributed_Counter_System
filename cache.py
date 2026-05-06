import time


class InMemoryCache:
    """
    Simulates a Redis cache with Time-To-Live (TTL) support.
    After TTL seconds, the cached value expires and the next read
    goes back to the database (shards) to get a fresh count.
    """

    def __init__(self, ttl=5):
        self._store = {}   # key -> (value, expiry_timestamp)
        self.ttl = ttl     # seconds before a cached entry expires

    def get(self, key):
        """Return cached value if it exists and hasn't expired."""
        if key in self._store:
            value, expiry = self._store[key]
            if time.time() < expiry:
                return value          # Cache HIT
            else:
                del self._store[key]  # Expired — remove it
        return None                   # Cache MISS

    def set(self, key, value):
        """Store a value in cache with TTL."""
        self._store[key] = (value, time.time() + self.ttl)

    def invalidate(self, key):
        """Remove a key from cache (called after a write)."""
        self._store.pop(key, None)

    def size(self):
        """Number of valid (non-expired) entries in cache."""
        now = time.time()
        return sum(1 for _, (_, exp) in self._store.items() if now < exp)

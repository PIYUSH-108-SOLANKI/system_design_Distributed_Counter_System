# Mini Project Report
## Problem Statement 18: Distributed Counter (High Throughput Writes)

**Subject:** System Design  
**Theme:** High-Scale Systems & Distributed Data  
**Student Name:** 1500
**Roll No:** ___________________________  
**Cohort:** Elon Musk / Mark Zuckerberg  
**Date:** May 2026

---

## 1. Objective

The goal of this project is to design and build a scalable distributed counter system — similar to the like counters on Instagram or view counters on YouTube — that can handle a large number of write operations per second without becoming a bottleneck.

The system accepts increment events (likes, views, clicks), distributes the writes across multiple shards, and returns the total count by aggregating values from all shards. A cache layer is used to serve read requests quickly without querying the database every time.

---

## 2. Key Features

**High Throughput Counter Writes**  
The system is designed to handle a massive number of increment operations per second. Instead of writing every increment to a single database row (which would create a bottleneck due to row-level locking), writes are spread across multiple shards.

**Sharded Counter System**  
A single counter is split into multiple smaller counters called shards. Each shard holds a partial count. The final count is the sum of all shard values. In this project, 3 shards are used to simulate this behaviour.

**Write Distribution Mechanism**  
Incoming write requests are distributed across shards using random selection. This ensures no single shard receives all the traffic, preventing bottlenecks.

**Aggregation Engine**  
When a read request comes in, the system queries all shards and sums their counts. This aggregated value is the total count for that item.

**Read Optimisation Layer (Cache)**  
After aggregation, the total count is stored in an in-memory cache. Subsequent read requests are served directly from the cache without hitting the database, keeping read latency under 100ms.

---

## 3. Functional Requirements

- The system accepts increment requests for any item (post, video, product) via a POST API.
- Incoming writes are distributed across multiple shards.
- The system returns the total count for a given item via a GET API.
- Multiple counters are supported — each identified by a unique item ID.
- No data is lost during failures because all writes are persisted to the database (SQLite).
- Concurrent updates are handled safely using Python threading locks.

---

## 4. Non-Functional Requirements

| Requirement | Description | How It Is Met |
|---|---|---|
| High Throughput | Handle millions of writes per second | Writes distributed across 3 shards in parallel |
| Low Latency Reads | Count retrieval under 100ms | In-memory cache serves most reads instantly |
| Scalability | Scale by adding more shards | `NUM_SHARDS` variable controls shard count |
| Availability | System works during partial failures | Each shard is independent |
| Durability | Counts are not lost | All data persisted to SQLite on disk |
| Eventual Consistency | Slight delay in final count is acceptable | Cache TTL of 5 seconds |

---

## 5. High-Level Design (HLD)

### System Architecture

```
Client (Browser / Mobile App)
        |
        | HTTP Request
        v
API Gateway / Backend Service  (Flask Server — app.py)
        |
        v
Counter Service  (counter.py)
|   - Shard selection logic
|   - Cache management
|   - Aggregation
        |
        |-- Write Path ----------------------------------|
        |                                               |
        v                                               v
Distributed Storage (SQLite — simulating NoSQL)    Cache Layer
                                                (In-Memory Dict)
  item_id  | shard_id | count                  item_id → total_count
  ---------|----------|------
  post_001 |    0     |  42
  post_001 |    1     |  38
  post_001 |    2     |  41
```

### Main Components

| Component | Role | Technology Used |
|---|---|---|
| Client | Triggers events (like/view/click) | Browser (HTML/JS) |
| API Gateway | Receives HTTP requests, routes them | Flask (Python) |
| Counter Service | Shard selection, aggregation, cache | Python class |
| Shard Manager | Selects target shard for each write | Random selection |
| Distributed Storage | Stores partial counts per shard | SQLite |
| Cache Layer | Serves reads without DB queries | In-memory dictionary |
| Aggregation Service | Sums all shard values on read | Python (sum of rows) |

### Data Flow — Write Path

```
1. User clicks Like / View / Click on the frontend
2. POST /increment/{item_id} sent to Flask server
3. Counter Service selects a random shard (0, 1, or 2)
4. count + 1 applied to that shard row in the database
5. Cache entry for this item is invalidated
```

### Data Flow — Read Path

```
1. GET /count/{item_id} sent to Flask server
2. Counter Service checks the in-memory cache
3a. Cache HIT  → return cached total immediately
3b. Cache MISS → query all 3 shard rows from database
4. Sum all shard values to get total count
5. Store total in cache (TTL = 5 seconds)
6. Return total count to client
```

---

## 6. Low-Level Design (LLD)

### 6.1 API Endpoints

| Method | Endpoint | Description | Request Body | Response |
|---|---|---|---|---|
| POST | `/increment/<item_id>` | Increment counter | None | `{ status, item_id, shard_used }` |
| GET  | `/count/<item_id>` | Get total count | None | `{ item_id, total_count, source, shard_breakdown }` |
| GET  | `/stats` | System statistics | None | Cache hits, misses, shard distribution |
| GET  | `/shards` | Raw DB table data | None | All rows from sharded_counters table |
| POST | `/reset/<item_id>` | Reset a counter | None | `{ status, item_id }` |

### 6.2 Core Logic — Shard Selection

```python
def _select_shard(self, item_id):
    return random.randint(0, NUM_SHARDS - 1)
```

Random selection is used to evenly distribute writes across all shards over time. An alternative approach is consistent hashing: `hash(item_id) % NUM_SHARDS`, which always routes the same item to the same shard.

### 6.3 Core Logic — Write Path

```python
def increment(self, item_id):
    shard_id = self._select_shard(item_id)   # 1. Pick random shard
    increment_shard(item_id, shard_id)        # 2. Write to DB
    self.cache.invalidate(item_id)            # 3. Invalidate cache
    return shard_id
```

### 6.4 Core Logic — Read Path

```python
def get_count(self, item_id):
    cached = self.cache.get(item_id)
    if cached is not None:
        return cached, "cache"               # Cache HIT

    rows = get_all_shards(item_id)           # Query all shards
    total = sum(row["count"] for row in rows) # Aggregate
    self.cache.set(item_id, total)           # Store in cache
    return total, "database"
```

### 6.5 Database Design

**Table name:** `sharded_counters`

| Column | Data Type | Description |
|---|---|---|
| item_id | TEXT | Unique ID of the post/video/product |
| shard_id | INTEGER | Which shard (0, 1, or 2) |
| count | INTEGER | Partial count stored on this shard |

**Primary Key:** `(item_id, shard_id)` — composite key ensures one row per item per shard.

**Sample Data:**

```
item_id     | shard_id | count
------------|----------|------
post_001    |    0     |  42
post_001    |    1     |  38
post_001    |    2     |  41
video_042   |    0     | 120
video_042   |    2     |  95
```

**Total count for post_001 = 42 + 38 + 41 = 121**

**SQL used for increment:**
```sql
INSERT INTO sharded_counters (item_id, shard_id, count)
VALUES (?, ?, 1)
ON CONFLICT(item_id, shard_id)
DO UPDATE SET count = count + 1;
```

### 6.6 Cache Design

```
Structure:  { item_id: (total_count, expiry_timestamp) }

Example:    { "post_001": (121, 1714923456.7) }

TTL:        5 seconds — after which the entry expires
            and the next read re-aggregates from the database.
```

---

## 7. Project File Structure

```
distributed-counter/
├── app.py           — Flask API server (all endpoints)
├── counter.py       — Core logic: sharding, aggregation, caching
├── database.py      — SQLite operations (read/write shards)
├── cache.py         — In-memory cache with TTL
├── requirements.txt — Python dependencies (flask, flask-cors)
├── counter.db       — SQLite database file (created on first run)
└── static/
    └── index.html   — Frontend demo UI
```

---

## 8. Sequence Diagrams

### Write Sequence (Increment)

```
User         Browser       Flask API      Counter Svc     SQLite DB     Cache
 |             |               |               |               |           |
 |--[click]-->  |               |               |               |           |
 |             |--POST /incr-->|               |               |           |
 |             |               |--increment()-->|               |           |
 |             |               |               |--pick shard-->|           |
 |             |               |               |--write +1 --->|           |
 |             |               |               |               |           |
 |             |               |               |--invalidate cache-------->|
 |             |               |<--shard_id----|               |           |
 |             |<--{ shard_used: 2 }-----------|               |           |
```

### Read Sequence (Get Count)

```
User         Browser       Flask API      Counter Svc     SQLite DB     Cache
 |             |               |               |               |           |
 |--[read]--->  |               |               |               |           |
 |             |--GET /count-->|               |               |           |
 |             |               |--get_count()-->|               |           |
 |             |               |               |--check cache------------->|
 |             |               |               |<-- MISS ------------------|
 |             |               |               |--query all shards-------->|
 |             |               |               |<--[42, 38, 41]------------|
 |             |               |               |--sum = 121                |
 |             |               |               |--store in cache---------->|
 |             |               |<--{ total: 121, source: "database" }------|
 |             |<--display 121-|               |               |           |
```

---

## 9. Technology Stack

| Layer | Technology | Production Equivalent |
|---|---|---|
| Backend API | Python Flask | Node.js, Go, Spring Boot |
| Database / Shards | SQLite | Apache Cassandra, DynamoDB |
| Cache | In-memory Python dict | Redis |
| Frontend | HTML, CSS, JavaScript | React, Angular |

---

## 10. Scalability Considerations

**Adding More Shards**  
The number of shards is controlled by `NUM_SHARDS = 3` in `database.py`. Increasing this value immediately distributes writes across more shards, reducing contention on each one.

**Hot Key Handling**  
If one item (e.g., a viral post) receives extremely high traffic, its shard count can be increased independently. More shards = more parallel writes = no single point of bottleneck.

**Horizontal Scaling**  
In a production system, each shard would run on a separate database server. New servers (shards) can be added without changing the application logic.

**Asynchronous Aggregation**  
For very read-heavy workloads, a background job can pre-compute and cache the total count periodically instead of aggregating on every cache miss.

---

## 11. Design Justifications and Trade-offs

**Why Sharding?**  
A single database row for a counter creates a write bottleneck because all concurrent writes compete for the same row lock. Sharding splits the writes across multiple independent rows, eliminating this bottleneck.

**Why Aggregation?**  
Since the count is split across shards, it must be summed on reads. This is a deliberate trade-off: accept slightly more expensive reads in exchange for highly scalable writes.

**Why Eventual Consistency?**  
Enforcing exact real-time accuracy across all shards would require distributed transactions and locks, which are expensive and slow. For counters (likes, views), a delay of a few seconds is acceptable. The system will eventually converge to the correct total.

**Why Caching?**  
Aggregating all shards on every read would put unnecessary load on the database at scale. The cache stores the computed total for 5 seconds, serving most read requests without any database query.

**Trade-off Summary:**

| Trade-off | Choice Made | Reason |
|---|---|---|
| Accuracy vs Performance | Performance | Exact real-time count is expensive |
| Consistency vs Availability | Availability | System keeps working during partial failures |
| Simple storage vs Real distributed DB | SQLite | Simulates sharding behaviour at student level |
| Synchronous vs Async aggregation | Synchronous | Simpler to implement and demonstrate |

---

## 12. How to Run the Project

```bash
# Step 1: Navigate to project folder
cd ~/Desktop/distributed-counter

# Step 2: Install dependencies (first time only)
pip3 install flask flask-cors

# Step 3: Start the server
python3 app.py

# Step 4: Open browser
# URL: http://localhost:8080
```

---

*End of Report*

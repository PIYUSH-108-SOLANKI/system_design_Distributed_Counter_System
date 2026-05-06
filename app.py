from flask import Flask, jsonify, request
from flask_cors import CORS
from counter import CounterService

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Single instance of our counter service (shared across all requests)
counter_service = CounterService()


# ──────────────────────────────────────────────
# Serve the frontend
# ──────────────────────────────────────────────

@app.route('/')
def index():
    return app.send_static_file('index.html')


# ──────────────────────────────────────────────
# API: Increment counter
# POST /increment/<item_id>
# ──────────────────────────────────────────────

@app.route('/increment/<item_id>', methods=['POST'])
def increment(item_id):
    """
    Increment the counter for the given item.
    Internally picks a random shard and writes to it.
    """
    shard_id = counter_service.increment(item_id)
    return jsonify({
        "status": "success",
        "item_id": item_id,
        "shard_used": shard_id,
        "message": f"Incremented '{item_id}' on Shard {shard_id}"
    })


# ──────────────────────────────────────────────
# API: Get total count
# GET /count/<item_id>
# ──────────────────────────────────────────────

@app.route('/count/<item_id>', methods=['GET'])
def get_count(item_id):
    """
    Return the total count for an item.
    Checks cache first; falls back to aggregating all shards.
    """
    result = counter_service.get_count(item_id)

    if len(result) == 3:
        total, source, shard_breakdown = result
    else:
        total, source = result
        shard_breakdown = {}

    return jsonify({
        "item_id": item_id,
        "total_count": total,
        "source": source,          # "cache" or "database"
        "shard_breakdown": shard_breakdown
    })


# ──────────────────────────────────────────────
# API: System stats
# GET /stats
# ──────────────────────────────────────────────

@app.route('/stats', methods=['GET'])
def get_stats():
    """Return system-wide stats: cache hits/misses, shard distribution, etc."""
    return jsonify(counter_service.get_stats())


# ──────────────────────────────────────────────
# API: Reset a counter (demo helper)
# POST /reset/<item_id>
# ──────────────────────────────────────────────

@app.route('/reset/<item_id>', methods=['POST'])
def reset(item_id):
    counter_service.reset_item(item_id)
    return jsonify({"status": "reset", "item_id": item_id})


# ──────────────────────────────────────────────

if __name__ == '__main__':
    print("\n🚀 Distributed Counter Server running at http://localhost:8080\n")
    app.run(debug=True, port=8080)

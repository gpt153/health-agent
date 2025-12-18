#!/usr/bin/env python3
"""
Simple web-based Mem0 viewer
Access at: http://localhost:5555
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template_string, request, jsonify
import psycopg
from datetime import datetime
from dotenv import load_dotenv
from src.config import DATABASE_URL

load_dotenv()

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mem0 Memory Viewer</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .controls {
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }
        .controls input, .controls select, .controls button {
            padding: 10px 15px;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            font-size: 14px;
        }
        .controls input[type="text"] { flex: 1; min-width: 200px; }
        .controls button {
            background: #667eea;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
        }
        .controls button:hover { background: #5568d3; }
        .stats {
            padding: 20px;
            background: #f8f9fa;
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .stat-card {
            background: white;
            padding: 15px 25px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .stat-card .number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-card .label {
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .memories {
            padding: 20px;
        }
        .memory-card {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 6px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .memory-card:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .memory-text {
            font-size: 1.1em;
            color: #212529;
            margin-bottom: 10px;
            line-height: 1.6;
        }
        .memory-meta {
            display: flex;
            gap: 15px;
            font-size: 0.85em;
            color: #6c757d;
        }
        .memory-meta span {
            background: white;
            padding: 4px 10px;
            border-radius: 4px;
        }
        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
        }
        .relevance {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Mem0 Memory Viewer</h1>
            <p>Semantic memory browser for Health Agent</p>
        </div>

        <div class="controls">
            <input type="text" id="userId" placeholder="User ID (e.g., 7376426503)" value="7376426503">
            <input type="text" id="searchQuery" placeholder="Search memories (semantic)...">
            <button onclick="loadMemories()">View All</button>
            <button onclick="searchMemories()">Search</button>
            <select id="limitSelect">
                <option value="20">20 results</option>
                <option value="50">50 results</option>
                <option value="100" selected>100 results</option>
                <option value="200">200 results</option>
            </select>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="number" id="totalCount">-</div>
                <div class="label">Total Memories</div>
            </div>
            <div class="stat-card">
                <div class="number" id="shownCount">-</div>
                <div class="label">Shown</div>
            </div>
        </div>

        <div class="memories" id="memoriesContainer">
            <div class="loading">Loading...</div>
        </div>
    </div>

    <script>
        function loadMemories() {
            const userId = document.getElementById('userId').value;
            const limit = document.getElementById('limitSelect').value;

            document.getElementById('memoriesContainer').innerHTML = '<div class="loading">Loading memories...</div>';

            fetch(`/api/memories?user_id=${userId}&limit=${limit}`)
                .then(r => r.json())
                .then(data => displayMemories(data))
                .catch(err => {
                    document.getElementById('memoriesContainer').innerHTML =
                        '<div class="no-results">Error loading memories: ' + err + '</div>';
                });
        }

        function searchMemories() {
            const userId = document.getElementById('userId').value;
            const query = document.getElementById('searchQuery').value;
            const limit = document.getElementById('limitSelect').value;

            if (!query) {
                alert('Please enter a search query');
                return;
            }

            document.getElementById('memoriesContainer').innerHTML =
                '<div class="loading">Searching memories...</div>';

            fetch(`/api/search?user_id=${userId}&query=${encodeURIComponent(query)}&limit=${limit}`)
                .then(r => r.json())
                .then(data => displayMemories(data, true))
                .catch(err => {
                    document.getElementById('memoriesContainer').innerHTML =
                        '<div class="no-results">Error searching: ' + err + '</div>';
                });
        }

        function displayMemories(data, isSearch = false) {
            const container = document.getElementById('memoriesContainer');

            if (!data.memories || data.memories.length === 0) {
                container.innerHTML = '<div class="no-results">No memories found</div>';
                document.getElementById('totalCount').textContent = '0';
                document.getElementById('shownCount').textContent = '0';
                return;
            }

            document.getElementById('totalCount').textContent = data.total || data.memories.length;
            document.getElementById('shownCount').textContent = data.memories.length;

            let html = '';
            data.memories.forEach((mem, idx) => {
                html += `
                    <div class="memory-card">
                        <div class="memory-text">
                            ${idx + 1}. ${escapeHtml(mem.memory)}
                        </div>
                        <div class="memory-meta">
                            ${mem.created_at ? '<span>📅 ' + new Date(mem.created_at).toLocaleString() + '</span>' : ''}
                            ${mem.source ? '<span>📍 ' + mem.source + '</span>' : ''}
                            ${isSearch && mem.score ? '<span class="relevance">Relevance: ' + (mem.score * 100).toFixed(1) + '%</span>' : ''}
                        </div>
                    </div>
                `;
            });

            container.innerHTML = html;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Load on start
        window.onload = () => loadMemories();

        // Enter key support
        document.getElementById('searchQuery').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchMemories();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/memories')
def get_memories():
    user_id = request.args.get('user_id', '7376426503')
    limit = int(request.args.get('limit', 100))

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        payload->>'data' as memory,
                        payload->>'source' as source,
                        payload->>'created_at' as created_at
                    FROM mem0
                    WHERE payload->>'user_id' = %s
                    ORDER BY (payload->>'created_at')::timestamp DESC
                    LIMIT %s
                """, (user_id, limit))

                memories = []
                for row in cur.fetchall():
                    memories.append({
                        'memory': row[0],
                        'source': row[1],
                        'created_at': row[2]
                    })

                # Get total count
                cur.execute("""
                    SELECT COUNT(*)
                    FROM mem0
                    WHERE payload->>'user_id' = %s
                """, (user_id,))
                total = cur.fetchone()[0]

                return jsonify({
                    'memories': memories,
                    'total': total
                })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search_memories():
    user_id = request.args.get('user_id', '7376426503')
    query = request.args.get('query', '')
    limit = int(request.args.get('limit', 20))

    try:
        # Use semantic search via Mem0
        from src.memory.mem0_manager import mem0_manager

        results = mem0_manager.search(user_id, query, limit=limit)

        if isinstance(results, dict):
            memories_list = results.get('results', [])
        else:
            memories_list = results

        memories = []
        for mem in memories_list:
            if isinstance(mem, dict):
                memories.append({
                    'memory': mem.get('memory', mem.get('text', str(mem))),
                    'score': mem.get('score', 0),
                    'source': None,
                    'created_at': None
                })
            else:
                memories.append({
                    'memory': str(mem),
                    'score': 0,
                    'source': None,
                    'created_at': None
                })

        return jsonify({
            'memories': memories,
            'total': len(memories)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧠 Mem0 Web Viewer Starting...")
    print("="*60)
    print(f"\n📊 Access the viewer at: http://localhost:5555")
    print(f"🗄️  Database: {DATABASE_URL}")
    print(f"\n✨ Features:")
    print(f"   • View all memories for a user")
    print(f"   • Semantic search with relevance scoring")
    print(f"   • Beautiful web interface")
    print(f"\n🛑 Press Ctrl+C to stop\n")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5555, debug=True)

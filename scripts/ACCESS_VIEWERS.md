# 🎯 Mem0 Viewers - Ready to Use!

Both viewers are now **running and configured** in your workspace!

---

## 🌐 Option 1: Web Viewer (EASIEST - READY NOW!)

### Access:
**http://localhost:5555**

### Features:
- ✅ **Beautiful web interface** - No setup needed!
- ✅ **View all memories** - Browse by user ID
- ✅ **Semantic search** - AI-powered relevance search
- ✅ **Real-time updates** - Instant results
- ✅ **Statistics** - Total count and more

### How to use:
1. **Open browser**: http://localhost:5555
2. **User ID is pre-filled**: 7376426503
3. **Click "View All"** to see all memories
4. **Or type search query** and click "Search"

### Features:
- Change user ID in the input field
- Adjust result limit (20/50/100/200)
- Semantic search finds relevant memories by meaning
- Memories show creation date and source

---

## 🗄️ Option 2: pgAdmin (Professional SQL Tool)

### Access:
**http://localhost:5050**

### Login:
- **Email**: admin@admin.com
- **Password**: admin

### Setup Connection (One-time):

1. **Open pgAdmin**: http://localhost:5050
2. **Add Server**: Right-click "Servers" → "Register" → "Server"
3. **General tab**:
   - Name: `Health Agent`
4. **Connection tab**:
   - Host: `host.docker.internal` (for Docker)
   - Or: Your machine's IP address
   - Port: `5434`
   - Database: `health_agent`
   - Username: `postgres`
   - Password: `postgres`
   - ✅ Check "Save password"
5. **Click Save**

### Navigate to Mem0:
```
Servers → Health Agent → Databases → health_agent → Schemas → public → Tables → mem0
```

### View Data:
- Right-click `mem0` → "View/Edit Data" → "All Rows"
- Or use Query Tool (F5) and run SQL queries

---

## 📊 Quick Comparison

| Feature | Web Viewer | pgAdmin |
|---------|------------|---------|
| Setup | ✅ Ready now! | One-time connection setup |
| Interface | Modern web UI | Professional SQL IDE |
| Search | Semantic AI search | SQL queries |
| Export | Via SQL | CSV, JSON, Excel |
| Speed | Very fast | Fast |
| Best for | Quick browsing | Deep analysis |

---

## 🚀 Management Commands

### Start viewers (if stopped):
```bash
bash scripts/start_mem0_viewers.sh
```

### Check status:
```bash
# Web viewer
curl http://localhost:5555

# pgAdmin
docker ps | grep pgadmin
```

### View logs:
```bash
# Web viewer
tail -f logs/mem0_viewer.log

# pgAdmin
docker logs health-agent-pgadmin
```

### Stop viewers:
```bash
# Web viewer
pkill -f mem0_web_viewer.py

# pgAdmin
docker stop health-agent-pgadmin
```

### Restart:
```bash
# Web viewer
pkill -f mem0_web_viewer.py
python scripts/mem0_web_viewer.py &

# pgAdmin
docker restart health-agent-pgadmin
```

---

## 💡 Usage Examples

### Web Viewer Examples:

1. **View all memories**:
   - Open http://localhost:5555
   - Click "View All"

2. **Search for training info**:
   - Type "training" in search box
   - Click "Search"
   - See relevance scores!

3. **Filter by limit**:
   - Select "50 results" or "100 results"
   - Click "View All" again

### pgAdmin Examples:

1. **View recent memories**:
   ```sql
   SELECT
       payload->>'data' as memory,
       payload->>'created_at' as created_at
   FROM mem0
   WHERE payload->>'user_id' = '7376426503'
   ORDER BY (payload->>'created_at')::timestamp DESC
   LIMIT 20;
   ```

2. **Search by keyword**:
   ```sql
   SELECT payload->>'data' as memory
   FROM mem0
   WHERE payload->>'user_id' = '7376426503'
     AND payload->>'data' ILIKE '%nutrition%';
   ```

3. **Export to CSV**:
   - Run any query
   - Click "Download" button
   - Choose CSV format

---

## 🎨 Screenshots (What to Expect)

### Web Viewer:
```
┌─────────────────────────────────────────┐
│  🧠 Mem0 Memory Viewer                  │
│  Semantic memory browser                │
├─────────────────────────────────────────┤
│ [7376426503] [Search...] [View] [Search]│
├─────────────────────────────────────────┤
│ Total: 63    Shown: 20                  │
├─────────────────────────────────────────┤
│ 1. Calorie goal is 2,200-2,300 kcal     │
│    📅 2025-12-17 15:54                   │
├─────────────────────────────────────────┤
│ 2. Today is a rest day from training    │
│    📅 2025-12-17 15:54                   │
└─────────────────────────────────────────┘
```

### pgAdmin:
- Professional database interface
- Tree view of tables
- SQL editor with syntax highlighting
- Data grid view
- Export options

---

## 🔧 Troubleshooting

### Web viewer not accessible?
```bash
# Check if running
ps aux | grep mem0_web_viewer

# Restart
pkill -f mem0_web_viewer.py
python scripts/mem0_web_viewer.py &
```

### pgAdmin not accessible?
```bash
# Check Docker
docker ps | grep pgadmin

# Restart
docker restart health-agent-pgadmin

# Wait 10 seconds then access http://localhost:5050
```

### Can't connect pgAdmin to database?
- Use `host.docker.internal` as host (for Mac/Windows Docker)
- Or use your machine's IP address (find with `hostname -I`)
- Port must be `5434`
- Check database is running: `ps aux | grep postgres`

---

## 🎯 Recommended Workflow

1. **Quick checks**: Use Web Viewer (http://localhost:5555)
   - Fast, simple, ready to use
   - Perfect for browsing and searching

2. **Deep analysis**: Use pgAdmin (http://localhost:5050)
   - Complex SQL queries
   - Data export
   - Professional features

---

## 📞 Support

**Web Viewer**:
- Port: 5555
- Process: `mem0_web_viewer.py`
- Logs: `logs/mem0_viewer.log`

**pgAdmin**:
- Port: 5050
- Container: `health-agent-pgadmin`
- Logs: `docker logs health-agent-pgadmin`

**Database**:
- Port: 5434
- Name: `health_agent`
- User: `postgres`

---

## ✅ Summary

✨ **Web Viewer is running at**: http://localhost:5555
🗄️ **pgAdmin is running at**: http://localhost:5050 (login: admin@admin.com / admin)

**Both are ready to use right now!** Open the URLs in your browser.

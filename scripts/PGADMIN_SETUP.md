# Using pgAdmin to View Mem0 Memories

pgAdmin provides a graphical interface to browse your PostgreSQL database and Mem0 memories.

---

## Installation

### Option 1: pgAdmin Desktop (Recommended)
```bash
# Ubuntu/Debian
curl -fsS https://www.pgadmin.org/static/packages_pgadmin_org.pub | sudo gpg --dearmor -o /usr/share/keyrings/packages-pgadmin-org.gpg
sudo sh -c 'echo "deb [signed-by=/usr/share/keyrings/packages-pgadmin-org.gpg] https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" > /etc/apt/sources.list.d/pgadmin4.list'
sudo apt update
sudo apt install pgadmin4-desktop
```

### Option 2: pgAdmin Web
```bash
sudo apt install pgadmin4-web
sudo /usr/pgadmin4/bin/setup-web.sh
```

### Option 3: Docker (Quick Start)
```bash
docker run -p 5050:80 \
  -e PGADMIN_DEFAULT_EMAIL=admin@admin.com \
  -e PGADMIN_DEFAULT_PASSWORD=admin \
  -d dpage/pgadmin4
```
Then open: http://localhost:5050

---

## Connection Details

Use these settings to connect to your health-agent database:

| Setting | Value |
|---------|-------|
| **Host** | `localhost` |
| **Port** | `5434` |
| **Database** | `health_agent` |
| **Username** | `postgres` |
| **Password** | `postgres` |

---

## Step-by-Step Setup in pgAdmin

### 1. Launch pgAdmin
```bash
pgadmin4
```

### 2. Add New Server
- Right-click "Servers" → "Register" → "Server"

### 3. General Tab
- **Name:** Health Agent Database

### 4. Connection Tab
- **Host:** localhost
- **Port:** 5434
- **Maintenance database:** postgres
- **Username:** postgres
- **Password:** postgres
- ✅ Save password

### 5. Click "Save"

---

## Viewing Mem0 Memories in pgAdmin

### Navigate to the Mem0 Table
```
Servers → Health Agent Database → Databases → health_agent → Schemas → public → Tables → mem0
```

### View Data
1. Right-click `mem0` table
2. Select "View/Edit Data" → "All Rows"

### Query Mem0 Memories

Click the **Query Tool** button (or press F5) and run:

```sql
-- View all memories for a user
SELECT
    id,
    payload->>'user_id' as user_id,
    payload->>'data' as memory,
    payload->>'created_at' as created_at
FROM mem0
WHERE payload->>'user_id' = '7376426503'
ORDER BY (payload->>'created_at')::timestamp DESC;
```

---

## Useful pgAdmin Features

### 1. Visual Query Builder
- Right-click table → "Query Tool"
- Use the graphical query builder
- Drag and drop columns

### 2. Export Data
- Run query
- Click "Download" icon
- Choose CSV, JSON, or other formats

### 3. Data Visualization
- View column statistics
- See data distribution
- Analyze patterns

### 4. JSON Viewer
- Click on `payload` column
- pgAdmin shows formatted JSON
- Navigate nested structures easily

---

## Common Queries for pgAdmin

### View Recent Memories
```sql
SELECT
    payload->>'data' as memory,
    payload->>'created_at' as created_at
FROM mem0
WHERE payload->>'user_id' = '7376426503'
ORDER BY (payload->>'created_at')::timestamp DESC
LIMIT 20;
```

### Search Memories
```sql
SELECT
    payload->>'data' as memory
FROM mem0
WHERE payload->>'user_id' = '7376426503'
  AND payload->>'data' ILIKE '%training%';
```

### Memory Count by User
```sql
SELECT
    payload->>'user_id' as user_id,
    COUNT(*) as memory_count
FROM mem0
GROUP BY payload->>'user_id'
ORDER BY memory_count DESC;
```

### Export All Memories to CSV
```sql
SELECT
    payload->>'user_id' as user_id,
    payload->>'data' as memory,
    payload->>'source' as source,
    payload->>'created_at' as created_at
FROM mem0
WHERE payload->>'user_id' = '7376426503'
ORDER BY (payload->>'created_at')::timestamp DESC;
```
Then click "Download as CSV"

---

## Alternative GUI Tools

### 1. DBeaver (Free, Cross-platform)
- Download: https://dbeaver.io/download/
- Very powerful, supports many databases
- Great for data analysis

**Connection:**
- Host: localhost
- Port: 5434
- Database: health_agent
- Username: postgres
- Password: postgres

### 2. TablePlus (Mac/Windows/Linux)
- Download: https://tableplus.com/
- Beautiful modern interface
- Native GUI, very fast

### 3. DataGrip (JetBrains, Paid)
- Download: https://www.jetbrains.com/datagrip/
- Professional IDE for databases
- Advanced features

### 4. Beekeeper Studio (Free, Open Source)
- Download: https://www.beekeeperstudio.io/
- Simple, clean interface
- Cross-platform

---

## Quick pgAdmin Tips

### Keyboard Shortcuts
- `F5` - Execute query
- `F7` - Format SQL
- `F8` - Explain query plan
- `Ctrl+Space` - Autocomplete

### View Vector Embeddings
```sql
-- See the actual vector for a memory
SELECT
    id,
    payload->>'data' as memory,
    vector::text -- Shows first few dimensions
FROM mem0
LIMIT 1;
```

### Analyze Memory Growth
```sql
SELECT
    DATE(payload->>'created_at') as date,
    COUNT(*) as memories_created
FROM mem0
WHERE payload->>'user_id' = '7376426503'
GROUP BY DATE(payload->>'created_at')
ORDER BY date DESC;
```

---

## Troubleshooting

### Can't connect?
1. Check PostgreSQL is running: `ps aux | grep postgres`
2. Verify port 5434 is open: `netstat -tlnp | grep 5434`
3. Test connection: `PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent -c "SELECT 1;"`

### pgAdmin slow?
- Limit results: Add `LIMIT 100` to queries
- Filter by date: `WHERE (payload->>'created_at')::timestamp > NOW() - INTERVAL '7 days'`

### Can't see payload contents?
- Right-click column → "View Data"
- Or use `payload->>'field_name'` in SQL

---

## Example pgAdmin Workflow

1. **Open pgAdmin** → Connect to server
2. **Navigate** to `health_agent` → `public` → `mem0`
3. **Query Tool** (F5)
4. **Run query:**
   ```sql
   SELECT
       payload->>'data' as memory,
       payload->>'created_at' as created_at
   FROM mem0
   WHERE payload->>'user_id' = '7376426503'
   ORDER BY (payload->>'created_at')::timestamp DESC
   LIMIT 50;
   ```
5. **View results** in grid
6. **Export** if needed (Download CSV button)

---

## Visual Benefits of pgAdmin

✅ Browse tables visually
✅ View JSON payloads formatted
✅ Run queries with autocomplete
✅ Export to CSV/JSON/Excel
✅ See table relationships
✅ Monitor query performance
✅ Backup/restore data
✅ No command line needed!

---

## Quick Access

Once set up, viewing memories is as simple as:
1. Open pgAdmin
2. Navigate to mem0 table
3. Right-click → View/Edit Data → All Rows
4. Or run saved queries

Much easier than command line for browsing!

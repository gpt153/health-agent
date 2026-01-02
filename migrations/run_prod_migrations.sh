#!/bin/bash
echo "=== Running migrations on PRODUCTION database (port 5436) ==="
echo ""
for sql in $(ls -1 *.sql | sort -V); do
  echo "▶ Running $sql..."
  PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres -d health_agent -f "$sql" 2>&1 | grep -E "CREATE|ALTER|INSERT|ERROR|already exists" | head -5
  if [ $? -eq 0 ]; then
    echo "  ✓ Completed"
  fi
  echo ""
done
echo "=== Migration complete ==="

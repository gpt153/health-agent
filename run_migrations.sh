#!/bin/bash
cd migrations
for sql in $(ls -1 *.sql | sort -V); do
  echo "Running $sql..."
  PGPASSWORD=postgres psql -h localhost -p 5433 -U postgres -d health_agent -f "$sql"
done

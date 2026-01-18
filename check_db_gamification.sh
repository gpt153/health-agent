#!/bin/bash
# Check if gamification tables exist in the database

echo "==================================================="
echo "Checking Gamification Tables in Database"
echo "==================================================="

# Database connection details from .env.example
DB_URL="postgresql://postgres:postgres@localhost:5436/health_agent"

echo ""
echo "1. Checking if tables exist..."
echo "---------------------------------------------------"
psql "$DB_URL" -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('user_xp', 'xp_transactions', 'user_streaks', 'achievements', 'user_achievements')
ORDER BY table_name;
"

echo ""
echo "2. Checking table row counts..."
echo "---------------------------------------------------"
psql "$DB_URL" -c "
SELECT
  'user_xp' as table_name, COUNT(*) as row_count FROM user_xp
UNION ALL
SELECT
  'xp_transactions', COUNT(*) FROM xp_transactions
UNION ALL
SELECT
  'user_streaks', COUNT(*) FROM user_streaks
UNION ALL
SELECT
  'achievements', COUNT(*) FROM achievements
UNION ALL
SELECT
  'user_achievements', COUNT(*) FROM user_achievements;
" 2>&1 || echo "ERROR: Tables might not exist!"

echo ""
echo "3. Checking recent XP transactions (last 30 days)..."
echo "---------------------------------------------------"
psql "$DB_URL" -c "
SELECT user_id, amount, source_type, reason, awarded_at
FROM xp_transactions
WHERE awarded_at > NOW() - INTERVAL '30 days'
ORDER BY awarded_at DESC
LIMIT 10;
" 2>&1 || echo "ERROR: xp_transactions table might not exist!"

echo ""
echo "4. Checking migration status..."
echo "---------------------------------------------------"
psql "$DB_URL" -c "
SELECT * FROM schema_migrations
WHERE version LIKE '%008%' OR filename LIKE '%gamif%'
ORDER BY applied_at DESC;
" 2>&1 || echo "No schema_migrations table or no matching migrations"

echo ""
echo "==================================================="
echo "Database Check Complete"
echo "==================================================="

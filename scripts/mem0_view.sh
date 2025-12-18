#!/bin/bash
# Quick viewer for Mem0 memories

USER_ID=${1:-7376426503}
ACTION=${2:-list}
LIMIT=${3:-20}

case $ACTION in
  list)
    echo "📝 Memories for user $USER_ID:"
    echo "========================================"
    PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent -c "
      SELECT 
        ROW_NUMBER() OVER (ORDER BY id DESC) as num,
        SUBSTRING(id::text, 1, 8) as id,
        payload->>'data' as memory
      FROM mem0 
      WHERE payload->>'user_id' = '$USER_ID'
      ORDER BY id DESC
      LIMIT $LIMIT;
    "
    ;;
    
  search)
    QUERY=$3
    echo "🔍 Searching for: $QUERY"
    echo "========================================"
    PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent -c "
      SELECT 
        payload->>'data' as memory
      FROM mem0 
      WHERE payload->>'user_id' = '$USER_ID'
        AND payload->>'data' ILIKE '%$QUERY%'
      LIMIT 20;
    "
    ;;
    
  count)
    PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent -c "
      SELECT COUNT(*) as total_memories
      FROM mem0 
      WHERE payload->>'user_id' = '$USER_ID';
    "
    ;;
    
  delete)
    MEM_ID=$3
    echo "⚠️  Deleting memory $MEM_ID"
    PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d health_agent -c "
      DELETE FROM mem0 WHERE id = '$MEM_ID';
    "
    echo "✅ Deleted"
    ;;
    
  *)
    echo "Usage: $0 <user_id> <action> [params]"
    echo ""
    echo "Actions:"
    echo "  list [limit]       - List memories (default: 20)"
    echo "  search <query>     - Search memories"
    echo "  count              - Count total memories"
    echo "  delete <id>        - Delete specific memory"
    echo ""
    echo "Example:"
    echo "  $0 7376426503 list 10"
    echo "  $0 7376426503 search 'training'"
    echo "  $0 7376426503 delete '<memory-id>'"
    ;;
esac

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="/home/hksentini/Downloads/ai-agent-main"

echo "=== Installing PostgreSQL 16 server + pgvector ==="
apt install -y postgresql-16 postgresql-16-pgvector

echo "=== Installing Redis server ==="
apt install -y redis-server

echo "=== Starting services ==="
pg_ctlcluster 16 main start 2>/dev/null || service postgresql start
sysctl vm.overcommit_memory=1 2>/dev/null || true
redis-server --daemonize yes 2>/dev/null || service redis-server start

echo "=== Creating database and user ==="
su - postgres -c "psql -c \"ALTER USER postgres PASSWORD 'postgres';\""
su - postgres -c "createdb ai_agent_db 2>/dev/null || true"

echo "=== Enabling pgvector extension ==="
su - postgres -c "psql -d ai_agent_db -c 'CREATE EXTENSION IF NOT EXISTS vector;'"

echo "=== Running init.sql ==="
su - postgres -c "psql -d ai_agent_db -f ${SCRIPT_DIR}/docker/postgres-init/init.sql"

echo "=== Installing Python dependencies ==="
cd ${SCRIPT_DIR}
pip install -r requirements.txt

echo "=== Installing frontend dependencies ==="
cd ${SCRIPT_DIR}/frontend
npm install

echo ""
echo "==========================================="
echo "  Setup complete!"
echo "==========================================="
echo ""
echo "Run these in separate terminals:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd ${SCRIPT_DIR} && python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd ${SCRIPT_DIR}/frontend && npm run dev"
echo ""
echo "Then open http://localhost:3000 in your browser."

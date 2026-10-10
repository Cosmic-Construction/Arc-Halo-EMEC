#!/bin/bash
# Arc-Halo Cognitive Fusion Reactor - Database Setup Script
# This script sets up the Neon database schema

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Arc-Halo Cognitive Fusion Reactor Database Setup       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .env file exists
if [ ! -f "db/config/.env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Copying .env.template to .env..."
    cp db/config/.env.template db/config/.env
    echo -e "${RED}Please edit db/config/.env with your Neon database credentials${NC}"
    echo "Then run this script again."
    exit 1
fi

# Load environment variables
source db/config/.env

# Check if NEON_DATABASE_URL is set
if [ -z "$NEON_DATABASE_URL" ]; then
    echo -e "${RED}Error: NEON_DATABASE_URL not set in .env file${NC}"
    exit 1
fi

echo "Database URL configured: ${NEON_DATABASE_URL%%@*}@***"
echo ""

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql not found. Please install PostgreSQL client${NC}"
    echo "On Ubuntu/Debian: sudo apt-get install postgresql-client"
    echo "On macOS: brew install postgresql"
    exit 1
fi

echo -e "${GREEN}Step 1: Testing database connection...${NC}"
if psql "$NEON_DATABASE_URL" -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Failed to connect to database${NC}"
    echo "Please check your NEON_DATABASE_URL in db/config/.env"
    exit 1
fi
echo ""

echo -e "${GREEN}Step 2: Installing required extensions...${NC}"
psql "$NEON_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" || true
# Note: pgvector extension installation may require Neon project configuration
psql "$NEON_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || echo -e "${YELLOW}Warning: vector extension not available (may need to enable in Neon project)${NC}"
echo -e "${GREEN}✓ Extensions configured${NC}"
echo ""

echo -e "${GREEN}Step 3: Deploying database schema...${NC}"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DB_DIR="$SCRIPT_DIR/.."

echo "Applying 01_core_tables.sql..."
psql "$NEON_DATABASE_URL" -f "$DB_DIR/schema/01_core_tables.sql"

echo "Applying 02_tensor_storage.sql..."
psql "$NEON_DATABASE_URL" -f "$DB_DIR/schema/02_tensor_storage.sql"

echo "Applying 03_training_state.sql..."
psql "$NEON_DATABASE_URL" -f "$DB_DIR/schema/03_training_state.sql"

echo "Applying 04_inference_cache.sql..."
psql "$NEON_DATABASE_URL" -f "$DB_DIR/schema/04_inference_cache.sql"

echo "Applying 05_cognitive_fusion.sql..."
psql "$NEON_DATABASE_URL" -f "$DB_DIR/schema/05_cognitive_fusion.sql"

echo "Applying 06_emec_device.sql..."
psql "$NEON_DATABASE_URL" -f "$DB_DIR/schema/06_emec_device.sql"

echo -e "${GREEN}✓ Schema deployment complete${NC}"
echo ""

echo -e "${GREEN}Step 4: Verifying deployment...${NC}"
table_count=$(psql "$NEON_DATABASE_URL" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
echo "Found $table_count tables in the database"

# Expected minimum tables: models, transformer_layers, attention_heads, 
# tensor_metadata, tensor_data, model_weights, embeddings, training_sessions, 
# training_metrics, optimizer_state, model_checkpoints, gradient_checkpoints,
# inference_sessions, activation_cache, kv_cache, inference_metrics, 
# attention_patterns, cognitive_fusion_reactors, reactor_models, 
# fusion_operations, model_interaction_graph, cognitive_state, reactor_metrics
EXPECTED_MIN_TABLES=20

if [ "$table_count" -lt "$EXPECTED_MIN_TABLES" ]; then
    echo -e "${YELLOW}Warning: Expected at least $EXPECTED_MIN_TABLES tables, found $table_count${NC}"
else
    echo -e "${GREEN}✓ Database schema verified successfully${NC}"
fi
echo ""

echo -e "${GREEN}Step 5: Creating sample data (optional)...${NC}"
read -p "Do you want to create sample data for testing? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating sample reactor..."
    psql "$NEON_DATABASE_URL" << EOF
    INSERT INTO cognitive_fusion_reactors (reactor_name, reactor_type, fusion_strategy, status)
    VALUES ('demo-reactor', 'ensemble', 'weighted_average', 'initialized')
    ON CONFLICT (reactor_name) DO NOTHING;
EOF
    echo -e "${GREEN}✓ Sample data created${NC}"
fi
echo ""

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Database Setup Complete!                       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Your Arc-Halo Cognitive Fusion Reactor database is ready!"
echo ""
echo "Next steps:"
echo "  1. Review the schema documentation in db/README.md"
echo "  2. Use the Python utilities in db/scripts/db_utils.py"
echo "  3. Configure GitHub Actions secrets for automated deployments"
echo ""
echo -e "${YELLOW}Security reminder:${NC}"
echo "  - Never commit db/config/.env to version control"
echo "  - Rotate your database credentials regularly"
echo "  - Enable SSL/TLS for all connections"
echo ""

# Database Migrations Guide

## Overview

This guide explains how to manage database schema changes for the Arc-Halo Cognitive Fusion Reactor.

## Migration Strategy

We use a numbered schema file approach where each major component is in its own file:
- `00_master_schema.sql` - Orchestration file (for manual deployment)
- `01_core_tables.sql` - Core model tables
- `02_tensor_storage.sql` - Tensor storage
- `03_training_state.sql` - Training state
- `04_inference_cache.sql` - Inference and caching
- `05_cognitive_fusion.sql` - Cognitive fusion reactor
- `06_emec_device.sql` - EMEC virtual hardware device registry, sessions, telemetry, fault log

## Creating a New Migration

### Step 1: Determine the Scope

Identify which component your changes belong to:
- Model architecture changes → `01_core_tables.sql`
- Tensor/weight changes → `02_tensor_storage.sql`
- Training changes → `03_training_state.sql`
- Inference changes → `04_inference_cache.sql`
- Reactor changes → `05_cognitive_fusion.sql`
- EMEC virtual device changes → `06_emec_device.sql`

### Step 2: Create Migration File

For significant changes that don't fit existing files, create a new numbered file:

```bash
# Create a new migration file
touch db/schema/06_new_feature.sql
```

### Step 3: Write Migration SQL

Follow this template:

```sql
-- Arc-Halo Cognitive Fusion Reactor - [Feature Name]
-- Part N: [Description]

-- Add new tables
CREATE TABLE IF NOT EXISTS new_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_new_table_field ON new_table(field);

-- Add comments
COMMENT ON TABLE new_table IS 'Description of the table';
```

### Step 4: Test Locally

```bash
# Test against local PostgreSQL
createdb arc_halo_test
psql arc_halo_test -f db/schema/06_new_feature.sql

# Verify
psql arc_halo_test -c "\\dt"
```

### Step 5: Update Workflows

If you created a new schema file, update:
1. `.github/workflows/deploy-db-schema.yml` - Add the new file to deployment steps
2. `db/scripts/setup_database.sh` - Add the new file to setup sequence

## Modifying Existing Tables

### Adding Columns

Use `ALTER TABLE` with `IF NOT EXISTS` pattern (PostgreSQL 9.6+):

```sql
-- Add column safely
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='your_table' AND column_name='new_column'
    ) THEN
        ALTER TABLE your_table ADD COLUMN new_column VARCHAR(255);
    END IF;
END $$;
```

### Adding Indexes

Always use `IF NOT EXISTS`:

```sql
CREATE INDEX IF NOT EXISTS idx_table_column ON table_name(column_name);
```

### Dropping Columns (Use with Caution)

Only drop columns if absolutely necessary:

```sql
-- Drop column (CAREFUL - data loss!)
ALTER TABLE your_table DROP COLUMN IF EXISTS old_column;
```

## Rollback Strategy

### Manual Rollback

Create a rollback script for destructive changes:

```sql
-- rollback_06_new_feature.sql
DROP TABLE IF EXISTS new_table CASCADE;
```

### Point-in-Time Recovery

Neon supports point-in-time recovery. Before major changes:

1. Note the current timestamp
2. Apply changes
3. If needed, restore to previous timestamp via Neon console

## Testing Migrations

### Local Testing

```bash
# Create test database
createdb arc_halo_migration_test

# Apply all schemas in order
for i in {01..06}; do
    psql arc_halo_migration_test -f db/schema/${i}_*.sql
done

# Verify
psql arc_halo_migration_test -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```

### CI Testing

The GitHub Actions workflow automatically tests migrations on pull requests.

## Best Practices

### 1. Idempotent Migrations

Always write migrations that can be run multiple times:

```sql
-- Good
CREATE TABLE IF NOT EXISTS my_table (...);

-- Bad
CREATE TABLE my_table (...);
```

### 2. Add Comments

Document your changes:

```sql
COMMENT ON TABLE new_table IS 'Purpose and usage of this table';
COMMENT ON COLUMN new_table.field IS 'What this field represents';
```

### 3. Preserve Data

When modifying columns:

```sql
-- Good: Add new column, migrate data, drop old
ALTER TABLE t ADD COLUMN new_col VARCHAR(255);
UPDATE t SET new_col = old_col;
-- Later: ALTER TABLE t DROP COLUMN old_col;

-- Bad: Drop and recreate
ALTER TABLE t DROP COLUMN col;
ALTER TABLE t ADD COLUMN col VARCHAR(255);
```

### 4. Index Naming Convention

Use descriptive, consistent names:

```sql
-- Pattern: idx_tablename_columnname
CREATE INDEX IF NOT EXISTS idx_models_status ON models(status);
CREATE INDEX IF NOT EXISTS idx_models_created_at ON models(created_at);
```

### 5. Foreign Key Constraints

Define relationships clearly:

```sql
ALTER TABLE child_table 
    ADD CONSTRAINT fk_child_parent 
    FOREIGN KEY (parent_id) 
    REFERENCES parent_table(id) 
    ON DELETE CASCADE;
```

## Handling Production Migrations

### Pre-Migration Checklist

- [ ] Test migration on development database
- [ ] Create database backup (Neon does this automatically)
- [ ] Review migration for performance impact
- [ ] Plan rollback strategy
- [ ] Schedule maintenance window if needed
- [ ] Notify team members

### During Migration

1. Create a Neon branch for safety:
   ```bash
   # Using Neon CLI
   neon branches create --name pre-migration-backup
   ```

2. Apply migration to main database
3. Verify changes
4. Monitor application logs

### Post-Migration

- [ ] Verify all tables and indexes exist
- [ ] Check application functionality
- [ ] Monitor database performance
- [ ] Update documentation
- [ ] Delete backup branch (after verification period)

## Common Migration Scenarios

### Adding a New Model Component

```sql
-- 1. Add table
CREATE TABLE IF NOT EXISTS new_component (
    component_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID NOT NULL REFERENCES models(model_id) ON DELETE CASCADE,
    -- other fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Add indexes
CREATE INDEX IF NOT EXISTS idx_component_model ON new_component(model_id);

-- 3. Add to existing view (if applicable)
CREATE OR REPLACE VIEW v_model_architecture AS
    -- Updated view definition
    ...
```

### Adding Metrics

```sql
-- Extend existing metrics table with new metric types
-- No schema change needed, just insert new metric types:
-- INSERT INTO training_metrics (session_id, metric_type, metric_value, ...)
-- New metric_type values like 'gradient_norm', 'learning_rate_schedule', etc.
```

### Performance Optimization

```sql
-- Add index for slow queries
CREATE INDEX IF NOT EXISTS idx_training_metrics_session_epoch 
    ON training_metrics(session_id, epoch);

-- Add partial index
CREATE INDEX IF NOT EXISTS idx_models_active 
    ON models(model_id) 
    WHERE status = 'active';
```

## Migration Troubleshooting

### Issue: Foreign Key Violations

```sql
-- Check for orphaned records before adding FK
SELECT t1.* FROM child_table t1
LEFT JOIN parent_table t2 ON t1.parent_id = t2.id
WHERE t2.id IS NULL;

-- Clean up orphaned records
DELETE FROM child_table WHERE id IN (...);
```

### Issue: Deadlocks During Migration

Apply migrations during low-traffic periods or:

```sql
-- Use lower lock levels when possible
ALTER TABLE my_table ADD COLUMN new_col VARCHAR(255) DEFAULT NULL;
-- Then update in batches
```

### Issue: Long-Running Migrations

For large tables:

```sql
-- Create new table
CREATE TABLE new_table AS SELECT * FROM old_table LIMIT 0;

-- Migrate in batches
INSERT INTO new_table SELECT * FROM old_table LIMIT 10000 OFFSET 0;
-- Repeat with different offsets

-- Swap tables (requires maintenance window)
BEGIN;
ALTER TABLE old_table RENAME TO old_table_backup;
ALTER TABLE new_table RENAME TO old_table;
COMMIT;
```

## Version Control

Track schema version in database:

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- After each migration
INSERT INTO schema_version (version, description) 
VALUES (6, 'Added new feature tables');
```

---

For questions about migrations, consult the team or review Neon's documentation on schema changes.

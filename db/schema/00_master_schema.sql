-- Arc-Halo Cognitive Fusion Reactor - Master Schema Initialization
-- This file orchestrates the deployment of all schema components

-- Initialize database with required extensions and settings
\echo 'Initializing Arc-Halo Cognitive Fusion Reactor Database...'

-- Set client encoding and timezone
SET client_encoding = 'UTF8';
SET timezone = 'UTC';

-- Execute all schema files in order
-- Note: These paths are relative to where psql is executed
-- For manual execution, adjust paths as needed based on your working directory
\echo 'Creating core tables...'
\i db/schema/01_core_tables.sql

\echo 'Creating tensor storage schema...'
\i db/schema/02_tensor_storage.sql

\echo 'Creating training state schema...'
\i db/schema/03_training_state.sql

\echo 'Creating inference and cache schema...'
\i db/schema/04_inference_cache.sql

\echo 'Creating cognitive fusion schema...'
\i db/schema/05_cognitive_fusion.sql

\echo 'Creating EMEC virtual device schema...'
\i db/schema/06_emec_device.sql

-- Add foreign key constraints that span multiple schema files
\echo 'Adding cross-schema foreign keys...'

-- Link attention heads to weight tensors
ALTER TABLE attention_heads
    ADD CONSTRAINT fk_query_weight FOREIGN KEY (query_weight_id) REFERENCES model_weights(weight_id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_key_weight FOREIGN KEY (key_weight_id) REFERENCES model_weights(weight_id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_value_weight FOREIGN KEY (value_weight_id) REFERENCES model_weights(weight_id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_output_weight FOREIGN KEY (output_weight_id) REFERENCES model_weights(weight_id) ON DELETE SET NULL;

-- Create views for common queries
\echo 'Creating database views...'

-- View: Complete Model Architecture
CREATE OR REPLACE VIEW v_model_architecture AS
SELECT 
    m.model_id,
    m.model_name,
    m.model_type,
    m.version,
    m.status,
    tl.layer_id,
    tl.layer_index,
    tl.layer_type,
    tl.input_dim,
    tl.output_dim,
    tl.num_heads,
    COUNT(mw.weight_id) as total_weights
FROM models m
LEFT JOIN transformer_layers tl ON m.model_id = tl.model_id
LEFT JOIN model_weights mw ON tl.layer_id = mw.layer_id
GROUP BY m.model_id, m.model_name, m.model_type, m.version, m.status,
         tl.layer_id, tl.layer_index, tl.layer_type, tl.input_dim, tl.output_dim, tl.num_heads
ORDER BY m.model_name, tl.layer_index;

COMMENT ON VIEW v_model_architecture IS 'Complete view of model architecture with layers and weight counts';

-- View: Training Progress
CREATE OR REPLACE VIEW v_training_progress AS
SELECT 
    ts.session_id,
    ts.session_name,
    m.model_name,
    ts.status,
    ts.current_epoch,
    ts.total_epochs,
    ROUND((ts.current_epoch::NUMERIC / NULLIF(ts.total_epochs, 0) * 100)::NUMERIC, 2) as progress_percentage,
    tm_loss.metric_value as latest_loss,
    tm_acc.metric_value as latest_accuracy,
    ts.start_time,
    ts.updated_at
FROM training_sessions ts
JOIN models m ON ts.model_id = m.model_id
LEFT JOIN LATERAL (
    SELECT metric_value
    FROM training_metrics
    WHERE session_id = ts.session_id AND metric_type = 'loss'
    ORDER BY epoch DESC, step DESC
    LIMIT 1
) tm_loss ON true
LEFT JOIN LATERAL (
    SELECT metric_value
    FROM training_metrics
    WHERE session_id = ts.session_id AND metric_type = 'accuracy'
    ORDER BY epoch DESC, step DESC
    LIMIT 1
) tm_acc ON true
ORDER BY ts.updated_at DESC;

COMMENT ON VIEW v_training_progress IS 'Real-time view of training session progress and metrics';

-- View: Reactor Status
CREATE OR REPLACE VIEW v_reactor_status AS
SELECT 
    cfr.reactor_id,
    cfr.reactor_name,
    cfr.reactor_type,
    cfr.fusion_strategy,
    cfr.status,
    COUNT(DISTINCT rm.model_id) as active_models,
    COUNT(DISTINCT fo.operation_id) FILTER (WHERE fo.operation_status = 'processing') as active_operations,
    AVG(rm_latest.metric_value) FILTER (WHERE rm_latest.metric_type = 'throughput') as avg_throughput,
    cfr.updated_at
FROM cognitive_fusion_reactors cfr
LEFT JOIN reactor_models rm ON cfr.reactor_id = rm.reactor_id AND rm.is_active = true
LEFT JOIN fusion_operations fo ON cfr.reactor_id = fo.reactor_id
LEFT JOIN LATERAL (
    SELECT metric_type, metric_value
    FROM reactor_metrics
    WHERE reactor_id = cfr.reactor_id
    ORDER BY recorded_at DESC
    LIMIT 1
) rm_latest ON true
GROUP BY cfr.reactor_id, cfr.reactor_name, cfr.reactor_type, 
         cfr.fusion_strategy, cfr.status, cfr.updated_at
ORDER BY cfr.reactor_name;

COMMENT ON VIEW v_reactor_status IS 'Overview of cognitive fusion reactor status and performance';

-- Create functions for common operations
\echo 'Creating helper functions...'

-- Function to calculate total model parameters
CREATE OR REPLACE FUNCTION calculate_model_parameters(p_model_id UUID)
RETURNS TABLE(total_parameters BIGINT, trainable_parameters BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        SUM(tm.total_elements) as total_parameters,
        SUM(CASE WHEN mw.is_trainable THEN tm.total_elements ELSE 0 END) as trainable_parameters
    FROM model_weights mw
    JOIN tensor_metadata tm ON mw.tensor_id = tm.tensor_id
    WHERE mw.model_id = p_model_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_model_parameters IS 'Calculate total and trainable parameters for a model';

-- Function to get latest checkpoint for a model
CREATE OR REPLACE FUNCTION get_latest_checkpoint(p_model_id UUID)
RETURNS UUID AS $$
DECLARE
    v_checkpoint_id UUID;
BEGIN
    SELECT checkpoint_id INTO v_checkpoint_id
    FROM model_checkpoints
    WHERE model_id = p_model_id
    ORDER BY created_at DESC
    LIMIT 1;
    
    RETURN v_checkpoint_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_latest_checkpoint IS 'Get the most recent checkpoint for a model';

-- Create triggers for automatic timestamp updates
\echo 'Creating triggers...'

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_models_updated_at BEFORE UPDATE ON models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tensor_metadata_updated_at BEFORE UPDATE ON tensor_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_model_weights_updated_at BEFORE UPDATE ON model_weights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_training_sessions_updated_at BEFORE UPDATE ON training_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_optimizer_state_updated_at BEFORE UPDATE ON optimizer_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_gradient_checkpoints_updated_at BEFORE UPDATE ON gradient_checkpoints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cognitive_fusion_reactors_updated_at BEFORE UPDATE ON cognitive_fusion_reactors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reactor_models_updated_at BEFORE UPDATE ON reactor_models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_model_interaction_graph_updated_at BEFORE UPDATE ON model_interaction_graph
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cognitive_state_updated_at BEFORE UPDATE ON cognitive_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_emec_devices_updated_at BEFORE UPDATE ON emec_devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_emec_device_sessions_updated_at BEFORE UPDATE ON emec_device_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

\echo 'Arc-Halo Cognitive Fusion Reactor Database Schema Deployment Complete!'
\echo 'Database is ready for LLM transformer model operations.'

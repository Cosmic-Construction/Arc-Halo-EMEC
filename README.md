# Arc-Halo EMEC - Cognitive Fusion & Electromagnetic Energy Conversion

Integrate your application with the Arc-Halo platform. The **Arc-Halo EMEC** system combines sophisticated database-backed LLM transformer model management with advanced electromagnetic energy conversion simulation capabilities.

## 🚀 Features

### Database-Backed LLM Infrastructure
- **Neon PostgreSQL Integration**: Scalable, serverless PostgreSQL database optimized for AI workloads
- **Tensor Storage**: Efficient storage and retrieval of model weights, embeddings, and activations
- **Training State Management**: Complete tracking of training sessions, metrics, and checkpoints
- **Inference Optimization**: KV-cache and activation caching for high-performance inference
- **Multi-Model Fusion**: Cognitive fusion reactor for ensemble and hierarchical model orchestration

### ⚡ NEW: Electromagnetic Energy Conversion (EMEC) Simulator
- **Virtual Engine Model**: Complete electro-mechanical induction motor simulation
- **Maxwell's Equations Solver**: EM field dynamics for rotating electrical machines
- **Polyphase Winding Model**: Three-phase induction winding with flux linkage calculations
- **Rotor & Stator Dynamics**: Coupled mechanical and electrical system simulation
- **Performance Analysis**: Torque, speed, efficiency, and power metrics

### Schema Components

1. **Core Tables**: Model registry, transformer layers, and attention mechanisms
2. **Tensor Storage**: Metadata and binary storage for tensors with chunking support
3. **Training State**: Sessions, metrics, optimizer state, and checkpointing
4. **Inference & Cache**: Session management, KV-cache, and activation caching
5. **Cognitive Fusion**: Multi-model reactors with fusion strategies and interaction graphs
6. **EMEC Module**: Virtual engine simulation for electro-mechanical energy conversion

## 📦 Quick Start

### Prerequisites
- PostgreSQL client (psql) - for database features
- Python 3.8+ (for utilities and EMEC simulator)
- NumPy (for EMEC module)
- Neon database account ([sign up here](https://neon.tech)) - optional, for database features

### Setup

#### For Database Features

1. **Clone the repository**
   ```bash
   git clone https://github.com/Cosmic-Construction/Arc-Halo-EMEC.git
   cd Arc-Halo-EMEC
   ```

2. **Configure database connection**
   ```bash
   cp db/config/.env.template db/config/.env
   # Edit .env with your Neon database credentials
   ```

3. **Run setup script**
   ```bash
   ./db/scripts/setup_database.sh
   ```

4. **Test connection**
   ```bash
   pip install -r db/requirements.txt
   python db/scripts/test_connection.py
   ```

See [db/QUICKSTART.md](db/QUICKSTART.md) for detailed setup instructions.

#### For EMEC Virtual Engine Simulator

1. **Install dependencies**
   ```bash
   pip install numpy
   ```

2. **Run examples**
   ```bash
   python -m emec.examples
   ```

3. **Run tests**
   ```bash
   python -m emec.test_emec
   ```

See [emec/README.md](emec/README.md) for detailed EMEC documentation.

## 🏗️ Architecture

The Arc-Halo EMEC system provides two complementary capabilities:

### 1. Cognitive Fusion Reactor (Database-Backed LLM Infrastructure)

Built on a comprehensive database schema designed for:

- **Model Architecture Management**: Store and version transformer model configurations
- **Tensor Operations**: Efficient tensor storage with support for large models (chunking, compression)
- **Training Lifecycle**: Complete training session tracking with metrics and checkpointing
- **Inference Pipeline**: Optimized caching strategies for production deployments
- **Cognitive Fusion**: Multi-model orchestration with configurable fusion strategies

```
┌─────────────────────────────────────────────────────────┐
│          Arc-Halo Cognitive Fusion Reactor              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Models     │  │   Tensors    │  │   Training   │  │
│  │   Registry   │  │   Storage    │  │    State     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  Inference   │  │   Cognitive  │                     │
│  │   & Cache    │  │    Fusion    │                     │
│  └──────────────┘  └──────────────┘                     │
│                                                          │
├─────────────────────────────────────────────────────────┤
│              Neon PostgreSQL Database                    │
└─────────────────────────────────────────────────────────┘
```

### 2. EMEC Virtual Engine (Electromagnetic Energy Conversion)

A complete electro-mechanical simulator integrating:

- **EM Field Solver**: Maxwell's equations for rotating machines
- **Polyphase Winding Model**: Inductances and flux linkages
- **Rotor Dynamics**: Mechanical motion equations
- **Stator Dynamics**: Electrical voltage/current equations
- **Energy Conversion**: Coupled electro-mechanical simulation

```
┌─────────────────────────────────────────────────────────┐
│              Virtual Engine (EMEC)                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │  EM Field Solver │      │ Polyphase Winding│        │
│  │  (Maxwell Eqs)   │◄────►│     Model        │        │
│  └──────────────────┘      └──────────────────┘        │
│           │                          │                  │
│           │                          │                  │
│           ▼                          ▼                  │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │ Rotor Dynamics   │      │ Stator Dynamics  │        │
│  │ (Mechanics)      │◄────►│  (Electrical)    │        │
│  └──────────────────┘      └──────────────────┘        │
│                                                          │
│                  Torque ◄──► Current                    │
│                  Speed  ◄──► Voltage                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 📚 Documentation

### Technical Architecture
- [**Technical Architecture Specification**](TECHNICAL_ARCHITECTURE.md) - **Comprehensive technical documentation with:**
  - Cross-section diagrams of rotor/stator EM field interaction
  - Complete Maxwell's equations and mathematical formulations
  - Mermaid architecture and data flow diagrams
  - Formal Z++ specifications for all system components
  - Performance specifications and safety properties

### Database & LLM Infrastructure
- [Quick Start Guide](db/QUICKSTART.md) - Get up and running quickly
- [Database README](db/README.md) - Comprehensive database documentation
- [Migration Guide](db/migrations/MIGRATION_GUIDE.md) - Schema management and migrations
- [GitHub Actions](.github/workflows/deploy-db-schema.yml) - Automated deployment workflow

### EMEC Virtual Engine Simulator
- [EMEC README](emec/README.md) - Complete EMEC documentation
- [Bond Graph Guide](emec/BOND_GRAPH_GUIDE.md) - Bond graph theory and neurological analogy
- [Examples](emec/examples.py) - Usage examples and demonstrations
- [Tests](emec/test_emec.py) - Test suite

## ⚡ EMEC Virtual Engine

### Quick Example

```python
from emec import VirtualEngine

# Create a virtual induction motor
engine = VirtualEngine()

# Set load torque
engine.set_load_torque(lambda t, omega: 10.0)  # 10 N⋅m constant load

# Run simulation
engine.simulate(duration=1.0, dt=1e-4)

# Get performance metrics
metrics = engine.get_performance_metrics()
print(f"Speed: {metrics['final_speed_rpm']:.1f} RPM")
print(f"Efficiency: {metrics['avg_efficiency']:.1f}%")
print(f"Torque: {metrics['avg_torque']:.2f} N⋅m")

# Export data for analysis
data = engine.export_data()
```

### Features
- **Maxwell's Equations**: Complete EM field solver
- **Park Transformation**: abc ↔ dq0 reference frames
- **Flux Linkages**: Position-dependent mutual inductances
- **Torque Computation**: Electromagnetic torque calculation
- **Mechanical Dynamics**: Rotor acceleration with friction
- **Three-Phase Supply**: Balanced voltage generation
- **Performance Metrics**: Efficiency, power, speed, torque analysis

See [emec/README.md](emec/README.md) for detailed documentation.

## 🔧 Database Schema

### Core Tables
- `models` - Model registry and configuration
- `transformer_layers` - Layer definitions
- `attention_heads` - Multi-head attention specifications

### Tensor Storage
- `tensor_metadata` - Tensor shape, type, and metadata
- `tensor_data` - Binary tensor storage (chunked)
- `model_weights` - Weight management with gradient tracking
- `embeddings` - Token, position, and segment embeddings

### Training State
- `training_sessions` - Training run tracking
- `training_metrics` - Performance metrics
- `optimizer_state` - Adam, SGD, AdamW state
- `model_checkpoints` - Checkpoint management

### Inference & Cache
- `inference_sessions` - Inference tracking
- `activation_cache` - Activation caching
- `kv_cache` - Key-value cache for generation
- `attention_patterns` - Attention analysis

### Cognitive Fusion
- `cognitive_fusion_reactors` - Multi-model reactors
- `reactor_models` - Model-reactor mappings
- `fusion_operations` - Fusion tracking
- `model_interaction_graph` - Inter-model dependencies

## 🔐 Security

- Never commit `.env` files or database credentials
- Use GitHub Secrets for CI/CD workflows
- Enable SSL/TLS for all database connections
- Rotate credentials regularly
- See [Security Best Practices](db/QUICKSTART.md#security-best-practices)

## 🚀 GitHub Actions

Automated schema deployment via GitHub Actions:
- ✅ SQL syntax validation
- ✅ Local PostgreSQL testing
- ✅ Automated deployment to Neon
- ✅ Deployment reports

Configure `NEON_DATABASE_URL` secret in your repository settings.

## 🛠️ Development

### Database - Python Utilities

```python
from db.scripts.db_utils import NeonDBConnection, ModelRepository

db = NeonDBConnection()
model_repo = ModelRepository(db)

# Create a model
model_id = model_repo.create_model(
    model_name="gpt-fusion-1",
    model_type="transformer",
    architecture_config={"num_layers": 12, "hidden_size": 768},
    version="1.0.0"
)
```

### EMEC - Virtual Engine Development

```python
from emec import (
    VirtualEngine,
    EngineParameters,
    EMFieldSolver,
    PolyphaseWindingModel,
    RotorDynamics,
    StatorDynamics
)

# Create custom engine parameters
params = EngineParameters.create_default(rated_power=10000.0)
params.stator_electrical.rated_voltage = 690.0

# Create engine
engine = VirtualEngine(params)

# Set custom load torque function
def ramp_load(t, omega):
    return 5.0 + 10.0 * min(t / 0.5, 1.0)

engine.set_load_torque(ramp_load)

# Simulate
engine.simulate(duration=2.0)

# Analyze
metrics = engine.get_performance_metrics()
data = engine.export_data()
```

### Database Views

```sql
-- View model architecture
SELECT * FROM v_model_architecture WHERE model_name = 'gpt-fusion-1';

-- Check training progress
SELECT * FROM v_training_progress WHERE status = 'running';

-- Monitor reactor status
SELECT * FROM v_reactor_status WHERE status = 'active';
```

## 📊 Use Cases

### Database & LLM Infrastructure
- **LLM Model Management**: Version control for transformer models
- **Training Infrastructure**: Complete training lifecycle tracking
- **Inference Optimization**: Production-ready caching strategies
- **Model Ensembles**: Cognitive fusion for multi-model systems
- **Research Platform**: Experiment tracking and reproducibility

### EMEC Virtual Engine
- **Motor Design & Analysis**: Performance prediction and optimization
- **Control System Development**: Test controllers before hardware implementation
- **Educational Demonstrations**: Teaching electromagnetic principles
- **Energy Conversion Studies**: Efficiency analysis and optimization
- **Transient Analysis**: Startup, load changes, fault conditions

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:
1. Review the [Migration Guide](db/migrations/MIGRATION_GUIDE.md) for database schema changes
2. Run tests locally before submitting PRs (`python -m emec.test_emec` for EMEC)
3. Ensure GitHub Actions pass
4. Document new features
5. Follow existing code style

## 📝 License

This project is part of the Arc-Halo ecosystem.

## 🔗 Links

### Database & Infrastructure
- [Neon Database](https://neon.tech) - Serverless PostgreSQL
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [pgvector Extension](https://github.com/pgvector/pgvector) - Vector similarity search

### Electromagnetic Theory
- [Maxwell's Equations](https://en.wikipedia.org/wiki/Maxwell%27s_equations)
- [Induction Motor Theory](https://en.wikipedia.org/wiki/Induction_motor)
- [Park Transformation](https://en.wikipedia.org/wiki/Direct-quadrature-zero_transformation)

---

**Arc-Halo EMEC** - Bridging AI model orchestration with electromagnetic energy conversion 🧠⚡🔄

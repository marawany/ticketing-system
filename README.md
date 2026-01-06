# NexusFlow

**Intelligent Ticket Auto-Resolution and Classification System**

NexusFlow is an AI-powered ticket classification system that combines graph-based reasoning, vector similarity search, and LLM judgment to automatically classify and route support tickets with high confidence.

## 🌟 Features

- **3-Level Classification Hierarchy**: Categorizes tickets into Level 1 (main category) → Level 2 (subcategory) → Level 3 (specific issue type)
- **Multi-Source Intelligence**:
  - **Neo4j Graph Database**: Stores classification hierarchy with weighted edges based on historical accuracy
  - **Milvus Vector Database**: Indexes historical tickets for semantic similarity search
  - **LLM as Judge**: Final classification decision using GPT-4o/Claude
- **Ensemble Confidence Scoring**: Combines scores from all sources with calibration
- **Human-in-the-Loop (HITL)**: Routes low-confidence tickets for human review
- **Auto-Learning**: Graph weights automatically update based on HITL corrections
- **Batch Processing**: Efficient handling of large ticket volumes
- **MCP Tools**: FastMCP 2.0 server exposing all tools for agent use
- **Observability**: Arize Phoenix integration for LLM monitoring

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MCP Server    │────▶│  Classification │────▶│   FastAPI       │
│   (FastMCP 2.0) │     │     Agent       │     │   REST API      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                      │                       │
         ▼                      ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Neo4j         │     │   Milvus        │     │   SQLite        │
│   (Graph DB)    │     │   (Vector DB)   │     │   (Persistence) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Neo4j 5.x (running)
- Milvus 2.x (running)
- OpenAI API key (or Azure OpenAI / Anthropic)

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone <repository>
cd ticketing-system

# Install dependencies
make install

# Or with dev dependencies
make dev
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# Required: At least one LLM provider
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...

# Databases (Neo4j Community Edition)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=nexusflow123
NEO4J_DATABASE=neo4j

# Milvus Vector Database
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### 3. Setup Databases

```bash
# Generate synthetic data and load into databases
make setup
```

### 4. Start Services

```bash
# Start API server (port 8000)
make api

# Start MCP server (port 8001)  
make mcp

# Start all services
make all
```

### 5. Access the API

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

## 📖 Usage

### Classify a Single Ticket

```bash
curl -X POST http://localhost:8000/api/v1/classification/classify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cannot reset password after lockout",
    "description": "The reset link keeps expiring before I can use it.",
    "priority": "high"
  }'
```

### Submit a Batch

```bash
curl -X POST http://localhost:8000/api/v1/batch/submit \
  -H "Content-Type: application/json" \
  -d '{
    "tickets": [
      {"title": "Payment failed", "description": "Card declined", "priority": "high"},
      {"title": "Need invoice", "description": "Missing invoice for order", "priority": "low"}
    ]
  }'
```

## 🔧 MCP Tools

The MCP server exposes these tools for agent use:

| Tool | Description |
|------|-------------|
| `classify_ticket` | Full classification pipeline |
| `query_graph_categories` | Query Neo4j for matching categories |
| `search_similar_tickets` | Search Milvus for similar tickets |
| `get_llm_classification` | Get LLM judgment |
| `calculate_confidence` | Combine scores from multiple sources |
| `create_hitl_task` | Create HITL review task |
| `get_category_hierarchy` | Get full classification hierarchy |
| `submit_batch` | Submit batch for processing |

## 📊 Confidence Scoring

NexusFlow uses a sophisticated ensemble approach:

1. **Graph Confidence** (weight: 0.3): Based on keyword matching and historical accuracy
2. **Vector Confidence** (weight: 0.3): Based on similarity to historical tickets
3. **LLM Confidence** (weight: 0.4): Based on LLM's assessment

The final score is calibrated using Platt scaling and component agreement is factored in.

**Routing Thresholds:**
- `> 0.7`: Auto-resolve
- `0.5 - 0.7`: Route to HITL
- `< 0.5`: Escalate

## 🧪 Testing

```bash
# Run all tests
make test

# Run API integration tests
make test-api

# Run unit tests
make test-unit

# Run with coverage
make test-cov
```

## 🐳 Docker

```bash
# Build images
docker compose build

# Start all services
docker compose up -d

# Start with local databases (Neo4j, Milvus)
docker compose --profile local-dbs up -d

# Stop services
docker compose down

# View logs
docker compose logs -f
```

## 📁 Project Structure

```
ticketing-system/
├── src/nexusflow/
│   ├── agents/              # Classification agent (LangGraph)
│   ├── api/                 # FastAPI routes
│   ├── db/                  # Database clients
│   ├── mcp/                 # MCP server (FastMCP 2.0)
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   └── observability/       # Phoenix integration
├── frontend/                # Next.js frontend
├── scripts/                 # Setup and test scripts
├── data/                    # Synthetic data
├── tests/                   # Test suite
├── Dockerfile               # Backend Dockerfile
├── docker-compose.yml       # Docker Compose config
├── Makefile                 # Development commands
└── pyproject.toml           # Python dependencies
```

## 🔑 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `NEO4J_URI` | Neo4j connection URI | `bolt://localhost:7687` |
| `NEO4J_DATABASE` | Neo4j database name | `neo4j` |
| `MILVUS_HOST` | Milvus host | `localhost` |
| `CLASSIFICATION_CONFIDENCE_THRESHOLD` | Auto-resolve threshold | `0.7` |
| `HITL_THRESHOLD` | HITL routing threshold | `0.5` |
| `BATCH_SIZE` | Batch processing size | `50` |

## 📈 Observability

NexusFlow integrates with Arize Phoenix for LLM observability:

```bash
# Start Phoenix
make phoenix

# Access Phoenix UI
open http://localhost:6006
```

## 🚢 Deployment

For production deployment:

1. Build the Docker image
2. Push to your container registry
3. Deploy using Kubernetes or your preferred orchestration

```bash
# Build for production
docker build -t nexusflow:latest .

# Tag and push to registry
docker tag nexusflow:latest your-registry.io/nexusflow:latest
docker push your-registry.io/nexusflow:latest
```

## 📝 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines first.

# ♎ LibraRAG: Advanced Agentic RAG Pipeline

LibraRAG (formerly KensakuRAG) is a highly concurrent, production-grade Retrieval-Augmented Generation (RAG) backend. Instead of relying on a linear or static pipeline, LibraRAG utilizes **LangGraph** to construct a dynamic, stateful directed acyclic graph (DAG) that acts as an intelligent routing and orchestration engine.

The system is designed to run locally, ensuring absolute data privacy while leveraging state-of-the-art retrieval mechanisms and local Small Language Models (SLMs) via Ollama (e.g., `qwen2.5:7b`).

---

## 🌟 Key Features

1. **Intelligent LangGraph Orchestration**: Queries are evaluated by an LLM router. Conversational intents ("Hello", "Thanks") bypass heavy computation, while information-seeking intents trigger full contextual retrieval.
2. **Hybrid Dual-Retrieval**: Leverages both Dense embeddings (ChromaDB + SentenceTransformers) for semantic matching, and Sparse indexing (Okapi BM25) for exact keyword matching.
3. **Parent-Child Chunking**: Retrieves granular, high-fidelity chunks while passing broader, parent-level context to the LLM to prevent context fragmentation.
4. **Massive Parallel Context Fetching**: Runs local hybrid retrieval (with Multi-Query Expansion) concurrently with live internet searches via the Tavily API.
5. **Reciprocal Rank Fusion (RRF)**: Merges disparate dense and sparse search results without scale calibration issues.
6. **Cross-Encoder Reranking**: Uses `BAAI/bge-reranker-v2-m3` to prune irrelevant documents from the merged context pool via transformer self-attention.
7. **Automated LLM Evaluation**: Computes probabilistic Faithfulness and Hallucination scores for every generated response.
8. **Stateless Persistence**: Ensures thread-safe concurrency by hydrating session memory per-request from a SQLite database via SQLAlchemy.

---

## 🛠️ System Architecture

### 1. Ingestion Layer (`ingestion/`)
Documents (PDFs) are parsed using `PyMuPDFLoader`. The system employs a Parent-Child chunking heuristic:
- **Parent Chunks** (~2000 tokens): Indexed using BM25.
- **Child Chunks** (~400 tokens): Embedded using `all-MiniLM-L6-v2` into ChromaDB.
When a child chunk matches a dense search, its corresponding parent chunk is yielded.

### 2. Retrieval Layer (`retrieval/`)
- **Multi-Query Expansion**: The LLM generates semantic variations of the user's query.
- **Hybrid Fetch**: Retrieves from both dense and sparse indices.
- **Web Search**: Integrates `tavily-python` for real-time web context.

### 3. Processing Layer (`generation/`)
- **Reranking**: A cross-encoder scores the query against all retrieved documents.
- **Compression**: An LLM-based `ContextCompressor` extracts only the explicit sentences relevant to the query to minimize context window bloat.
- **Citation Building**: Injects `[Source X]` markers into the context block with hyperlinked URLs for web documents and filenames for local PDFs.

### 4. Graph Orchestration (`pipeline.py`)
The pipeline runs on LangGraph using a strictly typed `GraphState`. 
- State includes `session_id`, `rewritten_query`, `all_retrieved_docs`, and granular latency metrics for frontend observability.
- The state graph dynamically routes the execution and merges the final evaluated response.

---

## 🚀 Getting Started

### Prerequisites
1. **Python 3.10+**
2. **Ollama**: Must be installed and running locally with the `qwen2.5:7b` model pulled (`ollama run qwen2.5:7b`).
3. **API Keys**: Required for web searching and ngrok tunneling.

### Installation

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd agentic-course
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your Environment Variables:
   Create a `.env` file in the root directory:
   ```env
   TAVILY_API_KEY=your_tavily_key
   NGROK_AUTHTOKEN=your_ngrok_token
   # Add other required API keys here
   ```

### Running the Backend

Start the FastAPI application using Uvicorn:
```bash
cd LibraRAG
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Upon startup, the application will:
1. Ingest documents located in `../data/raw/pdfs`.
2. Generate dense and sparse vector stores.
3. Establish a public Ngrok tunnel (bypassing local NATs) so your external frontends can interact with the API securely.

---

## 📊 API Endpoints

- **`POST /api/chat`**: The primary interaction endpoint. 
  - **Payload**: `{"query": "string", "session_id": "uuid"}`
  - **Response**: Returns the generated answer, extracted references, evaluation metrics, and granular step-by-step latency profiling.
- **`POST /api/ingest`**: Triggers a manual re-ingestion of the document directory.
- **`GET /health`**: Standard system health check.

---

## 🧠 Database & Observability

All session data is persisted in a local `sessions.db` SQLite database.
- **Session Memory**: Handled by SQLAlchemy. Each `/api/chat` request hydrates a temporary `ConversationalMemory` object to prevent thread collision.
- **Query Logs**: Every query, generated answer, and its associated metrics (routing time, web search time, reranking time, faithfulness score) are logged persistently for analytics dashboards.

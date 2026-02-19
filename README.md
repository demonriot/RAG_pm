# Enterprise Engineering Knowledge Copilot

A robust RAG (Retrieval-Augmented Generation) system designed for enterprise knowledge management. This project provides an asynchronous document ingestion pipeline, supporting multiple formats, version control, and scalable storage.

## 🚀 Key Features

*   **Document Ingestion**: Supports uploading PDF, Markdown, HTML, and TXT files.
*   **Asynchronous Processing**: Uses Redis-backed queues for background processing to handle large volumes of documents without blocking the API.
*   **Versioning**: Tracks document versions, status (queued, processing, done, failed), and history.
*   **Scalable Architecture**:
    *   **FastAPI**: High-performance API for ingestion and status checks.
    *   **PostgreSQL + pgvector**: Relational data and vector similarity search.
    *   **MinIO**: S3-compatible object storage for raw document files.
    *   **Redis**: High-performance task queue.

## 🛠️ Tech Stack

*   **Language**: Python 3.11
*   **Web Framework**: FastAPI
*   **Database**: PostgreSQL 15, SQLAlchemy (ORM), pgvector (Vector Store)
*   **Storage**: MinIO (S3 Compatible)
*   **Task Queue**: Redis
*   **Containerization**: Docker & Docker Compose

## 📂 Project Structure

```
llmops/
├── app/
│   ├── api/            # API Endpoints (Upload, Status)
│   ├── core/           # Configuration & Settings
│   ├── db/             # Database Models & Session Management
│   ├── ingestion/      # Worker Logic, Queue, & Storage Wrappers
│   └── main.py         # App Entrypoint
├── docker/             # Dockerfiles for API and Worker
├── alembic/            # Database Migrations
├── docker-compose.yml  # Orchestration
└── requirements.txt    # Python Dependencies
```

## 🏁 Getting Started

### Prerequisites

*   [Docker](https://www.docker.com/) installed on your machine.
*   [Docker Compose](https://docs.docker.com/compose/) installed.

### Installation & Running

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd llmops
    ```

2.  **Environment Configuration**:
    Create a `.env` file in the root directory (if not present) with necessary configurations. _(See `docker-compose.yml` for default environment variables used in containers)_.

3.  **Start Services**:
    Run the following command to build and start the API, Worker, Database, Redis, and MinIO:
    ```bash
    docker-compose up --build
    ```

4.  **Access Components**:
    *   **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
    *   **MinIO Console**: [http://localhost:9001](http://localhost:9001) (User: `minio`, Pass: `minio123`)

## 🔌 API Usage

### 1. Upload a Document

**Endpoint**: `POST /ingest/upload`

**Form Data**:
*   `file`: The document to upload.
*   `title`: Document title.
*   `doc_type`: Type (e.g., `md`, `txt`, `html`).
*   `tags`: (Optional) Comma-separated tags.

**Response**:
```json
{
  "doc_id": "uuid...",
  "version_id": "uuid...",
  "status": "queued"
}
```

### 2. Check Ingestion Status

**Endpoint**: `GET /ingest/status/{version_id}`

**Response**:
```json
{
  "version_id": "uuid...",
  "status": "done",
  "error_code": null,
  "ingested_at": "2023-10-27T10:00:00Z"
}
```

## 🧩 Data Model

*   **Documents**: Stores metadata like title and type.
*   **DocumentVersions**: Tracks ingestion attempts and status for each document.
*   **Chunks**: Text segments extracted from documents.
*   **Embeddings**: Vector representations of chunks (Model defined, generation logic pending in worker).

## ⚠️ Current Status & Known Issues

*   **Embedding Generation**: The database model for embeddings (`ChunkEmbedding`) exists, but the worker logic for generating embeddings (e.g., using OpenAI or local models) is currently not implemented in the ingestion pipeline.
*   **Parser**: Currently supports simple text-based formats (`txt`, `md`, `html`). PDF and complex parsing logic are placeholders.

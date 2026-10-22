# 🚀 Zomato Modern Data & AI Analytics Platform

[![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?style=for-the-badge&logo=snowflake&logoColor=white)](https://www.snowflake.com/)
[![dbt](https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow%203-017CEE?style=for-the-badge&logo=Apache%20Airflow&logoColor=white)](https://airflow.apache.org/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)

An end-to-end modern enterprise data engineering and GenAI platform built on transactional food delivery data. The platform automates batch ingestion from cloud storage to Snowflake, orchestrates multi-tiered dimensional warehouse modeling in dbt via Apache Airflow 3, enriches customer reviews using Google Gemini LLMs, and delivers interactive self-service analytics through Streamlit.

---

## 📌 Architecture Overview

```mermaid
flowchart TD
    subgraph Ingestion ["1. Data Ingestion & Storage"]
        A[Raw CSVs: Orders, Reviews, Users, etc.] --> B[AWS S3 Bucket / Snowflake Stage]
        B --> C[Snowflake RAW Schema]
    end

    subgraph Airflow ["2. Airflow 3 Orchestration (DAG: zomato_batch)"]
        C --> D[Task 1: reload_raw - Batch Ingest]
        D --> E[Task 2: dbt_build_core - Staging & Core Marts]
        E --> F[Task 3: enrich_reviews - Gemini Flash LLM Batch Job]
        F --> G[Task 4: dbt_build_ai - dbt build tag:ai]
    end

    subgraph SnowflakeWarehouse ["3. Snowflake Transformation Layers"]
        E --> H[(STAGING Views)]
        H --> I[(MARTS Dimensional & Fact Tables)]
        F --> J[(AI.REVIEW_ENRICHED Table)]
        G --> K[(MARTS.MART_REVIEW_INSIGHTS Table)]
    end

    subgraph GenAIApps ["4. GenAI Analytics Layer (Streamlit)"]
        I & K --> L[Text-to-SQL Assistant: Query Snowflake in English]
        H & J --> M[RAG Review Chatbot: Vector Search on Feedback]
    end
```

---

## ✨ Key Features

- **Decoupled Airflow 3.x Orchestration:** Containerized Airflow with separated `api-server`, standalone `dag-processor`, and an isolated Python virtual environment for dbt execution.
- **Dimensional Data Modeling with dbt:**
  - **Staging Layer:** Lightly cleansed views (`stg_orders`, `stg_reviews`, `stg_restaurants`, `stg_users`, `stg_food`, `stg_menu`).
  - **Core Marts:** Star-schema fact tables (`fct_orders`, `fact_order_items`), dimension tables (`dim_customer`, `dim_restaurants`, `dim_food`, `dim_date`), and domain marts (`mart_daily_city_revenue`, `mart_delivery_sla`, `mart_restaurant_performance`).
  - **AI Insights Mart:** `mart_review_insights` joining customer review dimensions with LLM-extracted sentiment and defect categories.
- **LLMOps Review Enrichment:**
  - Automated sentiment scoring, topic tagging (`food quality`, `delivery`, `pricing`, `service`, `packaging`), and root-cause extraction via **Google Gemini Flash**.
  - Idempotent incremental loading into Snowflake `AI` schema.
- **Self-Service GenAI Applications:**
  - **Text-to-SQL Assistant (`ai/text_to_sql.py`):** Translates natural language into Snowflake SQL queries with built-in safety guardrails against destructive DDL/DML.
  - **RAG Review Chatbot (`ai/rag_chat.py`):** Vector search powered by `gemini-embedding-001` with local Parquet caching and grounded context generation.

---

## 📂 Repository Structure

```
.
├── airflow/
│   ├── dags/
│   │   └── zomato_batch.py         # Airflow 3 DAG orchestrating ELT + AI steps
│   ├── docker-compose.yaml         # Airflow 3 + Postgres multi-container setup
│   ├── Dockerfile                  # Airflow image with dbt venv, Snowflake & Gemini
│   └── .env.example                # Airflow credentials template
├── zomato/                         # dbt Project
│   ├── dbt_project.yml
│   ├── profiles.example.yml        # dbt Snowflake profile template
│   └── models/
│       ├── staging/                # Staging views & source YAMLs
│       └── marts/                  # Fact, Dimension & AI Mart tables
├── ai/                             # GenAI & Streamlit Applications
│   ├── enrich_reviews.py           # Gemini batch review classification
│   ├── text_to_sql.py              # Streamlit Text-to-SQL application
│   ├── rag_chat.py                 # Streamlit RAG review search application
│   └── .env.example                # AI apps environment template
└── .gitignore                      # Excludes large CSVs, logs, and credentials
```

---

## ⚡ Quickstart & Setup Guide

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/) installed and running
- [Python 3.10+](https://www.python.org/)
- Snowflake account with permissions to create databases and warehouses
- Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/)

### 2. Configure Environment Variables
Copy and fill in the example configuration files:
```bash
# Airflow config
cp airflow/.env.example airflow/.env

# AI Apps config
cp ai/.env.example ai/.env

# dbt profile config
cp zomato/profiles.example.yml zomato/profiles.yml
```

### 3. Launch Airflow Pipeline
```bash
cd airflow
docker compose up -d --build
```
- Open Airflow UI: **http://localhost:8080** (Username: `admin`, Password: `admin`)
- Unpause and trigger the `zomato_batch` DAG.

### 4. Run dbt Standalone (Optional)
```bash
cd zomato
dbt run --profiles-dir .
dbt test --profiles-dir .
```

### 5. Launch the Streamlit Applications
```bash
cd ai

# 1. Text-to-SQL Analytics Assistant
streamlit run text_to_sql.py

# 2. RAG Review Semantic Search Chatbot
streamlit run rag_chat.py
```

---

## 🛡️ Security & Privacy
- **No Credentials in Repo:** Sensitive environment variables, passwords, and API keys are strictly excluded via `.gitignore`.
- **Large Files:** Multi-gigabyte raw data files (`*.csv`, `*.parquet`) are ignored to comply with GitHub file size constraints.
- **SQL Safety:** The Text-to-SQL engine strictly disallows DDL/DML statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, etc.) and runs under read-only warehouse roles.

# Product canonicalization

A Python pipeline I built at Auricore to turn inconsistent luxury-product listings into a common catalog. It combines source-quality heuristics, optional AI attribute extraction, visual-search enrichment, and a manual duplicate-review workflow.

This is a historical source snapshot, published as a portfolio project. It requires your own data and cloud resources; it is not a hosted demo.

## The problem

The same product appears across retailers with different names, categories, pricing text, and model identifiers. Normalizing those listings means deciding which source to trust while retaining the details that distinguish one product from another.

## Implementation

- **Source selection:** score original and enriched names using retailer-specific heuristics and content-quality checks.
- **Attribute extraction:** batch product records through an optional Anthropic parser, with JSON repair and heuristic fallbacks.
- **Enrichment:** use asynchronous, rate-limited SerpAPI visual searches to gather additional product information.
- **Classification:** combine URL patterns, keywords, and optional AI classification.
- **Storage and review:** persist canonical records in DynamoDB and provide an interactive workflow for reviewing and merging flagged duplicate pairs.
- **Embeddings:** optional local CLIP image embeddings and cosine similarity utilities. The main runner skips embeddings by default.

```mermaid
flowchart LR
    A[Source listings in DynamoDB] --> B[Source-quality scoring]
    B --> C[Optional visual search and AI parsing]
    C --> D[Category and attribute normalization]
    D --> E[Canonical catalog in DynamoDB]
    E --> F[Manual duplicate review]
```

## Explore the code

| File | Responsibility |
| --- | --- |
| [`src/canonicalizer.py`](src/canonicalizer.py) | Batch orchestration, source scoring, normalized names, and persistence |
| [`src/utils/ai_product_parser.py`](src/utils/ai_product_parser.py) | Batched attribute extraction and response handling |
| [`src/utils/async_serp_api_client.py`](src/utils/async_serp_api_client.py) | Concurrent visual-search enrichment |
| [`src/utils/category_classifier.py`](src/utils/category_classifier.py) | URL, keyword, and model-based classification |
| [`src/duplicate_reviewer.py`](src/duplicate_reviewer.py) | Human review and merge decisions |
| [`src/embedding_generator.py`](src/embedding_generator.py) | Optional embedding and similarity utilities |

## Local setup

Use Python 3.10 or newer, a virtual environment, and your own AWS development account.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your own source and destination table names. AWS authentication uses the standard boto3 credential chain, including local profiles or workload roles. Supply API keys only if you enable the optional providers. Keep `.env` out of Git.

The source table must contain the product records expected by the pipeline; no original catalog data is included. `scripts/setup_tables.py` creates the destination table. `scripts/run_canonicalization.py` reads source records and writes canonical records. The review and cleanup scripts can modify or delete database records, so use disposable development tables when exploring them.

```bash
python scripts/setup_tables.py
python scripts/run_canonicalization.py
```

Install OpenAI's CLIP package separately if you want to explore local image embeddings. Model weights are downloaded when that mode initializes.

## Status and limitations

- All 21 Python files passed syntax validation when this snapshot was prepared.
- Gitleaks found no secrets in the source snapshot or its published history.
- Cloud integrations, provider responses, model quality, and database writes have not been retested for this publication. Dependencies retain their historical version ranges.
- The OpenAI embedding path is a placeholder. Several embedding error paths fall back to deterministic dummy vectors; those vectors must not be used to judge real product similarity.
- The legacy synchronous SerpAPI fallback references a removed module. Install the listed `aiohttp` dependency for the included async client and compatibility wrapper.
- Name preservation and classification use heuristics and require evaluation on your own data. No accuracy or throughput benchmark is claimed.

## Provenance

Written by Jai Ashar for Auricore. This snapshot is derived from `Auricore/luxury-product-canonicalization` at commit `21e1391e2974f1fbb2b4027d785c9f4051786810`. The original repository's two commits are attributed to Jai Ashar. Publication adds documentation, an empty environment template, and ignore rules; the historical application code is unchanged.

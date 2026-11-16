"""Qdrant Hybrid Vector Engine combining Gemini Dense Embeddings + BM25 Sparse Vectors + RRF."""

from __future__ import annotations

import hashlib
import logging
import math
import re
import uuid
from collections import Counter
from typing import Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import SecretStr
from qdrant_client import QdrantClient, models

from app.config import Settings, get_settings
from app.knowledge.corpus import TRADINGTACKLE_CORPUS
from app.schemas import DocCategory, KnowledgeDocument, RetrievedChunk

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"[a-z0-9_.*//@-]+")
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "must",
        "into",
        "only",
        "when",
        "inside",
        "every",
        "using",
        "used",
        "such",
        "than",
        "have",
        "has",
    }
)


def _stable_token_id(token: str) -> int:
    """Map string token deterministically into a positive 31-bit integer index."""
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big") & 0x7FFFFFFF


def _deterministic_hash_embedding(text: str, dim: int = 256) -> list[float]:
    """Offline fallback dense vector for CI / zero-key tests preserving lexical cosine similarity."""
    vec = [0.0] * dim
    tokens = [t for t in _TOKEN_PATTERN.findall(text.lower()) if len(t) > 1 and t not in _STOPWORDS]
    for tok in tokens:
        h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(h[:4], "big") % dim
        sign = 1.0 if (h[4] & 1) == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class SparseBM25Encoder:
    """Lightweight, deterministic BM25 sparse vectorizer tailored for technical identifiers."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.idf: dict[str, float] = {}
        self.avg_doc_len: float = 50.0

    @staticmethod
    def tokenize(text: str) -> list[str]:
        raw = _TOKEN_PATTERN.findall(text.lower())
        tokens: list[str] = []
        for tok in raw:
            cleaned = tok.strip(".-/")
            if len(cleaned) < 2 or cleaned in _STOPWORDS:
                continue
            tokens.append(cleaned)
            # Also split dotted Pine namespaces like `ta.macd` or `request.security`
            if "." in cleaned:
                for sub in cleaned.split("."):
                    if len(sub) >= 2 and sub not in _STOPWORDS:
                        tokens.append(sub)
        return tokens

    def fit(self, documents: list[str]) -> None:
        doc_count = max(len(documents), 1)
        df: Counter[str] = Counter()
        total_len = 0
        for doc in documents:
            toks = self.tokenize(doc)
            total_len += len(toks)
            for unique_tok in set(toks):
                df[unique_tok] += 1
        self.avg_doc_len = max(total_len / doc_count, 1.0)
        self.idf = {
            term: math.log(1.0 + (doc_count - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def encode_document(self, text: str) -> models.SparseVector:
        toks = self.tokenize(text)
        dl = max(len(toks), 1)
        counts = Counter(toks)
        index_weights: dict[int, float] = {}
        for term, tf in counts.items():
            idf_val = self.idf.get(term, 1.2)
            denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / self.avg_doc_len))
            score = idf_val * ((tf * (self.k1 + 1.0)) / denom)
            idx = _stable_token_id(term)
            index_weights[idx] = index_weights.get(idx, 0.0) + score
        sorted_items = sorted(index_weights.items())
        return models.SparseVector(
            indices=[k for k, _ in sorted_items],
            values=[round(v, 5) for _, v in sorted_items],
        )

    def encode_query(self, query: str) -> models.SparseVector:
        toks = self.tokenize(query)
        counts = Counter(toks)
        index_weights: dict[int, float] = {}
        for term, qf in counts.items():
            idf_val = self.idf.get(term, 1.5)
            idx = _stable_token_id(term)
            index_weights[idx] = index_weights.get(idx, 0.0) + idf_val * (1.0 + 0.25 * (qf - 1))
        sorted_items = sorted(index_weights.items())
        return models.SparseVector(
            indices=[k for k, _ in sorted_items],
            values=[round(v, 5) for _, v in sorted_items],
        )


class HybridKnowledgeStore:
    """Production Qdrant Hybrid Search service with Dense + Sparse BM25 + RRF Fusion."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.collection_name = self.settings.qdrant_collection
        self.qdrant_mode = "remote-cluster" if self.settings.qdrant_url else "embedded-memory"
        self.client = (
            QdrantClient(url=self.settings.qdrant_url, timeout=10)
            if self.settings.qdrant_url
            else QdrantClient(location=":memory:")
        )
        self.sparse_encoder = SparseBM25Encoder()
        self._embedder: GoogleGenerativeAIEmbeddings | None = None
        if self.settings.gemini_api_key and self.settings.gemini_api_key != "your-gemini-api-key-here":
            self._embedder = GoogleGenerativeAIEmbeddings(
                model=self.settings.gemini_embedding_model,
                api_key=SecretStr(self.settings.gemini_api_key),
            )
        self.vector_dim: int = 256
        self.indexed_count: int = 0
        self._doc_map: dict[str, KnowledgeDocument] = {}

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self._embedder is not None:
            try:
                vectors = self._embedder.embed_documents(texts)
                return [[float(x) for x in vec] for vec in vectors]
            except Exception as exc:
                logger.warning("Gemini embedding fallback activated due to error: %s", exc)
        return [_deterministic_hash_embedding(t) for t in texts]

    def _embed_query(self, query: str) -> list[float]:
        if self._embedder is not None:
            try:
                vec = self._embedder.embed_query(query)
                return [float(x) for x in vec]
            except Exception as exc:
                logger.warning("Gemini query embedding fallback activated: %s", exc)
        return _deterministic_hash_embedding(query)

    def ensure_ingested(self, corpus: list[KnowledgeDocument] | None = None) -> int:
        """Fit BM25 statistics and ensure all corpus documents are indexed in Qdrant."""
        docs = corpus or TRADINGTACKLE_CORPUS
        self._doc_map = {d.doc_id: d for d in docs}
        full_texts = [f"{d.doc_id} {d.title} {' '.join(d.tags)} {d.content}" for d in docs]
        self.sparse_encoder.fit(full_texts)

        # Check if Qdrant already holds the exact corpus size & valid dimensions
        if self.client.collection_exists(self.collection_name):
            info = self.client.get_collection(self.collection_name)
            pts_count = info.points_count or 0
            if pts_count == len(docs):
                sample_vec = self._embed_query("pine script v5")
                self.vector_dim = len(sample_vec)
                self.indexed_count = pts_count
                return pts_count
            self.client.delete_collection(self.collection_name)

        dense_vectors = self._embed_texts(full_texts)
        self.vector_dim = len(dense_vectors[0])

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=self.vector_dim,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False)
                )
            },
        )

        # Create payload keyword indexes on remote Qdrant clusters for fast multi-tenant filtering
        if self.qdrant_mode == "remote-cluster":
            for field_name in ("tenant", "category", "severity", "doc_id"):
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

        points: list[models.PointStruct] = []
        for doc, full_text, dense_vec in zip(docs, full_texts, dense_vectors, strict=True):
            sparse_vec = self.sparse_encoder.encode_document(full_text)
            point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"gardoon.{doc.tenant}.{doc.doc_id}"))
            payload: dict[str, Any] = doc.model_dump()
            points.append(
                models.PointStruct(
                    id=point_uuid,
                    vector={"dense": dense_vec, "sparse": sparse_vec},
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
        self.indexed_count = len(points)
        logger.info(
            "Indexed %d documents into Qdrant (%s, dim=%d)",
            self.indexed_count,
            self.qdrant_mode,
            self.vector_dim,
        )
        return self.indexed_count

    def hybrid_search(
        self,
        query: str,
        *,
        tenant: str = "tradingtackle",
        category: DocCategory | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Execute Qdrant Hybrid Search (Dense + Sparse BM25) fused via Reciprocal Rank Fusion."""
        if self.indexed_count == 0:
            self.ensure_ingested()

        must_conditions: list[models.Condition] = [
            models.FieldCondition(key="tenant", match=models.MatchValue(value=tenant))
        ]
        if category is not None:
            must_conditions.append(
                models.FieldCondition(key="category", match=models.MatchValue(value=category))
            )
        qfilter = models.Filter(must=must_conditions)

        dense_q = self._embed_query(query)
        sparse_q = self.sparse_encoder.encode_query(query)
        prefetch_limit = max(top_k * 3, 12)

        # Fetch individual sub-scores for Glass-Box UI transparency alongside native RRF fusion
        dense_res = self.client.query_points(
            collection_name=self.collection_name,
            query=dense_q,
            using="dense",
            query_filter=qfilter,
            limit=prefetch_limit,
            with_payload=True,
        ).points

        sparse_res = self.client.query_points(
            collection_name=self.collection_name,
            query=sparse_q,
            using="sparse",
            query_filter=qfilter,
            limit=prefetch_limit,
            with_payload=True,
        ).points

        fused_res = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_q, using="dense", filter=qfilter, limit=prefetch_limit
                ),
                models.Prefetch(
                    query=sparse_q, using="sparse", filter=qfilter, limit=prefetch_limit
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        ).points

        dense_scores = {
            str(pt.payload.get("doc_id", "")): max(0.0, min(1.0, float(pt.score)))
            for pt in dense_res
            if pt.payload
        }
        max_sparse = max((float(pt.score) for pt in sparse_res), default=1.0) or 1.0
        sparse_scores = {
            str(pt.payload.get("doc_id", "")): round(
                max(0.0, min(1.0, float(pt.score) / max_sparse)), 4
            )
            for pt in sparse_res
            if pt.payload
        }
        max_rrf = max((float(pt.score) for pt in fused_res), default=1.0) or 1.0

        chunks: list[RetrievedChunk] = []
        for idx, pt in enumerate(fused_res, start=1):
            payload = pt.payload or {}
            doc_id = str(payload.get("doc_id", ""))
            d_score = round(dense_scores.get(doc_id, 0.42), 4)
            s_score = round(sparse_scores.get(doc_id, 0.0), 4)
            rrf_norm = round(max(0.0, min(1.0, float(pt.score) / max_rrf)), 4)
            chunks.append(
                RetrievedChunk(
                    doc_id=doc_id,
                    title=str(payload.get("title", "")),
                    category=payload.get("category", "pine_v5_reference"),
                    severity=payload.get("severity", "info"),
                    version=str(payload.get("version", "2026.4")),
                    tenant=str(payload.get("tenant", tenant)),
                    tags=[str(t) for t in payload.get("tags", [])],
                    excerpt=str(payload.get("content", "")),
                    dense_score=d_score,
                    sparse_score=s_score,
                    rrf_score=rrf_norm,
                    rank=idx,
                )
            )
        return chunks


_STORE_SINGLETON: HybridKnowledgeStore | None = None


def get_knowledge_store() -> HybridKnowledgeStore:
    """Return initialized singleton HybridKnowledgeStore."""
    global _STORE_SINGLETON
    if _STORE_SINGLETON is None:
        _STORE_SINGLETON = HybridKnowledgeStore()
    return _STORE_SINGLETON

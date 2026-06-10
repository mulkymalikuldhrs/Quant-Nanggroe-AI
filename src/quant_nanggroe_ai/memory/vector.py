"""
Vector Memory — In-Memory Vector Store with TF-IDF Embeddings
==============================================================
Lightweight vector store for semantic search without external
dependencies (no ChromaDB, Pinecone, etc. required).

Features:
    - TF-IDF style embeddings (no neural network required)
    - Cosine similarity search
    - Document metadata support
    - Incremental vocabulary building
    - Efficient numpy-based similarity computation

How it works:
    1. Documents are tokenized into words (lowercased, stripped punctuation)
    2. A vocabulary is built from all seen documents
    3. Each document is embedded as a TF-IDF vector
    4. Queries are embedded the same way
    5. Cosine similarity finds the k most similar documents

This is suitable for:
    - Research note retrieval
    - Strategy description matching
    - Knowledge base queries
    - Context retrieval for LLM augmentation

Not suitable for:
    - Large-scale production (>100k documents)
    - Semantic understanding beyond keyword matching
    - Real-time streaming updates

For production, swap to ChromaDB, Pinecone, or Weaviate.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# DOCUMENT MODEL
# ══════════════════════════════════════════════════════════════════════


class VectorDocument(BaseModel):
    """A document stored in the vector memory."""

    doc_id: str = ""
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] = Field(default_factory=list)
    token_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SearchResult(BaseModel):
    """A single search result from the vector store."""

    doc_id: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════
# TOKENIZER
# ══════════════════════════════════════════════════════════════════════


class SimpleTokenizer:
    """
    Simple whitespace tokenizer with basic preprocessing.

    - Lowercases text
    - Removes punctuation (keeps alphanumeric + spaces)
    - Removes common English stop words
    - Stems words with a simple suffix-stripping heuristic
    """

    STOP_WORDS = frozenset({
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "it", "as", "was", "are", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "shall", "not", "no",
        "this", "that", "these", "those", "i", "me", "my", "we", "our",
        "you", "your", "he", "she", "they", "them", "their", "its",
    })

    @classmethod
    def tokenize(cls, text: str) -> list[str]:
        """
        Tokenize text into words.

        Args:
            text: Input text

        Returns:
            List of processed tokens
        """
        # Lowercase and remove non-alphanumeric
        cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        # Split and filter
        tokens = [
            t for t in cleaned.split()
            if t and t not in cls.STOP_WORDS and len(t) > 1
        ]
        return tokens

    @classmethod
    def simple_stem(cls, word: str) -> str:
        """
        Very basic suffix-stripping stemmer.

        Handles common English suffixes: -ing, -ed, -tion, -ly, -ness, etc.
        Not as accurate as Porter stemmer but zero-dependency.
        """
        if len(word) <= 4:
            return word

        # Order matters: try longest suffixes first
        suffixes = [
            ("ization", 3), ("ation", 2), ("tion", 2), ("sion", 2),
            ("ing", 3), ("edly", 2), ("ly", 2), ("ness", 3),
            ("ment", 3), ("able", 3), ("ible", 3), ("ful", 2),
            ("ous", 2), ("ive", 2), ("al", 1), ("er", 1),
            ("ed", 1), ("es", 0), ("s", 0),
        ]

        for suffix, min_stem_len in suffixes:
            if word.endswith(suffix):
                stem = word[:-len(suffix)] if len(suffix) > 0 else word
                if len(stem) >= min_stem_len + 2:
                    return stem

        return word


# ══════════════════════════════════════════════════════════════════════
# TF-IDF EMBEDDER
# ══════════════════════════════════════════════════════════════════════


class TFIDFEmbedder:
    """
    TF-IDF embedding generator.

    Maintains document frequency counts and vocabulary to compute
    TF-IDF vectors for documents and queries.

    TF-IDF = term_frequency * log(N / document_frequency)

    Where:
    - term_frequency: count of term in document / total terms
    - N: total number of documents
    - document_frequency: number of documents containing the term
    """

    def __init__(self) -> None:
        self._vocab: dict[str, int] = {}  # term -> index
        self._doc_freq: dict[str, int] = defaultdict(int)  # term -> doc count
        self._total_docs = 0
        self._tokenizer = SimpleTokenizer()

    @property
    def vocab_size(self) -> int:
        """Current vocabulary size."""
        return len(self._vocab)

    def add_document(self, text: str) -> list[float]:
        """
        Add a document and return its TF-IDF embedding.

        Updates vocabulary and document frequency counts.

        Args:
            text: Document text

        Returns:
            TF-IDF embedding vector
        """
        tokens = self._tokenizer.tokenize(text)
        stemmed = [self._tokenizer.simple_stem(t) for t in tokens]

        # Update vocabulary
        for token in set(stemmed):
            if token not in self._vocab:
                self._vocab[token] = len(self._vocab)
            self._doc_freq[token] += 1

        self._total_docs += 1

        # Compute embedding
        return self._compute_tfidf(stemmed)

    def embed_query(self, text: str) -> list[float]:
        """
        Embed a query text using current vocabulary and IDF values.

        Args:
            text: Query text

        Returns:
            TF-IDF embedding vector
        """
        tokens = self._tokenizer.tokenize(text)
        stemmed = [self._tokenizer.simple_stem(t) for t in tokens]
        return self._compute_tfidf(stemmed)

    def _compute_tfidf(self, stemmed_tokens: list[str]) -> list[float]:
        """Compute TF-IDF vector for a list of stemmed tokens."""
        if not stemmed_tokens:
            return [0.0] * max(self.vocab_size, 1)

        # Term frequency
        tf_counts = Counter(stemmed_tokens)
        total_terms = len(stemmed_tokens)

        # Build TF-IDF vector
        vector = [0.0] * self.vocab_size

        for token, count in tf_counts.items():
            if token not in self._vocab:
                continue  # Unknown token

            idx = self._vocab[token]
            tf = count / total_terms

            # IDF with smoothing
            df = self._doc_freq.get(token, 1)
            idf = math.log((self._total_docs + 1) / (df + 1)) + 1

            vector[idx] = tf * idf

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector


# ══════════════════════════════════════════════════════════════════════
# VECTOR MEMORY
# ══════════════════════════════════════════════════════════════════════


class VectorMemory:
    """
    In-memory vector store with TF-IDF embeddings and cosine similarity.

    No external vector database required — uses numpy for efficient
    similarity computation. Suitable for up to ~100k documents.

    Features:
    - Add documents with metadata
    - Semantic similarity search
    - Keyword-based filtering
    - Incremental vocabulary building
    - Document deletion and updates

    Args:
        max_documents: Maximum number of documents to store
        similarity_threshold: Minimum similarity score for search results

    Example:
        vm = VectorMemory()
        vm.add_documents([
            {"text": "Apple Q4 earnings beat expectations", "metadata": {"symbol": "AAPL"}},
            {"text": "Tesla deliveries miss estimates", "metadata": {"symbol": "TSLA"}},
        ])
        results = vm.similarity_search("earnings report", k=5)
        for r in results:
            print(f"{r.score:.3f}: {r.text}")
    """

    def __init__(
        self,
        max_documents: int = 100_000,
        similarity_threshold: float = 0.0,
    ) -> None:
        self._max_documents = max_documents
        self._similarity_threshold = similarity_threshold

        self._documents: dict[str, VectorDocument] = {}
        self._embedder = TFIDFEmbedder()
        self._embedding_matrix: np.ndarray | None = None
        self._doc_ids: list[str] = []  # Ordered list matching matrix rows
        self._dirty = True  # Whether matrix needs rebuilding

        logger.info("VectorMemory initialized (max_docs=%d)", max_documents)

    @property
    def document_count(self) -> int:
        """Number of documents in the store."""
        return len(self._documents)

    @property
    def vocab_size(self) -> int:
        """Current vocabulary size."""
        return self._embedder.vocab_size

    # ══════════════════════════════════════════════════════════════════
    # ADD DOCUMENTS
    # ══════════════════════════════════════════════════════════════════

    def add_documents(
        self,
        documents: list[dict[str, Any]] | list[str],
    ) -> list[str]:
        """
        Add documents to the vector store.

        Args:
            documents: List of dicts with 'text' and optional 'metadata',
                       or list of plain strings

        Returns:
            List of document IDs
        """
        doc_ids = []

        for doc in documents:
            if isinstance(doc, str):
                text = doc
                metadata: dict[str, Any] = {}
            elif isinstance(doc, dict):
                text = doc.get("text", "")
                metadata = doc.get("metadata", {})
                if not text:
                    # Try other common keys
                    text = doc.get("content", doc.get("body", ""))
            else:
                logger.warning("Skipping invalid document type: %s", type(doc))
                continue

            if not text:
                continue

            doc_id = self._generate_doc_id(text, metadata)
            embedding = self._embedder.add_document(text)

            vector_doc = VectorDocument(
                doc_id=doc_id,
                text=text,
                metadata=metadata,
                embedding=embedding,
                token_count=len(SimpleTokenizer.tokenize(text)),
            )

            self._documents[doc_id] = vector_doc
            self._dirty = True
            doc_ids.append(doc_id)

        # Enforce max documents (FIFO eviction)
        while len(self._documents) > self._max_documents:
            oldest_id = next(iter(self._documents))
            del self._documents[oldest_id]
            self._dirty = True
            logger.debug("Evicted document: %s", oldest_id)

        logger.info("Added %d documents (total: %d)", len(doc_ids), len(self._documents))
        return doc_ids

    def add_document(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Add a single document.

        Args:
            text: Document text
            metadata: Optional metadata dict

        Returns:
            Document ID
        """
        ids = self.add_documents([{"text": text, "metadata": metadata or {}}])
        return ids[0] if ids else ""

    # ══════════════════════════════════════════════════════════════════
    # SIMILARITY SEARCH
    # ══════════════════════════════════════════════════════════════════

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        Find the k most similar documents to a query.

        Args:
            query: Search query text
            k: Number of results to return
            filter_metadata: Optional metadata filter (key-value pairs must match)

        Returns:
            List of SearchResult sorted by similarity (highest first)
        """
        if not self._documents:
            return []

        # Embed the query
        query_embedding = self._embedder.embed_query(query)
        query_vec = np.array(query_embedding, dtype=np.float64)

        # Rebuild embedding matrix if dirty
        if self._dirty:
            self._rebuild_matrix()

        if self._embedding_matrix is None or len(self._embedding_matrix) == 0:
            # Fallback: compute similarities individually
            return self._search_fallback(query_vec, k, filter_metadata)

        # Compute cosine similarities
        similarities = self._compute_similarities(query_vec)

        # Apply metadata filter
        if filter_metadata:
            mask = np.ones(len(self._doc_ids), dtype=bool)
            for i, doc_id in enumerate(self._doc_ids):
                doc = self._documents.get(doc_id)
                if doc:
                    for key, value in filter_metadata.items():
                        if doc.metadata.get(key) != value:
                            mask[i] = False
                            break
            similarities = similarities * mask

        # Get top-k indices
        k = min(k, len(similarities))
        if k == 0:
            return []

        top_indices = np.argsort(similarities)[::-1][:k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score < self._similarity_threshold:
                continue

            doc_id = self._doc_ids[idx]
            doc = self._documents.get(doc_id)
            if doc:
                results.append(SearchResult(
                    doc_id=doc_id,
                    text=doc.text,
                    score=round(score, 6),
                    metadata=doc.metadata,
                ))

        return results

    def _search_fallback(
        self,
        query_vec: np.ndarray,
        k: int,
        filter_metadata: dict[str, Any] | None,
    ) -> list[SearchResult]:
        """Fallback search when matrix is not available."""
        results = []

        for doc_id, doc in self._documents.items():
            # Apply metadata filter
            if filter_metadata:
                match = all(
                    doc.metadata.get(key) == value
                    for key, value in filter_metadata.items()
                )
                if not match:
                    continue

            if not doc.embedding:
                continue

            doc_vec = np.array(doc.embedding, dtype=np.float64)

            # Pad vectors to same length if needed
            max_len = max(len(query_vec), len(doc_vec))
            q = np.zeros(max_len)
            d = np.zeros(max_len)
            q[:len(query_vec)] = query_vec
            d[:len(doc_vec)] = doc_vec

            # Cosine similarity
            dot = np.dot(q, d)
            norm_q = np.linalg.norm(q)
            norm_d = np.linalg.norm(d)

            if norm_q > 0 and norm_d > 0:
                score = dot / (norm_q * norm_d)
            else:
                score = 0.0

            results.append(SearchResult(
                doc_id=doc_id,
                text=doc.text,
                score=round(float(score), 6),
                metadata=doc.metadata,
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]

    # ══════════════════════════════════════════════════════════════════
    # DOCUMENT MANAGEMENT
    # ══════════════════════════════════════════════════════════════════

    def get_document(self, doc_id: str) -> VectorDocument | None:
        """Get a document by ID."""
        return self._documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if document was found and deleted
        """
        if doc_id in self._documents:
            del self._documents[doc_id]
            self._dirty = True
            logger.debug("Deleted document: %s", doc_id)
            return True
        return False

    def clear(self) -> None:
        """Clear all documents and reset the vector store."""
        self._documents.clear()
        self._embedder = TFIDFEmbedder()
        self._embedding_matrix = None
        self._doc_ids.clear()
        self._dirty = True
        logger.info("VectorMemory cleared")

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _rebuild_matrix(self) -> None:
        """Rebuild the embedding matrix from current documents."""
        self._doc_ids = list(self._documents.keys())

        if not self._doc_ids:
            self._embedding_matrix = None
            self._dirty = False
            return

        # Get max embedding length
        max_len = max(
            len(self._documents[doc_id].embedding)
            for doc_id in self._doc_ids
            if self._documents[doc_id].embedding
        )

        if max_len == 0:
            self._embedding_matrix = None
            self._dirty = False
            return

        # Build matrix with zero-padding
        matrix = np.zeros((len(self._doc_ids), max_len), dtype=np.float64)
        for i, doc_id in enumerate(self._doc_ids):
            emb = self._documents[doc_id].embedding
            if emb:
                matrix[i, :len(emb)] = emb

        self._embedding_matrix = matrix
        self._dirty = False
        logger.debug("Rebuilt embedding matrix: %d x %d", *matrix.shape)

    def _compute_similarities(self, query_vec: np.ndarray) -> np.ndarray:
        """Compute cosine similarities between query and all documents."""
        matrix = self._embedding_matrix
        if matrix is None:
            return np.array([])

        # Pad query to match matrix width
        if len(query_vec) < matrix.shape[1]:
            padded = np.zeros(matrix.shape[1])
            padded[:len(query_vec)] = query_vec
            query_vec = padded
        elif len(query_vec) > matrix.shape[1]:
            query_vec = query_vec[:matrix.shape[1]]

        # Cosine similarity: dot(q, d) / (||q|| * ||d||)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return np.zeros(matrix.shape[0])

        doc_norms = np.linalg.norm(matrix, axis=1)
        # Avoid division by zero
        doc_norms = np.where(doc_norms == 0, 1.0, doc_norms)

        similarities = np.dot(matrix, query_vec) / (doc_norms * query_norm)
        return similarities

    @staticmethod
    def _generate_doc_id(text: str, metadata: dict[str, Any]) -> str:
        """Generate a unique document ID from content hash."""
        content = f"{text}:{sorted(metadata.items())}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

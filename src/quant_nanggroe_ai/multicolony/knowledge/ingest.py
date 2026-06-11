"""Document ingestion pipeline for the Multi-Colony Ecosystem.

This module provides document and URL ingestion capabilities for
feeding knowledge into the RAG (Retrieval-Augmented Generation) system.

Supported ingestion sources:
    - Documents: PDF, TXT, Markdown, HTML files
    - URLs: Web pages and APIs
    - Raw text: Direct text input
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class IngestionStatus(str, Enum):
    """Status of an ingestion job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


class DocumentType(str, Enum):
    """Supported document types for ingestion."""

    PDF = "pdf"
    TXT = "txt"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    URL = "url"
    RAW_TEXT = "raw_text"


class ChunkStrategy(str, Enum):
    """Chunking strategies for document splitting."""

    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"


class DocumentChunk(BaseModel):
    """A chunk of a document after processing.

    Attributes:
        chunk_id: Unique identifier for the chunk.
        document_id: ID of the source document.
        content: The chunk text content.
        chunk_index: Position of this chunk in the document.
        metadata: Chunk-level metadata (page number, section, etc.).
        token_count: Estimated token count.
    """

    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    content: str
    chunk_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    token_count: int = 0


class IngestedDocument(BaseModel):
    """A document that has been ingested into the knowledge base.

    Attributes:
        document_id: Unique identifier for the document.
        title: Document title.
        source: Source path or URL.
        document_type: Type of the document.
        content: Full document content.
        chunks: Document chunks after processing.
        status: Ingestion status.
        chunk_strategy: Strategy used for chunking.
        chunk_size: Target chunk size in tokens.
        chunk_overlap: Overlap between chunks in tokens.
        metadata: Document-level metadata.
        total_tokens: Total token count.
        created_at: When the document was ingested.
        error_message: Error details if ingestion failed.
    """

    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    source: str = ""
    document_type: DocumentType = DocumentType.RAW_TEXT
    content: str = ""
    chunks: list[DocumentChunk] = Field(default_factory=list)
    status: IngestionStatus = IngestionStatus.PENDING
    chunk_strategy: ChunkStrategy = ChunkStrategy.FIXED_SIZE
    chunk_size: int = 512
    chunk_overlap: int = 64
    metadata: dict[str, Any] = Field(default_factory=dict)
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: str | None = None


class KnowledgeIngest:
    """Document ingestion pipeline for the knowledge base.

    This class provides methods to ingest documents from various sources,
    process them into chunks, and prepare them for embedding and storage
    in the RAG system.

    Example::

        ingest = KnowledgeIngest(chunk_size=512)
        doc = await ingest.ingest_document("/path/to/file.pdf")
        doc = await ingest.ingest_url("https://example.com/article")
        doc = await ingest.ingest_text("Some text to ingest", title="Notes")
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        chunk_strategy: ChunkStrategy = ChunkStrategy.FIXED_SIZE,
        max_document_size_mb: float = 50.0,
    ) -> None:
        """Initialize the ingestion pipeline.

        Args:
            chunk_size: Target chunk size in tokens.
            chunk_overlap: Overlap between chunks in tokens.
            chunk_strategy: Strategy for chunking documents.
            max_document_size_mb: Maximum document size in MB.
        """
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._chunk_strategy = chunk_strategy
        self._max_document_size_mb = max_document_size_mb
        self._documents: dict[str, IngestedDocument] = {}
        self._log = logger.bind(component="knowledge_ingest")

    @property
    def document_count(self) -> int:
        """Number of ingested documents."""
        return len(self._documents)

    async def ingest_document(
        self,
        file_path: str | Path,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        chunk_strategy: ChunkStrategy | None = None,
    ) -> IngestedDocument:
        """Ingest a document from a file path.

        Args:
            file_path: Path to the document file.
            title: Optional title override.
            metadata: Additional metadata.
            chunk_strategy: Override chunking strategy.

        Returns:
            The ingested document with chunks.
        """
        file_path = Path(file_path)

        # Determine document type from extension
        doc_type = self._detect_document_type(file_path)

        # Read file content (stub: in production, would use proper parsers)
        try:
            if doc_type == DocumentType.PDF:
                content = await self._read_pdf(file_path)
            elif doc_type in (DocumentType.TXT, DocumentType.MARKDOWN):
                content = file_path.read_text(encoding="utf-8")
            elif doc_type == DocumentType.HTML:
                content = await self._read_html(file_path)
            else:
                content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            doc = IngestedDocument(
                title=title or file_path.name,
                source=str(file_path),
                document_type=doc_type,
                status=IngestionStatus.FAILED,
                error_message=str(exc),
                metadata=metadata or {},
            )
            self._documents[doc.document_id] = doc
            self._log.error("document_read_failed", path=str(file_path), error=str(exc))
            return doc

        return await self._process_document(
            content=content,
            source=str(file_path),
            title=title or file_path.name,
            document_type=doc_type,
            metadata=metadata,
            chunk_strategy=chunk_strategy,
        )

    async def ingest_url(
        self,
        url: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        chunk_strategy: ChunkStrategy | None = None,
    ) -> IngestedDocument:
        """Ingest content from a URL.

        Args:
            url: URL to fetch and ingest.
            title: Optional title override.
            metadata: Additional metadata.
            chunk_strategy: Override chunking strategy.

        Returns:
            The ingested document with chunks.
        """
        # Stub: In production, would use httpx/aiohttp to fetch
        content = f"[Content from {url}]"

        url_metadata = metadata or {}
        url_metadata["url"] = url

        return await self._process_document(
            content=content,
            source=url,
            title=title or url,
            document_type=DocumentType.URL,
            metadata=url_metadata,
            chunk_strategy=chunk_strategy,
        )

    async def ingest_text(
        self,
        text: str,
        title: str = "Untitled",
        source: str = "raw_text",
        metadata: dict[str, Any] | None = None,
        chunk_strategy: ChunkStrategy | None = None,
    ) -> IngestedDocument:
        """Ingest raw text content.

        Args:
            text: The text content to ingest.
            title: Document title.
            source: Source identifier.
            metadata: Additional metadata.
            chunk_strategy: Override chunking strategy.

        Returns:
            The ingested document with chunks.
        """
        return await self._process_document(
            content=text,
            source=source,
            title=title,
            document_type=DocumentType.RAW_TEXT,
            metadata=metadata,
            chunk_strategy=chunk_strategy,
        )

    def get_document(self, document_id: str) -> IngestedDocument:
        """Get an ingested document by ID.

        Args:
            document_id: ID of the document.

        Returns:
            The ingested document.

        Raises:
            DocumentNotFoundError: If the document is not found.
        """
        if document_id not in self._documents:
            raise DocumentNotFoundError(f"Document {document_id} not found.")
        return self._documents[document_id]

    def list_documents(
        self,
        status: IngestionStatus | None = None,
        document_type: DocumentType | None = None,
    ) -> list[IngestedDocument]:
        """List ingested documents with optional filtering.

        Args:
            status: Filter by ingestion status.
            document_type: Filter by document type.

        Returns:
            A list of matching documents.
        """
        docs = list(self._documents.values())
        if status is not None:
            docs = [d for d in docs if d.status == status]
        if document_type is not None:
            docs = [d for d in docs if d.document_type == document_type]
        return docs

    async def _process_document(
        self,
        content: str,
        source: str,
        title: str,
        document_type: DocumentType,
        metadata: dict[str, Any] | None = None,
        chunk_strategy: ChunkStrategy | None = None,
    ) -> IngestedDocument:
        """Process a document: chunk and prepare for embedding.

        Args:
            content: Document text content.
            source: Source identifier.
            title: Document title.
            document_type: Type of the document.
            metadata: Additional metadata.
            chunk_strategy: Override chunking strategy.

        Returns:
            The processed document with chunks.
        """
        strategy = chunk_strategy or self._chunk_strategy
        doc = IngestedDocument(
            title=title,
            source=source,
            document_type=document_type,
            content=content,
            status=IngestionStatus.PROCESSING,
            chunk_strategy=strategy,
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            metadata=metadata or {},
        )

        try:
            # Chunk the document
            chunks = self._chunk_text(content, strategy)
            doc.chunks = [
                DocumentChunk(
                    document_id=doc.document_id,
                    content=chunk,
                    chunk_index=idx,
                    token_count=len(chunk) // 4,
                )
                for idx, chunk in enumerate(chunks)
            ]
            doc.total_tokens = sum(c.token_count for c in doc.chunks)
            doc.status = IngestionStatus.COMPLETED

        except Exception as exc:
            doc.status = IngestionStatus.FAILED
            doc.error_message = str(exc)

        self._documents[doc.document_id] = doc

        self._log.info(
            "document_ingested",
            document_id=doc.document_id,
            title=title,
            status=doc.status.value,
            chunks=len(doc.chunks),
        )

        return doc

    def _chunk_text(
        self,
        text: str,
        strategy: ChunkStrategy,
    ) -> list[str]:
        """Split text into chunks based on the chosen strategy.

        Args:
            text: Text to chunk.
            strategy: Chunking strategy.

        Returns:
            A list of text chunks.
        """
        if strategy == ChunkStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(text)
        elif strategy == ChunkStrategy.PARAGRAPH:
            return self._chunk_by_paragraph(text)
        elif strategy == ChunkStrategy.SENTENCE:
            return self._chunk_by_sentence(text)
        elif strategy == ChunkStrategy.SEMANTIC:
            # Stub: In production, would use embedding-based semantic chunking
            return self._chunk_fixed_size(text)
        else:
            return self._chunk_fixed_size(text)

    def _chunk_fixed_size(self, text: str) -> list[str]:
        """Chunk text into fixed-size pieces with overlap.

        Args:
            text: Text to chunk.

        Returns:
            A list of text chunks.
        """
        chunk_chars = self._chunk_size * 4  # Rough: 4 chars per token
        overlap_chars = self._chunk_overlap * 4

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_chars
            chunks.append(text[start:end])
            start = end - overlap_chars

        return chunks if chunks else [text]

    def _chunk_by_paragraph(self, text: str) -> list[str]:
        """Chunk text by paragraph boundaries.

        Args:
            text: Text to chunk.

        Returns:
            A list of text chunks.
        """
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) > self._chunk_size * 4:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    def _chunk_by_sentence(self, text: str) -> list[str]:
        """Chunk text by sentence boundaries.

        Args:
            text: Text to chunk.

        Returns:
            A list of text chunks.
        """
        # Simple sentence splitting
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        sentences = [s.strip() + "." for s in sentences if s.strip()]

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self._chunk_size * 4:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    @staticmethod
    def _detect_document_type(file_path: Path) -> DocumentType:
        """Detect document type from file extension.

        Args:
            file_path: Path to the file.

        Returns:
            The detected document type.
        """
        ext = file_path.suffix.lower()
        extension_map = {
            ".pdf": DocumentType.PDF,
            ".txt": DocumentType.TXT,
            ".md": DocumentType.MARKDOWN,
            ".markdown": DocumentType.MARKDOWN,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
            ".json": DocumentType.JSON,
            ".csv": DocumentType.CSV,
        }
        return extension_map.get(ext, DocumentType.TXT)

    async def _read_pdf(self, file_path: Path) -> str:
        """Read content from a PDF file.

        Stub: In production, would use PyPDF2 or pdfplumber.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Extracted text content.
        """
        # Stub: In production, use proper PDF parsing
        return f"[PDF content from {file_path.name}]"

    async def _read_html(self, file_path: Path) -> str:
        """Read content from an HTML file.

        Stub: In production, would use BeautifulSoup for extraction.

        Args:
            file_path: Path to the HTML file.

        Returns:
            Extracted text content.
        """
        # Stub: In production, use BeautifulSoup
        return file_path.read_text(encoding="utf-8")


class DocumentNotFoundError(Exception):
    """Raised when a document is not found in the ingestion store."""

"""
Agent File Operations Tool — Upload, Download, Delete via Storage Backends
============================================================================
Merged from ai-manus feature/agent-file-oprate branch and adapted for
Quant-Nanggroe-AI.

Provides:
  - FileOperate: Protocol interface for file storage backends
  - FileOperationFactory: Creates storage instances based on config
  - LocalFileStorage: Local filesystem storage backend (default)
  - MongoDBGridFSStorage: MongoDB GridFS storage backend
  - AttachmentService: High-level file attachment management
  - FileOpsTool: Agent tool for file operations

Adapted from:
  - ai-manus/backend/app/domain/external/file_operate.py
  - ai-manus/backend/app/infrastructure/external/file/file_operate.py
  - ai-manus/backend/app/application/services/attachment_service.py
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, BinaryIO, Optional, Protocol, runtime_checkable

from pydantic import BaseModel

from quant_nanggroe_ai.config import get_settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Response Schemas
# ══════════════════════════════════════════════════════════════════════


class AttachmentUploadResponse(BaseModel):
    """Response model for file upload result."""
    filename: str
    content_type: str
    file_size: int
    storage_type: str
    storage_url: str


class AttachmentDownloadResponse(BaseModel):
    """Response model for file download result."""
    storage_url: str
    filename: str
    content_type: str
    content: bytes
    file_size: int


class AttachmentInfo(BaseModel):
    """Metadata for a stored attachment."""
    attachment_id: str
    filename: str
    content_type: str
    file_size: int
    storage_type: str
    storage_url: str


# ══════════════════════════════════════════════════════════════════════
# FileOperate Protocol
# ══════════════════════════════════════════════════════════════════════


@runtime_checkable
class FileOperate(Protocol):
    """
    Protocol interface for file storage backends.

    All storage backends must implement upload_file, download_file,
    and delete_file methods.
    """

    async def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]: ...

    async def download_file(self, storage_url: str) -> Optional[dict[str, Any]]: ...

    async def delete_file(self, storage_url: str) -> bool: ...


# ══════════════════════════════════════════════════════════════════════
# Local Filesystem Storage
# ══════════════════════════════════════════════════════════════════════


class LocalFileStorage:
    """
    Local filesystem-based file storage.

    Files are stored in a configurable upload directory with unique
    filenames to prevent collisions.
    """

    def __init__(self, upload_dir: str | None = None) -> None:
        settings = get_settings()
        self._upload_dir = Path(upload_dir or getattr(settings, "upload_dir", "/tmp/quant_nanggroe_uploads"))
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Upload a file to local filesystem.

        Args:
            file_data: The file data stream.
            filename: The name of the file.
            content_type: MIME type of the file.
            metadata: Additional metadata (stored alongside file).

        Returns:
            Dict with filename, content_type, storage_type, storage_url, file_size.
        """
        try:
            file_data.seek(0)
        except Exception:
            pass

        content = file_data.read()
        file_id = str(uuid.uuid4())

        # Create subdirectory per file to avoid collisions
        file_dir = self._upload_dir / file_id
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)

        # Store metadata alongside
        if metadata or content_type:
            meta_path = file_dir / ".meta"
            meta_content = f"content_type={content_type or ''}\nfilename={filename}\n"
            if metadata:
                for k, v in metadata.items():
                    meta_content += f"{k}={v}\n"
            with open(meta_path, "w") as f:
                f.write(meta_content)

        logger.info("File uploaded locally: %s (%d bytes)", filename, len(content))
        return {
            "filename": filename,
            "content_type": content_type,
            "storage_type": "local",
            "storage_url": file_id,
            "file_size": len(content),
        }

    async def download_file(self, storage_url: str) -> Optional[dict[str, Any]]:
        """
        Download a file from local filesystem.

        Args:
            storage_url: The file ID (subdirectory name).

        Returns:
            Dict with content, filename, content_type, file_size, metadata.
        """
        file_dir = self._upload_dir / storage_url
        if not file_dir.exists():
            logger.warning("File directory not found: %s", storage_url)
            return None

        # Find the actual file (skip .meta)
        files = [f for f in file_dir.iterdir() if f.name != ".meta" and f.is_file()]
        if not files:
            logger.warning("No file found in directory: %s", storage_url)
            return None

        file_path = files[0]
        content = file_path.read_bytes()

        # Read metadata if available
        content_type = "application/octet-stream"
        meta_path = file_dir / ".meta"
        metadata: dict[str, Any] = {}
        if meta_path.exists():
            for line in meta_path.read_text().strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k == "content_type":
                        content_type = v or content_type
                    else:
                        metadata[k] = v

        return {
            "content": content,
            "filename": file_path.name,
            "content_type": content_type,
            "file_size": len(content),
            "metadata": metadata,
        }

    async def delete_file(self, storage_url: str) -> bool:
        """
        Delete a file from local filesystem.

        Args:
            storage_url: The file ID (subdirectory name).

        Returns:
            True if the file was deleted successfully.
        """
        file_dir = self._upload_dir / storage_url
        if not file_dir.exists():
            return False
        try:
            shutil.rmtree(file_dir)
            logger.info("File deleted: %s", storage_url)
            return True
        except Exception as e:
            logger.error("Failed to delete file %s: %s", storage_url, e)
            return False


# ══════════════════════════════════════════════════════════════════════
# MongoDB GridFS Storage
# ══════════════════════════════════════════════════════════════════════


class MongoDBGridFSStorage:
    """
    MongoDB GridFS-based file storage.

    Stores files as chunks in MongoDB using the motor async driver.
    Requires a running MongoDB instance.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._client = None
        self._fs = None
        self._db_name = getattr(settings, "mongodb_database", "quant_nanggroe")

    async def initialize(self) -> None:
        """Initialize the MongoDB client and GridFS bucket."""
        if self._client is None:
            try:
                from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

                mongo_url = getattr(self._settings, "mongodb_url", "mongodb://localhost:27017")
                self._client = AsyncIOMotorClient(mongo_url)
                self._fs = AsyncIOMotorGridFSBucket(self._client[self._db_name])
                logger.info("MongoDB GridFS initialized for database: %s", self._db_name)
            except ImportError:
                raise ImportError(
                    "motor is required for MongoDB GridFS storage. "
                    "Install it with: pip install motor"
                )

    async def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Upload a file to MongoDB GridFS.

        Args:
            file_data: The file data stream.
            filename: The name of the file.
            content_type: MIME type of the file.
            metadata: Additional metadata for the file.

        Returns:
            Dict with filename, content_type, storage_type, storage_url, file_size.
        """
        if self._fs is None:
            await self.initialize()

        try:
            file_data.seek(0)
        except Exception:
            pass

        content = file_data.read()
        max_size = getattr(self._settings, "max_file_size", 50 * 1024 * 1024)  # 50MB default
        if len(content) > max_size:
            raise ValueError(f"File size exceeds limit of {max_size} bytes")

        file_id = await self._fs.upload_from_stream(
            filename,
            content,
            metadata={"content_type": content_type},
        )

        logger.info("File uploaded to GridFS: %s (%d bytes)", filename, len(content))
        return {
            "filename": filename,
            "content_type": content_type,
            "storage_type": "mongodb",
            "storage_url": str(file_id),
            "file_size": len(content),
        }

    async def download_file(self, storage_url: str) -> Optional[dict[str, Any]]:
        """
        Download a file from MongoDB GridFS.

        Args:
            storage_url: The ObjectId string of the file.

        Returns:
            Dict with content, filename, content_type, file_size, metadata.
        """
        if self._fs is None:
            await self.initialize()

        try:
            from bson import ObjectId

            grid_out = await self._fs.open_download_stream(ObjectId(storage_url))
            content = await grid_out.read()
            file_metadata = grid_out.metadata or {}
            return {
                "content": content,
                "filename": grid_out.filename,
                "content_type": file_metadata.get("content_type", "application/octet-stream"),
                "file_size": len(content),
                "metadata": file_metadata,
            }
        except Exception as e:
            logger.error("Failed to download file from GridFS: %s", e)
            return None

    async def delete_file(self, storage_url: str) -> bool:
        """
        Delete a file from MongoDB GridFS.

        Args:
            storage_url: The ObjectId string of the file.

        Returns:
            True if the file was deleted successfully.
        """
        try:
            from bson import ObjectId

            if self._fs is None:
                await self.initialize()
            await self._fs.delete(ObjectId(storage_url))
            logger.info("File deleted from GridFS: %s", storage_url)
            return True
        except Exception as e:
            logger.error("Failed to delete file from GridFS: %s", e)
            return False


# ══════════════════════════════════════════════════════════════════════
# File Operation Factory
# ══════════════════════════════════════════════════════════════════════


class FileOperationFactory:
    """
    Factory for creating file storage operation instances.

    Creates storage instances based on the configured storage type:
      - "local": LocalFileStorage (default, no external dependencies)
      - "mongodb": MongoDBGridFSStorage (requires MongoDB)
    """

    @staticmethod
    async def create_storage(
        storage_type: str | None = None,
    ) -> FileOperate:
        """
        Create a file storage instance based on configuration.

        Args:
            storage_type: Override storage type. If None, reads from settings.

        Returns:
            A FileOperate-compliant storage instance.

        Raises:
            ValueError: If the storage type is not supported.
        """
        if storage_type is None:
            settings = get_settings()
            storage_type = getattr(settings, "storage_type", "local")

        if storage_type == "local":
            return LocalFileStorage()
        elif storage_type == "mongodb":
            storage = MongoDBGridFSStorage()
            await storage.initialize()
            return storage  # type: ignore[return-value]
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")


# ══════════════════════════════════════════════════════════════════════
# Attachment Service
# ══════════════════════════════════════════════════════════════════════


class AttachmentService:
    """
    High-level service for file attachment management.

    Handles upload, download, binding to sessions, listing, and deletion.
    Uses FileOperationFactory to abstract storage backend.
    """

    def __init__(self, storage_factory: FileOperationFactory | None = None) -> None:
        self._factory = storage_factory or FileOperationFactory()
        self._attachments: dict[str, AttachmentInfo] = {}

    async def upload_attachment(
        self, file_data: BinaryIO, filename: str, content_type: str = "application/octet-stream"
    ) -> AttachmentUploadResponse:
        """
        Upload a file attachment to the storage backend.

        Args:
            file_data: The file data stream.
            filename: The name of the file.
            content_type: The MIME type of the file.

        Returns:
            AttachmentUploadResponse with upload result.
        """
        storage = await self._factory.create_storage()
        result = await storage.upload_file(file_data, filename, content_type)

        # Track attachment metadata
        info = AttachmentInfo(
            attachment_id=str(uuid.uuid4()),
            filename=result["filename"],
            content_type=result.get("content_type", content_type),
            file_size=result["file_size"],
            storage_type=result["storage_type"],
            storage_url=result["storage_url"],
        )
        self._attachments[info.attachment_id] = info

        return AttachmentUploadResponse(**result)

    async def download_attachment(self, storage_url: str) -> AttachmentDownloadResponse:
        """
        Download an attachment from the storage backend.

        Args:
            storage_url: The storage URL or object ID.

        Returns:
            AttachmentDownloadResponse with file content and metadata.
        """
        storage = await self._factory.create_storage()
        result = await storage.download_file(storage_url)
        if result is None:
            raise FileNotFoundError(f"File not found: {storage_url}")

        return AttachmentDownloadResponse(
            storage_url=storage_url,
            filename=result["filename"],
            content_type=result["content_type"],
            content=result["content"],
            file_size=result["file_size"],
        )

    async def delete_attachment(self, attachment_id: str) -> bool:
        """
        Delete an attachment from both storage and tracking.

        Args:
            attachment_id: The unique ID of the attachment.

        Returns:
            True if deleted successfully.
        """
        info = self._attachments.get(attachment_id)
        if not info:
            return False

        storage = await self._factory.create_storage()
        deleted = await storage.delete_file(info.storage_url)
        if deleted:
            del self._attachments[attachment_id]
        return deleted

    async def list_attachments(self) -> list[AttachmentInfo]:
        """
        List all tracked attachments.

        Returns:
            List of AttachmentInfo objects.
        """
        return list(self._attachments.values())

    async def get_attachment_info(self, attachment_id: str) -> Optional[AttachmentInfo]:
        """
        Get metadata for a specific attachment.

        Args:
            attachment_id: The unique ID of the attachment.

        Returns:
            AttachmentInfo, or None if not found.
        """
        return self._attachments.get(attachment_id)


# ══════════════════════════════════════════════════════════════════════
# Agent Tool: FileOpsTool
# ══════════════════════════════════════════════════════════════════════


class FileOpsTool:
    """
    Agent tool for file operations — upload, download, delete, list.

    Provides a simple interface for agents to manage file attachments
    through the trading platform's storage backends.

    Usage::

        tool = FileOpsTool()
        result = await tool.upload(filename="report.csv", data=file_stream)
        content = await tool.download(storage_url="abc-123")
        files = await tool.list_files()
    """

    def __init__(self, storage_type: str | None = None) -> None:
        self._service = AttachmentService()
        self._storage_type = storage_type

    async def upload(
        self,
        filename: str,
        data: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        """
        Upload a file.

        Args:
            filename: Name of the file.
            data: File data stream.
            content_type: MIME type.

        Returns:
            Upload result dict.
        """
        result = await self._service.upload_attachment(data, filename, content_type)
        return result.model_dump()

    async def download(self, storage_url: str) -> dict[str, Any]:
        """
        Download a file by storage URL.

        Args:
            storage_url: The storage URL or object ID.

        Returns:
            Download result dict with content and metadata.
        """
        result = await self._service.download_attachment(storage_url)
        return result.model_dump()

    async def delete(self, attachment_id: str) -> dict[str, Any]:
        """
        Delete a file by attachment ID.

        Args:
            attachment_id: The unique attachment ID.

        Returns:
            Deletion status dict.
        """
        deleted = await self._service.delete_attachment(attachment_id)
        return {"status": "deleted" if deleted else "not_found", "attachment_id": attachment_id}

    async def list_files(self) -> dict[str, Any]:
        """
        List all tracked files.

        Returns:
            Dict with file list and count.
        """
        attachments = await self._service.list_attachments()
        return {
            "files": [a.model_dump() for a in attachments],
            "count": len(attachments),
        }

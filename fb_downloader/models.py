"""Pydantic data models for Facebook Media items and pipeline results."""

from typing import List, Optional
from pydantic import BaseModel, Field


class MediaItem(BaseModel):
    """Represents a discovered high-resolution image asset."""

    url: str = Field(..., description="High-resolution direct CDN URL")
    original_url: Optional[str] = Field(None, description="Raw source URL or parent link")
    photo_id: Optional[str] = Field(None, description="Facebook internal photo fbid")
    width: Optional[int] = Field(None, description="Pixel width if parsed")
    height: Optional[int] = Field(None, description="Pixel height if parsed")
    mime_type: Optional[str] = Field("image/jpeg", description="MIME type from headers")
    suggested_filename: Optional[str] = Field(None, description="Formatted output filename")
    index: int = Field(0, description="Sequential position index in post/album")
    file_size_bytes: Optional[int] = Field(0, description="Size in bytes after download")
    local_path: Optional[str] = Field(None, description="Saved absolute or relative local path")


class PostMetadata(BaseModel):
    """Metadata extracted from the Facebook post container."""

    post_id: str = Field(..., description="Normalized Facebook Post ID")
    canonical_url: str = Field(..., description="Canonical Facebook web endpoint")
    original_url: str = Field(..., description="Original user-provided URL")
    author: Optional[str] = Field(None, description="Post author name or page name")
    caption: Optional[str] = Field(None, description="Post text caption or summary")
    timestamp: Optional[str] = Field(None, description="Post creation timestamp or time string")
    is_multi_photo: bool = Field(False, description="True if post contains 2+ photos")


class ScrapeResult(BaseModel):
    """Result returned by the Scraper component."""

    post_id: str
    canonical_url: str
    original_url: str
    items: List[MediaItem] = Field(default_factory=list)
    total_discovered: int = 0
    metadata: Optional[PostMetadata] = None
    is_private_or_deleted: bool = Field(False, description="True if post is private, restricted, or deleted")
    status_message: Optional[str] = Field(None, description="Detailed status, warning, or error message")


class DownloadResult(BaseModel):
    """Result returned by the Downloader component."""

    post_id: str
    output_dir: str
    successful_items: List[MediaItem] = Field(default_factory=list)
    failed_items: List[MediaItem] = Field(default_factory=list)
    total_bytes: int = 0
    elapsed_seconds: float = 0.0

    @property
    def is_success(self) -> bool:
        return len(self.successful_items) > 0 and len(self.failed_items) == 0

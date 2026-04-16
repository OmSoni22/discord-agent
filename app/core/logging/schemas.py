from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class LogEntry(BaseModel):
    """Individual log entry schema."""
    
    level: str
    message: str
    time: str
    module: str
    exception: Optional[str] = None


class LogResponse(BaseModel):
    """Response schema for log queries."""
    
    total: int = Field(..., description="Total number of matching logs")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    items: List[dict] = Field(..., description="Log entries")

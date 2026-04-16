"""
Log reader implementation for querying application logs.

Supports:
- Reading from current and rotated log files
- Filtering by date range
- Pagination
- Multiple log levels
"""

import json
import os
import glob
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from app.core.config.settings import settings


def read_logs(
    level: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    size: int = 50
) -> Dict[str, Any]:
    """
    Read and filter logs from files.
    
    Args:
        level: Log level (debug, info, error)
        start_date: Optional start date filter
        end_date: Optional end date filter
        page: Page number (1-indexed)
        size: Items per page
        
    Returns:
        Dict with total count, page number, and log items
    """
    log_file_pattern = f"{settings.log_dir}/{level}.log*"
    log_files = sorted(glob.glob(log_file_pattern), reverse=True)  # Newest first
    
    all_logs: List[Dict[str, Any]] = []
    
    # Read all matching log files
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        log_entry = json.loads(line)
                        
                        # Parse timestamp
                        log_time = datetime.fromisoformat(log_entry.get('time', ''))
                        
                        # Filter by date range
                        if start_date and log_time < start_date:
                            continue
                        if end_date and log_time > end_date:
                            continue
                            
                        all_logs.append(log_entry)
                        
                    except (json.JSONDecodeError, ValueError):
                        # Skip invalid JSON lines
                        continue
                        
        except Exception as e:
            # Log file might be locked or doesn't exist
            continue
    
    # Sort by time (newest first)
    all_logs.sort(key=lambda x: x.get('time', ''), reverse=True)
    
    # Pagination
    total = len(all_logs)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paginated_logs = all_logs[start_idx:end_idx]
    
    return {
        "total": total,
        "page": page,
        "page_size": size,
        "total_pages": (total + size - 1) // size if total > 0 else 0,
        "items": paginated_logs
    }


def get_log_stats() -> Dict[str, Any]:
    """
    Get statistics about log files.
    
    Returns:
        Dict with log file statistics
    """
    stats = {
        "log_directory": settings.log_dir,
        "levels": {}
    }
    
    for level in ["debug", "info", "error"]:
        log_file = f"{settings.log_dir}/{level}.log"
        
        if os.path.exists(log_file):
            stat = os.stat(log_file)
            # Count rotated files
            rotated_count = len(glob.glob(f"{log_file}.*"))
            
            stats["levels"][level] = {
                "current_file_size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "rotated_files": rotated_count
            }
        else:
            stats["levels"][level] = {
                "current_file_size": 0,
                "last_modified": None,
                "rotated_files": 0
            }
    
    return stats

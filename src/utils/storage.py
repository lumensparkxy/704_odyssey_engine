"""
Session Storage for Odyssey Engine.

This module handles storage and retrieval of research sessions in JSON format.
"""

import json
import asyncio
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging


class SessionStorage:
    """Handles storage and retrieval of research sessions."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize session storage."""
        self.config = config
        self.storage_path = Path(config.get("SESSION_STORAGE_PATH", "./sessions"))
        self.storage_path.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def save_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Save a research session to storage.
        
        Args:
            session_id: Unique identifier for the session
            session_data: Complete session data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add metadata
            session_data["last_updated"] = datetime.now().isoformat()
            session_data["version"] = session_data.get("version", 1)
            
            # Create filename
            filename = f"session_{session_id}.json"
            file_path = self.storage_path / filename
            
            # Save to file
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session_data, indent=2, default=str))
            
            self.logger.info(f"Session {session_id} saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving session {session_id}: {str(e)}")
            return False
    
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a research session from storage.
        
        Args:
            session_id: Unique identifier for the session
            
        Returns:
            Session data dictionary or None if not found
        """
        try:
            filename = f"session_{session_id}.json"
            file_path = self.storage_path / filename
            
            if not file_path.exists():
                self.logger.warning(f"Session {session_id} not found")
                return None
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                session_data = json.loads(content)
            
            self.logger.info(f"Session {session_id} loaded successfully")
            return session_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in session {session_id}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading session {session_id}: {str(e)}")
            return None
    
    async def list_sessions(self, limit: Optional[int] = None, sort_by: str = "created_at") -> List[Dict[str, Any]]:
        """
        List all stored research sessions.
        
        Args:
            limit: Maximum number of sessions to return
            sort_by: Field to sort by (created_at, last_updated, session_id)
            
        Returns:
            List of session summaries
        """
        try:
            session_files = list(self.storage_path.glob("session_*.json"))
            sessions = []
            
            for file_path in session_files:
                try:
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        session_data = json.loads(content)
                    
                    # Create session summary
                    summary = {
                        "session_id": session_data.get("session_id"),
                        "created_at": session_data.get("created_at"),
                        "last_updated": session_data.get("last_updated"),
                        "status": session_data.get("status"),
                        "initial_query": session_data.get("initial_query", "")[:100] + "..." if len(session_data.get("initial_query", "")) > 100 else session_data.get("initial_query", ""),
                        "file_path": str(file_path),
                        "file_size": file_path.stat().st_size
                    }
                    
                    sessions.append(summary)
                    
                except Exception as e:
                    self.logger.warning(f"Error reading session file {file_path}: {str(e)}")
                    continue
            
            # Sort sessions
            if sort_by in ["created_at", "last_updated"]:
                sessions.sort(key=lambda x: x.get(sort_by, ""), reverse=True)
            elif sort_by == "session_id":
                sessions.sort(key=lambda x: x.get("session_id", ""))
            
            # Apply limit
            if limit:
                sessions = sessions[:limit]
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Error listing sessions: {str(e)}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a research session from storage.
        
        Args:
            session_id: Unique identifier for the session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filename = f"session_{session_id}.json"
            file_path = self.storage_path / filename
            
            if not file_path.exists():
                self.logger.warning(f"Session {session_id} not found for deletion")
                return False
            
            file_path.unlink()
            self.logger.info(f"Session {session_id} deleted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False
    
    async def backup_session(self, session_id: str, backup_name: Optional[str] = None) -> bool:
        """
        Create a backup copy of a session.
        
        Args:
            session_id: Unique identifier for the session
            backup_name: Optional custom backup name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session_data = await self.load_session(session_id)
            if not session_data:
                return False
            
            # Create backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if backup_name:
                backup_filename = f"backup_{backup_name}_{timestamp}.json"
            else:
                backup_filename = f"backup_session_{session_id}_{timestamp}.json"
            
            backup_path = self.storage_path / "backups"
            backup_path.mkdir(exist_ok=True)
            
            backup_file = backup_path / backup_filename
            
            # Add backup metadata
            session_data["backup_info"] = {
                "original_session_id": session_id,
                "backup_created": datetime.now().isoformat(),
                "backup_name": backup_name
            }
            
            async with aiofiles.open(backup_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session_data, indent=2, default=str))
            
            self.logger.info(f"Session {session_id} backed up as {backup_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error backing up session {session_id}: {str(e)}")
            return False
    
    async def restore_session(self, backup_filename: str, new_session_id: Optional[str] = None) -> Optional[str]:
        """
        Restore a session from backup.
        
        Args:
            backup_filename: Name of the backup file
            new_session_id: Optional new session ID (otherwise generates new one)
            
        Returns:
            New session ID if successful, None otherwise
        """
        try:
            backup_path = self.storage_path / "backups" / backup_filename
            
            if not backup_path.exists():
                self.logger.error(f"Backup file {backup_filename} not found")
                return None
            
            async with aiofiles.open(backup_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                session_data = json.loads(content)
            
            # Generate new session ID if not provided
            if not new_session_id:
                import uuid
                new_session_id = str(uuid.uuid4())
            
            # Update session data
            session_data["session_id"] = new_session_id
            session_data["restored_from"] = backup_filename
            session_data["restored_at"] = datetime.now().isoformat()
            
            # Remove backup metadata
            if "backup_info" in session_data:
                del session_data["backup_info"]
            
            # Save restored session
            success = await self.save_session(new_session_id, session_data)
            
            if success:
                self.logger.info(f"Session restored from {backup_filename} as {new_session_id}")
                return new_session_id
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error restoring session from {backup_filename}: {str(e)}")
            return None
    
    async def search_sessions(self, query: str, search_fields: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search sessions by content.
        
        Args:
            query: Search query string
            search_fields: Fields to search in (default: ["initial_query", "status"])
            
        Returns:
            List of matching session summaries
        """
        if search_fields is None:
            search_fields = ["initial_query", "status"]
        
        try:
            all_sessions = await self.list_sessions()
            matching_sessions = []
            
            query_lower = query.lower()
            
            for session_summary in all_sessions:
                # Load full session for detailed search
                session_data = await self.load_session(session_summary["session_id"])
                if not session_data:
                    continue
                
                # Search in specified fields
                match_found = False
                for field in search_fields:
                    field_value = str(session_data.get(field, "")).lower()
                    if query_lower in field_value:
                        match_found = True
                        break
                
                if match_found:
                    matching_sessions.append(session_summary)
            
            return matching_sessions
            
        except Exception as e:
            self.logger.error(f"Error searching sessions: {str(e)}")
            return []
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about session storage.
        
        Returns:
            Storage statistics dictionary
        """
        try:
            session_files = list(self.storage_path.glob("session_*.json"))
            backup_path = self.storage_path / "backups"
            backup_files = list(backup_path.glob("backup_*.json")) if backup_path.exists() else []
            
            total_size = sum(f.stat().st_size for f in session_files)
            backup_size = sum(f.stat().st_size for f in backup_files)
            
            # Count sessions by status
            status_counts = {}
            total_sessions = 0
            
            for file_path in session_files:
                try:
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        session_data = json.loads(content)
                    
                    status = session_data.get("status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
                    total_sessions += 1
                    
                except Exception:
                    continue
            
            return {
                "total_sessions": total_sessions,
                "total_storage_size": total_size,
                "average_session_size": total_size / total_sessions if total_sessions > 0 else 0,
                "status_distribution": status_counts,
                "backup_count": len(backup_files),
                "backup_storage_size": backup_size,
                "storage_path": str(self.storage_path),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting storage stats: {str(e)}")
            return {"error": str(e)}
    
    async def cleanup_old_sessions(self, days_old: int = 30, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Clean up old sessions based on age and status.
        
        Args:
            days_old: Delete sessions older than this many days
            status_filter: Only delete sessions with this status (optional)
            
        Returns:
            Cleanup results
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            session_files = list(self.storage_path.glob("session_*.json"))
            
            deleted_count = 0
            error_count = 0
            total_size_freed = 0
            
            for file_path in session_files:
                try:
                    # Check file modification time
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_date:
                        # Load session to check status if filter is specified
                        if status_filter:
                            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                                content = await f.read()
                                session_data = json.loads(content)
                            
                            if session_data.get("status") != status_filter:
                                continue
                        
                        # Delete the file
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        
                        deleted_count += 1
                        total_size_freed += file_size
                        
                except Exception as e:
                    self.logger.warning(f"Error processing file {file_path}: {str(e)}")
                    error_count += 1
                    continue
            
            return {
                "deleted_sessions": deleted_count,
                "errors": error_count,
                "total_size_freed": total_size_freed,
                "cutoff_date": cutoff_date.isoformat(),
                "status_filter": status_filter
            }
            
        except Exception as e:
            self.logger.error(f"Error cleaning up sessions: {str(e)}")
            return {"error": str(e)}
    
    async def export_sessions(self, export_path: str, session_ids: Optional[List[str]] = None) -> bool:
        """
        Export sessions to a different location.
        
        Args:
            export_path: Path to export sessions to
            session_ids: Optional list of specific session IDs to export
            
        Returns:
            True if successful, False otherwise
        """
        try:
            export_dir = Path(export_path)
            export_dir.mkdir(parents=True, exist_ok=True)
            
            if session_ids:
                # Export specific sessions
                for session_id in session_ids:
                    session_data = await self.load_session(session_id)
                    if session_data:
                        export_file = export_dir / f"session_{session_id}.json"
                        async with aiofiles.open(export_file, 'w', encoding='utf-8') as f:
                            await f.write(json.dumps(session_data, indent=2, default=str))
            else:
                # Export all sessions
                session_files = list(self.storage_path.glob("session_*.json"))
                for file_path in session_files:
                    export_file = export_dir / file_path.name
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as source:
                        content = await source.read()
                    async with aiofiles.open(export_file, 'w', encoding='utf-8') as dest:
                        await dest.write(content)
            
            self.logger.info(f"Sessions exported to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting sessions: {str(e)}")
            return False

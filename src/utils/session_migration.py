"""
Session Migration Utilities for Odyssey Engine.

This module provides utilities for working with legacy session data
and the new ADK-based session format.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def list_legacy_sessions(sessions_path: str = "./sessions") -> List[Dict[str, Any]]:
    """
    List all legacy session files.
    
    Args:
        sessions_path: Path to sessions directory
        
    Returns:
        List of session summaries with id, query, status, created_at
    """
    sessions_dir = Path(sessions_path)
    if not sessions_dir.exists():
        return []
    
    sessions = []
    for session_file in sessions_dir.glob("session_*.json"):
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
            
            sessions.append({
                "session_id": data.get("session_id", session_file.stem),
                "initial_query": data.get("initial_query", "Unknown"),
                "status": data.get("status", "unknown"),
                "created_at": data.get("created_at", "Unknown"),
                "file_path": str(session_file),
                "file_size": session_file.stat().st_size,
            })
        except Exception as e:
            sessions.append({
                "session_id": session_file.stem,
                "initial_query": "Error reading session",
                "status": "error",
                "created_at": "Unknown",
                "file_path": str(session_file),
                "error": str(e),
            })
    
    return sorted(sessions, key=lambda x: x.get("created_at", ""), reverse=True)


def extract_session_state(session_file: str) -> Dict[str, Any]:
    """
    Extract state data from a legacy session file for use with ADK.
    
    This converts legacy session format to ADK state format.
    
    Args:
        session_file: Path to the legacy session JSON file
        
    Returns:
        Dictionary suitable for ADK session state
    """
    with open(session_file, 'r') as f:
        data = json.load(f)
    
    state = {}
    
    # Extract original query
    state["original_query"] = data.get("initial_query", "")
    
    # Extract intent analysis results
    stages = data.get("stages", {})
    
    if "intent_analysis" in stages:
        intent_result = stages["intent_analysis"].get("result", {})
        state["intent_result"] = intent_result.get("intent", intent_result)
    
    # Extract data gathering results
    if "data_gathering" in stages:
        data_result = stages["data_gathering"].get("result", {})
        state["consolidated_data"] = data_result.get("consolidated_information", {})
        state["data_sources"] = data_result.get("sources", {})
    
    # Extract analysis results
    if "analysis_compilation" in stages:
        analysis_result = stages["analysis_compilation"].get("result", {})
        state["analysis_result"] = analysis_result
    
    # Extract report if available
    if "report_generation" in stages:
        report_result = stages["report_generation"].get("result", {})
        state["report_content"] = report_result.get("content", "")
        state["report_metadata"] = report_result.get("metadata", {})
    
    return state


def get_session_report_path(session_file: str) -> Optional[str]:
    """
    Get the report file path from a legacy session.
    
    Args:
        session_file: Path to the legacy session JSON file
        
    Returns:
        Path to the generated report, or None if not available
    """
    try:
        with open(session_file, 'r') as f:
            data = json.load(f)
        
        stages = data.get("stages", {})
        if "report_generation" in stages:
            result = stages["report_generation"].get("result", {})
            return result.get("file_path")
        
        # Also check final_report field
        final_report = data.get("final_report", {})
        return final_report.get("file_path")
        
    except Exception:
        return None


def archive_legacy_sessions(
    sessions_path: str = "./sessions",
    archive_path: str = "./sessions/archive"
) -> Dict[str, Any]:
    """
    Archive legacy session files.
    
    Moves all legacy session files to an archive directory.
    
    Args:
        sessions_path: Path to sessions directory
        archive_path: Path to archive directory
        
    Returns:
        Summary of archived files
    """
    sessions_dir = Path(sessions_path)
    archive_dir = Path(archive_path)
    
    if not sessions_dir.exists():
        return {"error": "Sessions directory not found", "archived": 0}
    
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    archived = []
    errors = []
    
    for session_file in sessions_dir.glob("session_*.json"):
        try:
            dest = archive_dir / session_file.name
            session_file.rename(dest)
            archived.append(str(dest))
        except Exception as e:
            errors.append({"file": str(session_file), "error": str(e)})
    
    return {
        "archived": len(archived),
        "archived_files": archived,
        "errors": errors,
        "archive_path": str(archive_dir),
    }


def print_migration_status():
    """Print a summary of migration status for legacy sessions."""
    sessions = list_legacy_sessions()
    
    print("\n=== Legacy Session Migration Status ===\n")
    print(f"Total legacy sessions: {len(sessions)}")
    
    if not sessions:
        print("No legacy sessions found.")
        return
    
    # Count by status
    status_counts = {}
    for session in sessions:
        status = session.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\nBy Status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    
    print("\nRecent Sessions:")
    for session in sessions[:5]:
        print(f"  - {session['session_id'][:8]}... | {session['status']} | {session['initial_query'][:40]}...")
    
    print("\nNote: Legacy sessions can still be accessed using --legacy mode.")
    print("ADK mode uses in-memory sessions by default.")


if __name__ == "__main__":
    print_migration_status()

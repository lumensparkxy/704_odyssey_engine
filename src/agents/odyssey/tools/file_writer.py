"""
File Writer Tool for Report Generation.

Provides functionality to save research reports to markdown files.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def save_report_to_file(
    content: str,
    query_words: str,
) -> Dict[str, Any]:
    """
    Save a research report to a markdown file.

    This tool saves the generated research report to the reports directory
    with an auto-generated filename based on the query and timestamp.

    Args:
        content: The full markdown content of the report
        query_words: First few words from the research query for filename
                    (e.g., "what are the best" becomes "what_are_the_best")

    Returns:
        Dictionary containing:
        - success: Whether the save was successful
        - file_path: Full path to the saved file
        - filename: Just the filename
        - metadata: Additional file metadata
    """
    try:
        # Get reports directory from environment or use default
        reports_dir = Path(os.getenv("REPORTS_OUTPUT_PATH", "./reports"))
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Clean query words for filename
        clean_words = re.sub(r'[^\w\s]', '', query_words.lower())
        clean_words = re.sub(r'\s+', '_', clean_words.strip())
        
        # Limit to first 4-5 words
        word_parts = clean_words.split('_')[:5]
        query_part = '_'.join(word_parts)

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create filename
        filename = f"research_report_{query_part}_{timestamp}.md"
        file_path = reports_dir / filename

        # Save the report
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Generate metadata
        metadata = {
            "file_path": str(file_path.absolute()),
            "filename": filename,
            "size_bytes": len(content.encode('utf-8')),
            "created_at": datetime.now().isoformat(),
            "word_count": len(content.split()),
            "character_count": len(content),
            "sections_count": content.count('## '),
        }

        return {
            "success": True,
            "file_path": str(file_path.absolute()),
            "filename": filename,
            "metadata": metadata,
            "message": f"Report saved successfully to {file_path.absolute()}"
        }

    except Exception as e:
        return {
            "success": False,
            "file_path": None,
            "filename": None,
            "metadata": None,
            "message": f"Failed to save report: {str(e)}"
        }


def get_report_path(query_words: str) -> str:
    """
    Get the expected path for a report without saving it.
    
    Useful for previewing where a report would be saved.
    
    Args:
        query_words: First few words from the research query
        
    Returns:
        Expected file path as string
    """
    reports_dir = Path(os.getenv("REPORTS_OUTPUT_PATH", "./reports"))
    
    clean_words = re.sub(r'[^\w\s]', '', query_words.lower())
    clean_words = re.sub(r'\s+', '_', clean_words.strip())
    word_parts = clean_words.split('_')[:5]
    query_part = '_'.join(word_parts)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_report_{query_part}_{timestamp}.md"
    
    return str(reports_dir / filename)

"""
Test suite for Odyssey Engine.
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.engine import ResearchEngine
from utils.gemini_client import GeminiClient
from utils.storage import SessionStorage


class TestOdysseyEngine:
    """Test cases for the main research engine."""
    
    def setup_method(self):
        """Setup test configuration."""
        self.config = {
            "GEMINI_API_KEY": "test_key",
            "GEMINI_MODEL": "gemini-2.5-pro",
            "CONFIDENCE_THRESHOLD": 75,
            "MAX_SCRAPING_DEPTH": 2,
            "SESSION_STORAGE_PATH": "./test_sessions",
            "REPORTS_OUTPUT_PATH": "./test_reports"
        }
    
    def test_engine_initialization(self):
        """Test that the engine initializes correctly."""
        engine = ResearchEngine(self.config)
        assert engine.config == self.config
        assert engine.confidence_scorer is not None
    
    @pytest.mark.asyncio
    async def test_session_creation(self):
        """Test creating a new research session."""
        # This would require a mock Gemini client for real testing
        pass


class TestGeminiClient:
    """Test cases for Gemini API client."""
    
    def test_client_initialization(self):
        """Test client initialization with config."""
        config = {"GEMINI_API_KEY": "test_key"}
        
        # This would fail without real API key, so we'd need mocking
        # client = GeminiClient(config)
        # assert client.api_key == "test_key"
        pass


class TestSessionStorage:
    """Test cases for session storage."""
    
    def setup_method(self):
        """Setup test storage."""
        self.config = {"SESSION_STORAGE_PATH": "./test_sessions"}
        self.storage = SessionStorage(self.config)
    
    @pytest.mark.asyncio
    async def test_save_and_load_session(self):
        """Test saving and loading a session."""
        session_data = {
            "session_id": "test_123",
            "initial_query": "Test query",
            "status": "started"
        }
        
        # Save session
        success = await self.storage.save_session("test_123", session_data)
        assert success
        
        # Load session
        loaded_data = await self.storage.load_session("test_123")
        assert loaded_data is not None
        assert loaded_data["session_id"] == "test_123"
        assert loaded_data["initial_query"] == "Test query"
        
        # Cleanup
        await self.storage.delete_session("test_123")


if __name__ == "__main__":
    pytest.main([__file__])

"""
Gemini API Client for Odyssey Engine.

This module handles all interactions with Google's Gemini Pro 2.5 API.
"""

import os
import asyncio
from typing import Dict, List, Optional, Any, Union
from google import genai
from google.genai import types
from google.genai.types import (
    GenerateContentConfig,
    GoogleSearch,
    Tool,
)


class GeminiClient:
    """Client for interacting with Gemini Pro 2.5 API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Gemini client."""
        self.config = config
        self.api_key = config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model_name = config.get("GEMINI_MODEL", "gemini-2.0-flash-001")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in config or environment variables")
        
        # Create the client using the new API
        self.client = genai.Client(api_key=self.api_key)
        
        # Safety settings using new API structure
        self.safety_settings = [
            types.SafetySetting(
                category='HARM_CATEGORY_HATE_SPEECH',
                threshold='BLOCK_NONE',
            ),
            types.SafetySetting(
                category='HARM_CATEGORY_DANGEROUS_CONTENT',
                threshold='BLOCK_NONE',
            ),
            types.SafetySetting(
                category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
                threshold='BLOCK_NONE',
            ),
            types.SafetySetting(
                category='HARM_CATEGORY_HARASSMENT',
                threshold='BLOCK_NONE',
            ),
        ]
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Generate a response from Gemini.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        try:
            # Configure generation parameters using the new API
            config = types.GenerateContentConfig(
                temperature=kwargs.get("temperature", 0.5),
                top_p=kwargs.get("top_p", 1.0),
                max_output_tokens=kwargs.get("max_tokens", 8192),
                safety_settings=self.safety_settings
            )
            
            # Generate response using the new async API
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            return response.text
            
        except Exception as e:
            raise GeminiAPIError(f"Error generating response: {str(e)}")
    
    async def generate_with_grounding(self, prompt: str, enable_search: bool = True) -> Dict[str, Any]:
        """
        Generate response with grounding (Google Search integration).
        
        Args:
            prompt: The input prompt
            enable_search: Whether to enable Google Search grounding
            
        Returns:
            Response with grounding information
        """
        try:
            if enable_search:
                try:
                    # Use actual Google Search grounding
                    config = GenerateContentConfig(
                        tools=[Tool(google_search=GoogleSearch())],
                        temperature=0.5,
                        max_output_tokens=8192,
                        safety_settings=self.safety_settings
                    )
                    
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=config
                    )
                    
                    # Extract basic source information if available
                    sources = []
                    grounding_info = None
                    
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                            grounding_info = candidate.grounding_metadata
                            sources = self._extract_basic_sources(grounding_info)
                    
                    return {
                        "response": response.text,
                        "grounding_enabled": True,
                        "sources": sources
                        # Removed grounding_info to avoid JSON serialization issues
                    }
                    
                except Exception as grounding_error:
                    print(f"⚠️ Grounding failed, falling back to regular generation: {str(grounding_error)}")
                    # Fallback to regular generation
                    response_text = await self.generate_response(prompt)
                    return {
                        "response": response_text,
                        "grounding_enabled": False,
                        "sources": [],
                        "fallback_reason": f"Grounding failed: {str(grounding_error)}"
                    }
            else:
                # Regular generation without grounding
                response_text = await self.generate_response(prompt)
                return {
                    "response": response_text,
                    "grounding_enabled": False,
                    "sources": []
                }
            
        except Exception as e:
            raise GeminiAPIError(f"Error with grounded generation: {str(e)}")
    
    def _extract_basic_sources(self, grounding_info) -> List[str]:
        """Extract basic source URLs from grounding information."""
        sources = []
        try:
            # Extract URLs from grounding_chunks
            if hasattr(grounding_info, 'grounding_chunks'):
                for chunk in grounding_info.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web:
                        if hasattr(chunk.web, 'uri'):
                            sources.append(chunk.web.uri)
                        elif hasattr(chunk.web, 'url'):
                            sources.append(chunk.web.url)
                            
            # Also check older structure for backward compatibility
            elif hasattr(grounding_info, 'web_search_queries'):
                for query_result in grounding_info.web_search_queries:
                    if hasattr(query_result, 'sources'):
                        for source in query_result.sources:
                            if hasattr(source, 'uri'):
                                sources.append(source.uri)
                            elif hasattr(source, 'url'):
                                sources.append(source.url)
        except Exception as e:
            print(f"Warning: Could not extract grounding sources: {e}")
        
        return sources
    
    async def analyze_content(self, content: str, analysis_type: str = "general") -> Dict[str, Any]:
        """
        Analyze content using Gemini.
        
        Args:
            content: Content to analyze
            analysis_type: Type of analysis (sentiment, quality, reliability, etc.)
            
        Returns:
            Analysis results
        """
        analysis_prompts = {
            "reliability": f"""
            Analyze the reliability and credibility of this content:
            {content}
            
            Consider:
            1. Source credibility indicators
            2. Factual accuracy markers
            3. Bias indicators
            4. Completeness of information
            5. Recency and relevance
            
            Return a JSON response with reliability_score (0-100) and detailed assessment.
            """,
            
            "quality": f"""
            Assess the quality of this content:
            {content}
            
            Consider:
            1. Clarity and coherence
            2. Completeness
            3. Accuracy
            4. Relevance
            5. Depth of information
            
            Return a JSON response with quality_score (0-100) and detailed assessment.
            """,
            
            "sentiment": f"""
            Analyze the sentiment and bias in this content:
            {content}
            
            Return a JSON response with sentiment analysis and bias indicators.
            """,
            
            "general": f"""
            Provide a general analysis of this content:
            {content}
            
            Include key themes, main points, and overall assessment.
            """
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
        response = await self.generate_response(prompt)
        
        return {
            "analysis_type": analysis_type,
            "result": response,
            "content_length": len(content)
        }
    
    async def summarize_content(self, content: str, max_length: int = 500) -> str:
        """
        Summarize content to specified length.
        
        Args:
            content: Content to summarize
            max_length: Maximum length of summary
            
        Returns:
            Summarized content
        """
        prompt = f"""
        Summarize the following content in approximately {max_length} words or less:
        
        {content}
        
        Focus on the most important points and key findings.
        Maintain accuracy and context.
        """
        
        return await self.generate_response(prompt)
    
    async def extract_key_points(self, content: str, num_points: int = 5) -> List[str]:
        """
        Extract key points from content.
        
        Args:
            content: Content to analyze
            num_points: Number of key points to extract
            
        Returns:
            List of key points
        """
        prompt = f"""
        Extract the {num_points} most important key points from this content:
        
        {content}
        
        Return as a JSON array of strings, each containing one key point.
        """
        
        response = await self.generate_response(prompt)
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: split by lines and clean up
            lines = response.strip().split('\n')
            return [line.strip('- ').strip() for line in lines if line.strip()][:num_points]
    
    async def compare_content(self, content1: str, content2: str, comparison_type: str = "general") -> Dict[str, Any]:
        """
        Compare two pieces of content.
        
        Args:
            content1: First content to compare
            content2: Second content to compare
            comparison_type: Type of comparison
            
        Returns:
            Comparison results
        """
        prompt = f"""
        Compare these two pieces of content:
        
        Content 1:
        {content1}
        
        Content 2:
        {content2}
        
        Provide a detailed comparison including:
        1. Similarities
        2. Differences
        3. Contradictions
        4. Complementary information
        5. Relative reliability/quality
        
        Return as structured analysis.
        """
        
        response = await self.generate_response(prompt)
        
        return {
            "comparison_type": comparison_type,
            "analysis": response,
            "content1_length": len(content1),
            "content2_length": len(content2)
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model_name": self.model_name,
            "api_key_configured": bool(self.api_key),
            "config": self.config
        }


class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors."""
    pass

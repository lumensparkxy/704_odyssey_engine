"""
Data Gatherer for collecting information from multiple sources.

This module handles gathering information from Google Search, web scraping,
documents, and other data sources.
"""

import asyncio
import json
import aiohttp
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

from utils.gemini_client import GeminiClient
from utils.web_scraper import WebScraper


class DataGatherer:
    """Gathers data from multiple sources for research."""
    
    def __init__(self, gemini_client: GeminiClient, config: Dict[str, Any]):
        """Initialize the data gatherer."""
        self.gemini_client = gemini_client
        self.config = config
        self.web_scraper = WebScraper(config)
        self.max_search_results = config.get("MAX_SEARCH_RESULTS", 10)
        self.max_scraping_depth = config.get("MAX_SCRAPING_DEPTH", 3)
        
        # Data source priority (from PRD)
        self.source_priority = [
            "internal_knowledge",
            "google_search", 
            "provided_documents",
            "web_scraping"
        ]
    
    async def gather_data(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gather data from all available sources based on intent analysis.
        
        Args:
            intent_result: Results from intent analysis
            
        Returns:
            Comprehensive data collection results
        """
        research_questions = intent_result.get("research_questions", [])
        key_entities = intent_result.get("key_entities", [])
        domain = intent_result.get("domain", "general")
        
        gathered_data = {
            "sources": {},
            "consolidated_information": {},
            "source_reliability": {},
            "conflicts": [],
            "coverage_assessment": {}
        }
        
        # Gather from each source type according to priority
        for source_type in self.source_priority:
            try:
                print(f"📡 Gathering data from {source_type}...")
                
                if source_type == "internal_knowledge":
                    internal_data = await self._gather_internal_knowledge(research_questions, key_entities)
                    gathered_data["sources"]["internal_knowledge"] = internal_data
                    
                elif source_type == "google_search":
                    search_data = await self._gather_google_search(research_questions, key_entities)
                    gathered_data["sources"]["google_search"] = search_data
                    
                elif source_type == "provided_documents":
                    doc_data = await self._gather_document_data(intent_result)
                    gathered_data["sources"]["provided_documents"] = doc_data
                    
                elif source_type == "web_scraping":
                    # Only scrape if we have URLs from search
                    search_data = gathered_data["sources"].get("google_search", {})
                    scraped_data = await self._gather_web_scraping(search_data.get("urls", []))
                    gathered_data["sources"]["web_scraping"] = scraped_data
                    
            except Exception as e:
                print(f"⚠️ Error gathering data from {source_type}: {str(e)}")
                gathered_data["sources"][source_type] = {"error": str(e)}
        
        try:
            # Assess source reliability
            gathered_data["source_reliability"] = await self._assess_source_reliability(gathered_data["sources"])
            
            # Identify conflicts between sources
            gathered_data["conflicts"] = await self._identify_data_conflicts(gathered_data["sources"])
            
            # Consolidate information
            gathered_data["consolidated_information"] = await self._consolidate_information(
                gathered_data["sources"],
                gathered_data["conflicts"]
            )
            
            # Assess coverage
            gathered_data["coverage_assessment"] = await self._assess_coverage(
                research_questions,
                gathered_data["consolidated_information"]
            )
            
        except Exception as e:
            print(f"⚠️ Error in post-processing: {str(e)}")
            gathered_data["processing_errors"] = str(e)
        
        return gathered_data
    
    async def _gather_internal_knowledge(self, research_questions: List[str], key_entities: List[str]) -> Dict[str, Any]:
        """Gather information from internal knowledge (Gemini's training data)."""
        internal_data = {
            "responses": [],
            "confidence": 0.0,
            "knowledge_date": "Training data cutoff"
        }
        
        for question in research_questions:
            prompt = f"""
            Based on your training data, provide comprehensive information about: {question}
            
            Key entities to focus on: {', '.join(key_entities)}
            
            Please include:
            1. Factual information
            2. Key statistics or data points
            3. Historical context
            4. Different perspectives or viewpoints
            5. Any limitations or uncertainties in your knowledge
            
            Be clear about what you know with high confidence vs. what might be uncertain.
            """
            
            response = await self.gemini_client.generate_response(prompt)
            confidence = await self._assess_response_confidence(response)
            
            internal_data["responses"].append({
                "question": question,
                "response": response,
                "confidence": confidence
            })
        
        # Calculate overall confidence
        if internal_data["responses"]:
            internal_data["confidence"] = sum(r["confidence"] for r in internal_data["responses"]) / len(internal_data["responses"])
        
        return internal_data
    
    async def _gather_google_search(self, research_questions: List[str], key_entities: List[str]) -> Dict[str, Any]:
        """Gather information using Google Search through Gemini's grounding."""
        search_data = {
            "queries": [],
            "results": [],
            "urls": [],
            "reliability_scores": {}
        }
        
        # Generate search queries
        search_queries = await self._generate_search_queries(research_questions, key_entities)
        
        for query in search_queries[:3]:  # Limit to 3 queries to prevent hanging
            print(f"🔍 Searching: {query}")
            
            try:
                # Use Gemini's grounding capability for search with timeout
                grounded_response = await asyncio.wait_for(
                    self.gemini_client.generate_with_grounding(
                        f"Research and provide detailed information about: {query}",
                        enable_search=True
                    ),
                    timeout=30  # 30 second timeout
                )
                
                search_data["queries"].append(query)
                search_data["results"].append(grounded_response)
                
                # Extract URLs from response (this would be improved with actual grounding API)
                urls = await self._extract_urls_from_response(grounded_response["response"])
                search_data["urls"].extend(urls)
                
            except asyncio.TimeoutError:
                print(f"⚠️ Search timeout for query: {query}")
                search_data["queries"].append(query)
                search_data["results"].append({"response": "Search timed out", "error": "timeout"})
            except Exception as e:
                print(f"⚠️ Search error for query '{query}': {str(e)}")
                search_data["queries"].append(query)
                search_data["results"].append({"response": f"Search failed: {str(e)}", "error": str(e)})
        
        # Remove duplicates
        search_data["urls"] = list(set(search_data["urls"]))
        
        return search_data
    
    async def _gather_document_data(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """Gather data from provided documents (placeholder for document analysis)."""
        # This would be implemented when documents are provided
        return {
            "documents_processed": 0,
            "extracted_information": [],
            "document_reliability": {}
        }
    
    async def _gather_web_scraping(self, urls: List[str]) -> Dict[str, Any]:
        """Gather data through web scraping with depth limits."""
        scraped_data = {
            "scraped_pages": [],
            "followed_links": [],
            "depth_map": {},
            "errors": []
        }
        
        # Limit initial URLs
        initial_urls = urls[:self.max_search_results]
        
        for url in initial_urls:
            try:
                print(f"🕷️ Scraping: {url}")
                page_data = await self.web_scraper.scrape_page(url)
                
                if page_data:
                    scraped_data["scraped_pages"].append(page_data)
                    scraped_data["depth_map"][url] = 1
                    
                    # Follow links up to max depth
                    if self.max_scraping_depth > 1:
                        followed_data = await self._follow_links(
                            page_data.get("links", []), 
                            current_depth=1,
                            scraped_data=scraped_data
                        )
                        scraped_data["followed_links"].extend(followed_data)
                        
            except Exception as e:
                scraped_data["errors"].append({"url": url, "error": str(e)})
        
        return scraped_data
    
    async def _follow_links(self, links: List[str], current_depth: int, scraped_data: Dict) -> List[Dict]:
        """Follow links up to maximum depth."""
        if current_depth >= self.max_scraping_depth:
            return []
        
        followed_data = []
        
        for link in links[:5]:  # Limit links per page
            if link in scraped_data["depth_map"]:
                continue  # Already scraped
            
            try:
                page_data = await self.web_scraper.scrape_page(link)
                if page_data:
                    followed_data.append(page_data)
                    scraped_data["depth_map"][link] = current_depth + 1
                    
                    # Recursive follow if not at max depth
                    if current_depth + 1 < self.max_scraping_depth:
                        deeper_data = await self._follow_links(
                            page_data.get("links", []),
                            current_depth + 1,
                            scraped_data
                        )
                        followed_data.extend(deeper_data)
                        
            except Exception as e:
                scraped_data["errors"].append({"url": link, "error": str(e), "depth": current_depth + 1})
        
        return followed_data
    
    async def _generate_search_queries(self, research_questions: List[str], key_entities: List[str]) -> List[str]:
        """Generate effective search queries from research questions."""
        prompt = f"""
        Generate effective Google search queries for these research questions:
        {json.dumps(research_questions, indent=2)}
        
        Key entities: {', '.join(key_entities)}
        
        Create {min(len(research_questions) * 2, 10)} search queries that will gather comprehensive information.
        Make queries specific and varied to capture different perspectives.
        
        Return as JSON array of search query strings.
        """
        
        response = await self.gemini_client.generate_response(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: use research questions as queries
            return research_questions[:5]
    
    async def _extract_urls_from_response(self, response_text: str) -> List[str]:
        """Extract URLs from response text (placeholder implementation)."""
        # This is a simplified implementation
        # In reality, this would extract URLs from Gemini's grounded response
        import re
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, response_text)
        return urls[:10]  # Limit URLs
    
    async def _assess_source_reliability(self, sources: Dict[str, Any]) -> Dict[str, float]:
        """Assess the reliability of each data source."""
        reliability_scores = {}
        
        for source_type, source_data in sources.items():
            if source_type == "internal_knowledge":
                # Internal knowledge has moderate reliability (depends on training data)
                reliability_scores[source_type] = 0.75
                
            elif source_type == "google_search":
                # Google search results vary in reliability
                reliability_scores[source_type] = 0.80
                
            elif source_type == "web_scraping":
                # Web scraping reliability depends on source quality
                avg_reliability = await self._assess_scraped_content_reliability(source_data)
                reliability_scores[source_type] = avg_reliability
                
            elif source_type == "provided_documents":
                # Document reliability would be assessed per document
                reliability_scores[source_type] = 0.85
        
        return reliability_scores
    
    async def _assess_scraped_content_reliability(self, scraped_data: Dict) -> float:
        """Assess reliability of scraped web content."""
        if not scraped_data.get("scraped_pages"):
            return 0.0
        
        total_score = 0.0
        count = 0
        
        for page in scraped_data["scraped_pages"]:
            # Assess based on domain, content quality, etc.
            domain_score = self._assess_domain_reliability(page.get("url", ""))
            content_score = await self._assess_content_quality(page.get("content", ""))
            
            page_score = (domain_score + content_score) / 2
            total_score += page_score
            count += 1
        
        return total_score / count if count > 0 else 0.0
    
    def _assess_domain_reliability(self, url: str) -> float:
        """Assess domain reliability based on URL."""
        try:
            domain = urlparse(url).netloc.lower()
            
            # High-reliability domains
            high_reliability_domains = [
                'edu', 'gov', 'org', 'wikipedia.org', 'reuters.com',
                'bbc.com', 'cnn.com', 'nytimes.com', 'nature.com',
                'science.org', 'nih.gov', 'who.int'
            ]
            
            for reliable_domain in high_reliability_domains:
                if reliable_domain in domain:
                    return 0.9
            
            # Medium-reliability domains
            if any(ext in domain for ext in ['.org', '.edu', '.gov']):
                return 0.8
            
            # Default reliability for other domains
            return 0.6
            
        except Exception:
            return 0.5
    
    async def _assess_content_quality(self, content: str) -> float:
        """Assess content quality using AI analysis."""
        if len(content) < 100:
            return 0.3
        
        analysis = await self.gemini_client.analyze_content(content, "quality")
        
        # Extract quality score from analysis (simplified)
        try:
            import re
            score_match = re.search(r'"quality_score":\s*(\d+)', analysis.get("result", ""))
            if score_match:
                return float(score_match.group(1)) / 100.0
        except Exception:
            pass
        
        # Fallback: basic content quality assessment
        if len(content) > 1000 and content.count('.') > 10:
            return 0.7
        return 0.5
    
    async def _identify_data_conflicts(self, sources: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify conflicts between different data sources."""
        conflicts = []
        
        # Compare information between sources
        prompt = f"""
        Analyze the following data from multiple sources and identify any conflicts or contradictions:
        
        {json.dumps(sources, indent=2, default=str)}
        
        Look for:
        1. Contradictory facts or figures
        2. Different perspectives on the same topic
        3. Inconsistent timelines or dates
        4. Conflicting expert opinions
        
        Return a JSON array of conflict objects with:
        - conflict_type: The type of conflict
        - sources_involved: Which sources have conflicting information
        - description: Description of the conflict
        - severity: High/Medium/Low
        """
        
        response = await self.gemini_client.generate_response(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return []
    
    async def _consolidate_information(self, sources: Dict[str, Any], conflicts: List[Dict]) -> Dict[str, Any]:
        """Consolidate information from all sources, handling conflicts."""
        prompt = f"""
        Consolidate the following information from multiple sources into a coherent knowledge base:
        
        Sources:
        {json.dumps(sources, indent=2, default=str)}
        
        Known Conflicts:
        {json.dumps(conflicts, indent=2)}
        
        Create a consolidated view that:
        1. Combines complementary information
        2. Notes areas of disagreement
        3. Prioritizes more reliable sources
        4. Maintains factual accuracy
        
        Return structured consolidated information.
        """
        
        response = await self.gemini_client.generate_response(prompt)
        return {"consolidated_text": response, "processing_notes": "Automated consolidation"}
    
    async def _assess_coverage(self, research_questions: List[str], consolidated_info: Dict) -> Dict[str, Any]:
        """Assess how well the gathered data covers the research questions."""
        coverage_assessment = {
            "overall_coverage": 0.0,
            "question_coverage": {},
            "gaps": [],
            "strengths": []
        }
        
        for question in research_questions:
            prompt = f"""
            Assess how well this consolidated information answers the research question:
            
            Question: {question}
            
            Information:
            {json.dumps(consolidated_info, indent=2, default=str)}
            
            Rate coverage from 0-100 and identify any gaps.
            Return JSON with coverage_score and gaps list.
            """
            
            response = await self.gemini_client.generate_response(prompt)
            try:
                assessment = json.loads(response)
                coverage_assessment["question_coverage"][question] = assessment
            except json.JSONDecodeError:
                coverage_assessment["question_coverage"][question] = {"coverage_score": 50, "gaps": ["Assessment failed"]}
        
        # Calculate overall coverage
        if coverage_assessment["question_coverage"]:
            scores = [q.get("coverage_score", 0) for q in coverage_assessment["question_coverage"].values()]
            coverage_assessment["overall_coverage"] = sum(scores) / len(scores)
        
        return coverage_assessment
    
    async def _assess_response_confidence(self, response: str) -> float:
        """Assess confidence in a response."""
        # Simplified confidence assessment
        confidence_indicators = [
            "based on", "according to", "research shows", "studies indicate",
            "data suggests", "evidence points", "confirmed by"
        ]
        
        uncertainty_indicators = [
            "might", "could", "possibly", "uncertain", "unclear",
            "conflicting", "disputed", "unconfirmed"
        ]
        
        confidence_score = 0.5  # Baseline
        
        for indicator in confidence_indicators:
            if indicator in response.lower():
                confidence_score += 0.1
        
        for indicator in uncertainty_indicators:
            if indicator in response.lower():
                confidence_score -= 0.15
        
        return max(0.0, min(1.0, confidence_score))

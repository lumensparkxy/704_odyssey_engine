"""
Report Generator for Odyssey Engine.

This module generates comprehensive markdown reports from analyzed research data.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

from utils.gemini_client import GeminiClient


class ReportGenerator:
    """Generates comprehensive research reports in markdown format."""
    
    def __init__(self, gemini_client: GeminiClient, config: Dict[str, Any]):
        """Initialize the report generator."""
        self.gemini_client = gemini_client
        self.config = config
        self.reports_path = Path(config.get("REPORTS_OUTPUT_PATH", "./reports"))
        self.reports_path.mkdir(exist_ok=True)
        
        # Report configuration
        self.default_tone = config.get("DEFAULT_REPORT_TONE", "formal_accessible")
        self.include_confidence = config.get("INCLUDE_CONFIDENCE_SCORES", True)
        self.include_reliability = config.get("INCLUDE_SOURCE_RELIABILITY", True)
    
    async def generate_report(self, intent_result: Dict, data_result: Dict, analysis_result: Dict) -> Dict[str, Any]:
        """
        Generate a comprehensive research report.
        
        Args:
            intent_result: Results from intent analysis
            data_result: Results from data gathering
            analysis_result: Results from analysis and compilation
            
        Returns:
            Report generation results including file path and metadata
        """
        print("📝 Generating comprehensive report...")
        
        # Extract report configuration from intent
        report_config = self._extract_report_config(intent_result)
        
        # Generate each section of the report
        sections = {}
        
        # Executive Summary
        sections["executive_summary"] = await self._generate_executive_summary(
            intent_result, data_result, analysis_result
        )
        
        # Key Findings
        sections["key_findings"] = await self._generate_key_findings(
            data_result, analysis_result
        )
        
        # Detailed Sections
        sections["detailed_sections"] = await self._generate_detailed_sections(
            intent_result, data_result, analysis_result
        )
        
        # Contradictory Viewpoints
        sections["contradictory_viewpoints"] = await self._generate_contradictory_viewpoints(
            data_result, analysis_result
        )
        
        # Bibliography
        sections["bibliography"] = self._generate_bibliography(data_result)
        
        # Compile full report
        full_report = self._compile_report(sections, report_config, intent_result)
        
        # Save report to file
        report_metadata = await self._save_report(full_report, intent_result)
        
        return {
            "content": full_report,
            "file_path": report_metadata["file_path"],
            "metadata": report_metadata,
            "sections": sections,
            "word_count": len(full_report.split()),
            "generation_time": datetime.now().isoformat()
        }
    
    def _extract_report_config(self, intent_result: Dict) -> Dict[str, Any]:
        """Extract report configuration from intent analysis."""
        return {
            "tone": intent_result.get("output_preferences", {}).get("tone", self.default_tone),
            "format_preferences": intent_result.get("output_preferences", {}).get("formats", ["comprehensive_report"]),
            "research_type": intent_result.get("research_type", "general_research"),
            "domain": intent_result.get("domain", "general"),
            "include_visuals": "visual_charts" in intent_result.get("output_preferences", {}).get("formats", [])
        }
    
    async def _generate_executive_summary(self, intent_result: Dict, data_result: Dict, analysis_result: Dict) -> str:
        """Generate executive summary section."""
        prompt = f"""
        Generate an executive summary for a research report with the following information:
        
        Research Intent:
        {json.dumps(intent_result, indent=2)}
        
        Key Analysis Results:
        {json.dumps(analysis_result.get("summaries", {}), indent=2)}
        
        Create a concise executive summary (200-300 words) that:
        1. States the research objective clearly
        2. Highlights the most important findings
        3. Mentions key conclusions or insights
        4. Notes any significant limitations
        
        Use a {intent_result.get('output_preferences', {}).get('tone', 'formal_accessible')} tone.
        """
        
        return await self.gemini_client.generate_response(prompt)
    
    async def _generate_key_findings(self, data_result: Dict, analysis_result: Dict) -> str:
        """Generate key findings section."""
        prompt = f"""
        Generate a key findings section based on this research data and analysis:
        
        Data Summary:
        {json.dumps(data_result.get("consolidated_information", {}), indent=2, default=str)}
        
        Analysis Results:
        {json.dumps(analysis_result, indent=2, default=str)}
        
        Create a clear key findings section that:
        1. Lists 5-8 most important findings as bullet points
        2. Includes specific data points and statistics where available
        3. Groups related findings logically
        4. Uses clear, factual language
        5. Includes comparison tables if comparison data is available
        
        Format as markdown with appropriate headers and bullet points.
        """
        
        return await self.gemini_client.generate_response(prompt)
    
    async def _generate_detailed_sections(self, intent_result: Dict, data_result: Dict, analysis_result: Dict) -> str:
        """Generate detailed analysis sections."""
        research_questions = intent_result.get("research_questions", [])
        themes = analysis_result.get("themes", [])
        
        sections_content = []
        
        # Generate sections based on research questions
        for i, question in enumerate(research_questions, 1):
            section_content = await self._generate_question_section(question, data_result, analysis_result)
            sections_content.append(f"## {i}. {self._create_section_title(question)}\n\n{section_content}")
        
        # Generate sections based on identified themes
        for theme in themes:
            if isinstance(theme, dict) and theme.get("title"):
                theme_content = await self._generate_theme_section(theme, data_result)
                sections_content.append(f"## {theme['title']}\n\n{theme_content}")
        
        return "\n\n".join(sections_content)
    
    async def _generate_question_section(self, question: str, data_result: Dict, analysis_result: Dict) -> str:
        """Generate a detailed section for a research question."""
        prompt = f"""
        Generate a detailed section answering this research question:
        
        Question: {question}
        
        Available Data:
        {json.dumps(data_result.get("consolidated_information", {}), indent=2, default=str)}
        
        Analysis Context:
        {json.dumps(analysis_result, indent=2, default=str)}
        
        Create a comprehensive section (300-500 words) that:
        1. Directly addresses the research question
        2. Provides supporting evidence and data
        3. Includes multiple perspectives when available
        4. Cites specific sources
        5. Acknowledges uncertainties or limitations
        
        Use clear, informative language with proper markdown formatting.
        """
        
        return await self.gemini_client.generate_response(prompt)
    
    async def _generate_theme_section(self, theme: Dict, data_result: Dict) -> str:
        """Generate a section for an identified theme."""
        prompt = f"""
        Generate a detailed section about this theme:
        
        Theme: {json.dumps(theme, indent=2)}
        
        Supporting Data:
        {json.dumps(data_result.get("consolidated_information", {}), indent=2, default=str)}
        
        Create a focused section that:
        1. Explains the theme and its significance
        2. Provides supporting evidence
        3. Shows connections to the broader research topic
        4. Includes relevant examples or case studies
        
        Use informative, engaging language with proper markdown formatting.
        """
        
        return await self.gemini_client.generate_response(prompt)
    
    async def _generate_contradictory_viewpoints(self, data_result: Dict, analysis_result: Dict) -> str:
        """Generate section on contradictory viewpoints and conflicts."""
        conflicts = analysis_result.get("conflicts", [])
        
        if not conflicts:
            return "No significant contradictory viewpoints were identified in the research data."
        
        prompt = f"""
        Generate a section on contradictory viewpoints based on these identified conflicts:
        
        Conflicts:
        {json.dumps(conflicts, indent=2)}
        
        Source Reliability:
        {json.dumps(data_result.get("source_reliability", {}), indent=2)}
        
        Create a balanced section that:
        1. Presents each contradictory viewpoint fairly
        2. Explains the source of each viewpoint
        3. Assesses the reliability of conflicting sources
        4. Provides context for why conflicts might exist
        5. Avoids taking sides unless evidence strongly supports one view
        
        Use objective, analytical language.
        """
        
        return await self.gemini_client.generate_response(prompt)
    
    def _generate_bibliography(self, data_result: Dict) -> str:
        """Generate bibliography/sources section."""
        bibliography_entries = []
        
        # Process different source types
        sources = data_result.get("sources", {})
        
        # Google Search sources
        if "google_search" in sources:
            search_data = sources["google_search"]
            for i, url in enumerate(search_data.get("urls", []), 1):
                bibliography_entries.append(f"{i}. {url}")
        
        # Web scraping sources
        if "web_scraping" in sources:
            scraping_data = sources["web_scraping"]
            for page in scraping_data.get("scraped_pages", []):
                if page.get("success"):
                    title = page.get("title", "Untitled")
                    url = page.get("url")
                    scraped_time = page.get("scrape_time", "Unknown")
                    bibliography_entries.append(
                        f"- **{title}** - {url} (Accessed: {datetime.now().strftime('%Y-%m-%d')})"
                    )
        
        # Internal knowledge
        if "internal_knowledge" in sources:
            bibliography_entries.append("- Gemini AI Knowledge Base (Training data)")
        
        if not bibliography_entries:
            return "No external sources were used in this research."
        
        return "## Sources and References\n\n" + "\n".join(bibliography_entries)
    
    def _compile_report(self, sections: Dict[str, str], config: Dict[str, Any], intent_result: Dict) -> str:
        """Compile all sections into a full report."""
        original_query = intent_result.get("intent", {}).get("research_questions", ["Unknown query"])[0]
        report_title = self._generate_report_title(original_query, config["research_type"])
        
        report_parts = []
        
        # Header
        report_parts.append(f"# {report_title}\n")
        report_parts.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        report_parts.append(f"**Research Type:** {config['research_type'].replace('_', ' ').title()}")
        report_parts.append(f"**Domain:** {config['domain'].title()}")
        
        if self.include_confidence:
            report_parts.append(f"**Research Confidence:** See individual sections")
        
        report_parts.append("\n---\n")
        
        # Executive Summary
        report_parts.append("## Executive Summary\n")
        report_parts.append(sections["executive_summary"])
        
        # Key Findings
        report_parts.append("\n## Key Findings\n")
        report_parts.append(sections["key_findings"])
        
        # Detailed Sections
        if sections["detailed_sections"]:
            report_parts.append("\n## Detailed Analysis\n")
            report_parts.append(sections["detailed_sections"])
        
        # Contradictory Viewpoints
        report_parts.append("\n## Contradictory Viewpoints\n")
        report_parts.append(sections["contradictory_viewpoints"])
        
        # Bibliography
        report_parts.append("\n" + sections["bibliography"])
        
        # Footer
        report_parts.append("\n---\n")
        report_parts.append("*This report was generated by Odyssey Engine - Deep Research AI*")
        
        return "\n".join(report_parts)
    
    def _generate_report_title(self, query: str, research_type: str) -> str:
        """Generate an appropriate title for the report."""
        # Clean and shorten query for title
        clean_query = re.sub(r'[^\w\s]', '', query)
        words = clean_query.split()
        
        if len(words) > 8:
            title_base = " ".join(words[:8]) + "..."
        else:
            title_base = clean_query
        
        type_suffix = {
            "comparison": "Comparative Analysis",
            "analysis": "Research Analysis", 
            "timeline": "Timeline Analysis",
            "pros_cons": "Pros and Cons Analysis",
            "general_research": "Research Report"
        }.get(research_type, "Research Report")
        
        return f"{title_base.title()}: {type_suffix}"
    
    def _create_section_title(self, question: str) -> str:
        """Create a clean section title from a research question."""
        # Remove question words and clean up
        clean_title = re.sub(r'^(what|how|why|when|where|who|which)\s+', '', question, flags=re.IGNORECASE)
        clean_title = re.sub(r'\?$', '', clean_title)
        
        # Capitalize first letter
        if clean_title:
            clean_title = clean_title[0].upper() + clean_title[1:]
        
        return clean_title.strip()
    
    async def _save_report(self, report_content: str, intent_result: Dict) -> Dict[str, Any]:
        """Save report to file and return metadata."""
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_query = intent_result.get("intent", {}).get("research_questions", ["research"])[0]
        
        # Clean query for filename
        clean_query = re.sub(r'[^\w\s]', '', original_query)
        query_words = clean_query.split()[:4]  # First 4 words
        query_part = "_".join(query_words).lower()
        
        filename = f"research_report_{query_part}_{timestamp}.md"
        file_path = self.reports_path / filename
        
        # Save file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # Generate metadata
        metadata = {
            "file_path": str(file_path),
            "filename": filename,
            "size_bytes": len(report_content.encode('utf-8')),
            "created_at": datetime.now().isoformat(),
            "word_count": len(report_content.split()),
            "character_count": len(report_content),
            "sections_count": report_content.count('##')
        }
        
        return metadata
    
    async def generate_summary_report(self, report_content: str) -> str:
        """Generate a summary version of a full report."""
        prompt = f"""
        Create a concise summary (max 500 words) of this research report:
        
        {report_content}
        
        The summary should:
        1. Capture the main research question
        2. Highlight key findings (3-5 points)
        3. Note any important conclusions
        4. Mention significant limitations
        
        Use clear, accessible language.
        """
        
        return await self.gemini_client.generate_response(prompt)

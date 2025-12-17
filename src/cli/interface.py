"""
Command Line Interface for Odyssey Engine.

This module provides the main CLI interface for interacting with the research engine.
"""

from utils.storage import SessionStorage
from core.engine import ResearchEngine
import os
import sys
import asyncio
import click
from pathlib import Path
from typing import Dict, List, Optional, Any
from rich.console import Console  # type: ignore
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class OdysseyCLI:
    """Main CLI interface for Odyssey Engine."""

    def __init__(self):
        """Initialize the CLI."""
        self.console = Console()
        self.config = self._load_config()
        self.engine = ResearchEngine(self.config)
        self.storage = SessionStorage(self.config)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
            "CONFIDENCE_THRESHOLD": int(os.getenv("CONFIDENCE_THRESHOLD", "75")),
            "FORCE_CLARIFICATION_ON_UNCERTAINTY": os.getenv("FORCE_CLARIFICATION_ON_UNCERTAINTY", "true").lower() == "true",
            "MAX_SCRAPING_DEPTH": int(os.getenv("MAX_SCRAPING_DEPTH", "3")),
            "MAX_SEARCH_RESULTS": int(os.getenv("MAX_SEARCH_RESULTS", "10")),
            "MAX_FOLLOW_UP_QUESTIONS": int(os.getenv("MAX_FOLLOW_UP_QUESTIONS", "5")),
            "MAX_REMOTE_CALLS": int(os.getenv("MAX_REMOTE_CALLS", "10")),
            "SESSION_STORAGE_PATH": os.getenv("SESSION_STORAGE_PATH", "./sessions"),
            "REPORTS_OUTPUT_PATH": os.getenv("REPORTS_OUTPUT_PATH", "./reports"),
            "USER_AGENT": os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; OdysseyEngine/1.0)"),
            "REQUEST_TIMEOUT": int(os.getenv("REQUEST_TIMEOUT", "30")),
            "MAX_CONCURRENT_REQUESTS": int(os.getenv("MAX_CONCURRENT_REQUESTS", "5")),
            "DEFAULT_REPORT_TONE": os.getenv("DEFAULT_REPORT_TONE", "formal_accessible"),
            "INCLUDE_CONFIDENCE_SCORES": os.getenv("INCLUDE_CONFIDENCE_SCORES", "true").lower() == "true",
            "INCLUDE_SOURCE_RELIABILITY": os.getenv("INCLUDE_SOURCE_RELIABILITY", "true").lower() == "true"
        }

        return config

    async def run(self):
        """Main CLI entry point."""
        try:
            self._show_welcome()
            await self._check_configuration()
            await self._main_menu()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]👋 Goodbye![/yellow]")
        except Exception as e:
            self.console.print(f"[red]❌ Error: {str(e)}[/red]")

    def _show_welcome(self):
        """Show welcome message."""
        welcome_text = """
# 🔍 Odyssey Engine - Deep Research AI

Welcome to your intelligent research assistant! 

Odyssey Engine helps you conduct comprehensive research by:
- Understanding your research intent through conversation
- Gathering information from multiple sources
- Analyzing and synthesizing findings
- Generating detailed research reports

Let's start your research journey!
        """

        self.console.print(Panel(Markdown(welcome_text),
                           title="Welcome", border_style="blue"))

    async def _check_configuration(self):
        """Check if configuration is valid."""
        if not self.config.get("GEMINI_API_KEY"):
            self.console.print("[red]❌ Error: GEMINI_API_KEY not found![/red]")
            self.console.print(
                "Please set your Gemini API key in the .env file or environment variables.")
            self.console.print("Example: GEMINI_API_KEY=your_api_key_here")
            sys.exit(1)

        self.console.print(
            "[green]✅ Configuration loaded successfully[/green]")

    async def _main_menu(self):
        """Show main menu and handle user choices."""
        while True:
            self.console.print("\n" + "="*60)
            self.console.print(
                "[bold blue]🔍 Odyssey Engine - Main Menu[/bold blue]")
            self.console.print("="*60)

            options = [
                "1. Start New Research",
                "2. Continue Existing Research",
                "3. View Research Sessions",
                "4. View Generated Reports",
                "5. Settings & Configuration",
                "6. Help & Documentation",
                "7. Exit"
            ]

            for option in options:
                self.console.print(f"  {option}")

            choice = Prompt.ask(
                "\n[bold]Select an option[/bold]", choices=["1", "2", "3", "4", "5", "6", "7"])

            if choice == "1":
                await self._start_new_research()
            elif choice == "2":
                await self._continue_research()
            elif choice == "3":
                await self._view_sessions()
            elif choice == "4":
                await self._view_reports()
            elif choice == "5":
                await self._show_settings()
            elif choice == "6":
                self._show_help()
            elif choice == "7":
                self.console.print(
                    "[yellow]👋 Thank you for using Odyssey Engine![/yellow]")
                break

    async def _start_new_research(self):
        """Start a new research session."""
        self.console.print(
            "\n[bold blue]🚀 Starting New Research Session[/bold blue]")

        # Get initial query (supports multi-line input)
        query = self._get_research_query()

        if not query.strip():
            self.console.print(
                "[red]❌ Please provide a research question.[/red]")
            return

        # Start research session
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(
                "Initializing research session...", total=None)

            try:
                session_id = await self.engine.start_research_session(query)
                progress.update(task, description="Conducting research...")

                result = await self.engine.conduct_research(session_id)

                if result["status"] == "needs_clarification":
                    progress.stop()
                    await self._handle_clarification(session_id, result)
                elif result["status"] == "completed":
                    progress.update(task, description="Research completed!")
                    await self._show_research_results(result)
                elif result["status"] == "error":
                    progress.stop()
                    self.console.print(
                        f"[red]❌ Research failed: {result.get('error', 'Unknown error')}[/red]")
                    self.console.print(
                        "[yellow]Check the logs/odyssey.log file for more details.[/yellow]")
                else:
                    progress.stop()
                    self.console.print(
                        f"[red]❌ Research failed: {result.get('error', 'Unknown error')}[/red]")

            except Exception as e:
                progress.stop()
                self.console.print(
                    f"[red]❌ Error during research: {str(e)}[/red]")

    def _get_research_query(self) -> str:
        """Get the user's research query.

        Rich's Prompt is single-line by default, which makes multi-line pasted
        prompts awkward. This helper supports:

        - single-line input
        - multi-line input terminated by a sentinel line (default: END)
        - loading the query from a text/markdown file
        """
        mode = Prompt.ask(
            "\n[bold]Enter query mode[/bold]",
            choices=["single", "multiline", "file"],
            default="single",
            show_choices=True,
        )

        if mode == "single":
            return Prompt.ask("\n[bold]What would you like to research?[/bold]")

        if mode == "file":
            path_str = Prompt.ask(
                "\n[bold]Path to a prompt file (.txt/.md)[/bold]")
            file_path = Path(path_str).expanduser()
            try:
                return file_path.read_text(encoding="utf-8")
            except Exception as e:
                self.console.print(
                    f"[red]❌ Could not read file: {file_path}[/red]")
                self.console.print(f"[dim]{e}[/dim]")
                return ""

        # multiline
        return self._read_multiline_input(
            title="Paste your multi-line research prompt",
            terminator="END",
        )

    def _read_multiline_input(self, title: str, terminator: str = "END") -> str:
        """Read a multi-line block from stdin.

        Users can paste multi-line text, then finish by typing the terminator on
        a line by itself (or by sending EOF via Ctrl-D on macOS/Linux).
        """
        instructions = (
            f"{title}\n\n"
            f"Paste your text. When finished, type [bold]{terminator}[/bold] on its own line, then press Enter.\n"
            "Tip: You can also finish with Ctrl-D (EOF)."
        )
        self.console.print(Panel(instructions, border_style="blue"))
        self.console.print("[dim]— Start pasting below —[/dim]")

        lines: List[str] = []
        while True:
            try:
                line = input()
            except EOFError:
                break

            if line.strip() == terminator:
                break
            lines.append(line)

        # Preserve internal blank lines; just trim trailing newlines.
        return "\n".join(lines).strip("\n")

    async def _handle_clarification(self, session_id: str, result: Dict[str, Any], clarification_round: int = 1):
        """Handle clarification questions from the engine with looping support."""
        max_rounds = self.config.get("MAX_FOLLOW_UP_QUESTIONS", 5)

        self.console.print(
            f"\n[yellow]🤔 Clarification Round {clarification_round}/{max_rounds}[/yellow]")

        # Show confidence info if available
        confidence = result.get("confidence", "N/A")
        threshold = result.get("confidence_threshold",
                               self.config.get("CONFIDENCE_THRESHOLD", 75))
        self.console.print(
            f"[dim]Current confidence: {confidence}% (threshold: {threshold}%)[/dim]")

        questions = result.get("questions", [])

        if not questions:
            self.console.print(
                "[yellow]No clarification questions generated. Proceeding with current understanding.[/yellow]")
            # Force proceed even with low confidence
            return await self._force_proceed_research(session_id)

        self.console.print(
            f"[yellow]I need some clarification to provide better results ({len(questions)} questions)...[/yellow]")

        user_responses = {}

        for i, question_data in enumerate(questions, 1):
            question = question_data.get("question", "")
            purpose = question_data.get("purpose", "")
            examples = question_data.get("examples", [])
            allow_unknown = question_data.get("allow_unknown", True)

            self.console.print(
                f"\n[bold]Question {i}/{len(questions)}:[/bold] {question}")
            if purpose:
                self.console.print(f"[dim]Purpose: {purpose}[/dim]")
            if examples:
                self.console.print(
                    f"[dim]Examples: {', '.join(str(e) for e in examples)}[/dim]")

            if allow_unknown:
                self.console.print(
                    "[dim]You can answer 'unknown' or 'skip' if you're not sure[/dim]")

            answer = Prompt.ask(f"[bold]Your answer[/bold]")
            user_responses[question] = answer

        # Continue research with responses
        self.console.print("\n[blue]🔄 Processing your responses...[/blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(
                "Analyzing with new context...", total=None)

            try:
                result = await self.engine.conduct_research(session_id, user_responses)
                progress.stop()

                if result["status"] == "completed":
                    self.console.print(
                        "[green]✅ Sufficient understanding achieved![/green]")
                    await self._show_research_results(result)

                elif result["status"] == "needs_clarification":
                    # Check if we've hit the max rounds
                    if clarification_round >= max_rounds:
                        self.console.print(
                            f"\n[yellow]⚠️  Maximum clarification rounds ({max_rounds}) reached.[/yellow]")
                        self.console.print(
                            "[yellow]Proceeding with current understanding...[/yellow]")
                        # Force proceed with what we have
                        await self._force_proceed_research(session_id)
                    else:
                        # Recurse for another round of clarification
                        new_confidence = result.get("confidence", "N/A")
                        self.console.print(
                            f"\n[yellow]Still need more clarity (confidence: {new_confidence}%)[/yellow]")
                        await self._handle_clarification(session_id, result, clarification_round + 1)

                elif result["status"] == "error":
                    self.console.print(
                        f"[red]❌ Research failed: {result.get('error', 'Unknown error')}[/red]")
                    self.console.print(
                        "[yellow]Check the logs/odyssey.log file for more details.[/yellow]")
                else:
                    self.console.print(
                        f"[red]❌ Unexpected status: {result.get('status')}[/red]")

            except Exception as e:
                progress.stop()
                self.console.print(
                    f"[red]❌ Error during research: {str(e)}[/red]")
                self.console.print(
                    "[yellow]Check the logs/odyssey.log file for more details.[/yellow]")

    async def _force_proceed_research(self, session_id: str):
        """Force proceed with research even if confidence is below threshold."""
        self.console.print(
            "\n[blue]🚀 Forcing research to proceed with current understanding...[/blue]")

        # Load session and mark that we're forcing proceed
        session_data = await self.storage.load_session(session_id)
        if session_data:
            session_data["force_proceed"] = True
            session_data["status"] = "proceeding_with_low_confidence"
            await self.storage.save_session(session_id, session_data)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(
                "Conducting research with available context...", total=None)

            try:
                # Call the engine with a flag to skip confidence check
                result = await self.engine.conduct_research_forced(session_id)
                progress.stop()

                if result["status"] == "completed":
                    await self._show_research_results(result)
                else:
                    self.console.print(
                        f"[red]❌ Research failed: {result.get('error', 'Unknown error')}[/red]")
            except AttributeError:
                # If conduct_research_forced doesn't exist, just show what we have
                progress.stop()
                self.console.print(
                    "[yellow]Research could not be completed with current understanding.[/yellow]")
                self.console.print(
                    "[dim]Consider starting a new research session with more specific details.[/dim]")
            except Exception as e:
                progress.stop()
                self.console.print(f"[red]❌ Error: {str(e)}[/red]")

    async def _show_research_results(self, result: Dict[str, Any]):
        """Show research results to the user."""
        self.console.print(
            "\n[green]✅ Research completed successfully![/green]")

        report = result.get("report", {})
        confidence = result.get("confidence", {})
        session_data = result.get("session_data", {})

        # Show intent summary (including decision/success criteria when available)
        try:
            intent_stage = session_data.get("stages", {}).get(
                "intent_analysis", {}).get("result", {})
            intent_payload = intent_stage.get(
                "intent", intent_stage) if isinstance(intent_stage, dict) else {}
            if isinstance(intent_payload, dict):
                decision_criteria = intent_payload.get("decision_criteria", [])
                success_criteria = intent_payload.get("success_criteria", [])
                missing_information = intent_payload.get(
                    "missing_information", [])

                intent_summary = f"""
**Research Type:** {intent_payload.get('research_type', 'N/A')}
**Domain:** {intent_payload.get('domain', 'N/A')}
**Scope:** {intent_payload.get('scope', 'N/A')}

**Decision Criteria:** {', '.join(decision_criteria) if isinstance(decision_criteria, list) and decision_criteria else 'N/A'}
**Success Criteria:** {', '.join(success_criteria) if isinstance(success_criteria, list) and success_criteria else 'N/A'}

**Missing Info (if any):** {', '.join(missing_information) if isinstance(missing_information, list) and missing_information else 'None'}
                """
                self.console.print(
                    Panel(Markdown(intent_summary), title="Intent Summary", border_style="cyan"))
        except Exception:
            # Avoid breaking the UI if a session payload is unexpected
            pass

        # Show confidence summary
        if confidence:
            overall_conf = confidence.get("overall_confidence", 0)
            conf_level = confidence.get("confidence_level", "Unknown")

            confidence_panel = f"""
**Overall Confidence:** {overall_conf:.1f}% ({conf_level})

**Stage Breakdown:**
{self._format_confidence_breakdown(confidence.get("confidence_breakdown", {}))}
            """

            self.console.print(Panel(Markdown(confidence_panel),
                               title="Research Confidence", border_style="green"))

        # Show report summary
        if report:
            word_count = report.get("word_count", 0)
            file_path = report.get("file_path", "")

            summary_panel = f"""
**Report Generated:** {file_path}
**Word Count:** {word_count:,} words
**Sections:** {report.get('metadata', {}).get('sections_count', 0)} sections

The comprehensive research report has been saved and is ready for review.
            """

            self.console.print(Panel(Markdown(summary_panel),
                               title="Report Summary", border_style="blue"))

        # Ask about next steps directly (no automatic report display)
        next_action = Prompt.ask(
            "\n[bold]What would you like to do next?[/bold]",
            choices=["menu", "new", "view", "save"],
            default="menu"
        )

        if next_action == "new":
            await self._start_new_research()
        elif next_action == "view":
            await self._display_report(report.get("file_path"))
        elif next_action == "save":
            self._show_save_options(report)

    def _format_confidence_breakdown(self, breakdown: Dict[str, str]) -> str:
        """Format confidence breakdown for display."""
        if not breakdown:
            return "No breakdown available"

        formatted_lines = []
        for stage, confidence in breakdown.items():
            stage_name = stage.replace("_", " ").title()
            formatted_lines.append(f"- {stage_name}: {confidence}")

        return "\n".join(formatted_lines)

    async def _display_report(self, file_path: Optional[str]):
        """Display a research report."""
        if not file_path or not Path(file_path).exists():
            self.console.print("[red]❌ Report file not found[/red]")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Display report with pagination
            lines = content.split('\n')
            lines_per_page = 30

            for i in range(0, len(lines), lines_per_page):
                page_lines = lines[i:i + lines_per_page]
                page_content = '\n'.join(page_lines)

                self.console.print("\n" + "="*60)
                self.console.print(Markdown(page_content))
                self.console.print("="*60)

                if i + lines_per_page < len(lines):
                    if not Confirm.ask("\n[bold]Continue reading?[/bold]", default=True):
                        break

        except Exception as e:
            self.console.print(f"[red]❌ Error reading report: {str(e)}[/red]")

    def _show_save_options(self, report: Dict[str, Any]):
        """Show options for saving/exporting the report."""
        self.console.print("\n[blue]💾 Save/Export Options[/blue]")
        self.console.print("The report is already saved as markdown.")
        self.console.print(f"Location: {report.get('file_path')}")

        # Future: Add export to different formats (PDF, HTML, etc.)

    async def _continue_research(self):
        """Continue an existing research session."""
        self.console.print(
            "\n[bold blue]🔄 Continue Existing Research[/bold blue]")

        # List recent sessions
        sessions = await self.storage.list_sessions(limit=10)

        if not sessions:
            self.console.print(
                "[yellow]No existing research sessions found.[/yellow]")
            return

        # Create table of sessions
        table = Table(title="Recent Research Sessions")
        table.add_column("Session ID", style="cyan")
        table.add_column("Query", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="blue")

        for session in sessions:
            table.add_row(
                session["session_id"][:8] + "...",
                session["initial_query"][:50] + "..." if len(
                    session["initial_query"]) > 50 else session["initial_query"],
                session["status"],
                session["created_at"][:10]
            )

        self.console.print(table)

        # Get session selection
        session_id = Prompt.ask(
            "\n[bold]Enter full session ID to continue[/bold]")

        try:
            session_data = await self.storage.load_session(session_id)
            if not session_data:
                self.console.print("[red]❌ Session not found[/red]")
                return

            status = session_data.get("status")

            if status == "completed":
                self.console.print(
                    "[yellow]This research session is already completed.[/yellow]")
                if Confirm.ask("View the results?"):
                    # Show completed results
                    report_path = session_data.get(
                        "final_report", {}).get("file_path")
                    if report_path:
                        await self._display_report(report_path)

            elif status == "needs_clarification":
                self.console.print(
                    "[blue]This session needs clarification.[/blue]")
                questions = session_data.get("clarifying_questions", [])
                result = {"status": "needs_clarification",
                          "questions": questions}
                await self._handle_clarification(session_id, result)

            else:
                self.console.print(
                    f"[yellow]Session status: {status}[/yellow]")
                if Confirm.ask("Restart this research session?"):
                    result = await self.engine.conduct_research(session_id)
                    await self._show_research_results(result)

        except Exception as e:
            self.console.print(f"[red]❌ Error loading session: {str(e)}[/red]")

    async def _view_sessions(self):
        """View all research sessions."""
        self.console.print("\n[bold blue]📊 Research Sessions[/bold blue]")

        sessions = await self.storage.list_sessions()

        if not sessions:
            self.console.print("[yellow]No research sessions found.[/yellow]")
            return

        # Create detailed table
        table = Table(title=f"All Research Sessions ({len(sessions)} total)")
        table.add_column("Session ID", style="cyan")
        table.add_column("Query", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="blue")
        table.add_column("Size", style="magenta")

        for session in sessions:
            file_size = session.get("file_size", 0)
            size_str = f"{file_size // 1024}KB" if file_size > 1024 else f"{file_size}B"

            table.add_row(
                session["session_id"][:8] + "...",
                session["initial_query"][:40] + "..." if len(
                    session["initial_query"]) > 40 else session["initial_query"],
                session["status"],
                session["created_at"][:10],
                size_str
            )

        self.console.print(table)

        # Show storage stats
        stats = await self.storage.get_storage_stats()
        stats_panel = f"""
**Total Sessions:** {stats.get('total_sessions', 0)}
**Storage Used:** {stats.get('total_storage_size', 0) // 1024}KB
**Average Session Size:** {stats.get('average_session_size', 0) // 1024}KB
        """

        self.console.print(Panel(Markdown(stats_panel),
                           title="Storage Statistics", border_style="green"))

    async def _view_reports(self):
        """View generated reports."""
        self.console.print("\n[bold blue]📄 Generated Reports[/bold blue]")

        reports_path = Path(self.config.get(
            "REPORTS_OUTPUT_PATH", "./reports"))

        if not reports_path.exists():
            self.console.print("[yellow]Reports directory not found.[/yellow]")
            return

        # List report files
        report_files = list(reports_path.glob("*.md"))

        if not report_files:
            self.console.print("[yellow]No reports found.[/yellow]")
            return

        # Create table of reports
        table = Table(title=f"Generated Reports ({len(report_files)} total)")
        table.add_column("Filename", style="cyan")
        table.add_column("Size", style="green")
        table.add_column("Modified", style="blue")

        for report_file in sorted(report_files, key=lambda x: x.stat().st_mtime, reverse=True):
            size_kb = report_file.stat().st_size // 1024
            modified_time = Path(report_file).stat().st_mtime
            from datetime import datetime
            modified_str = datetime.fromtimestamp(
                modified_time).strftime("%Y-%m-%d %H:%M")

            table.add_row(
                report_file.name,
                f"{size_kb}KB",
                modified_str
            )

        self.console.print(table)

        # Ask if user wants to view a report
        if Confirm.ask("\n[bold]Would you like to view a report?[/bold]"):
            filename = Prompt.ask("[bold]Enter filename[/bold]")
            report_path = reports_path / filename

            if report_path.exists():
                await self._display_report(str(report_path))
            else:
                self.console.print("[red]❌ Report file not found[/red]")

    async def _show_settings(self):
        """Show current settings and configuration."""
        self.console.print(
            "\n[bold blue]⚙️ Settings & Configuration[/bold blue]")

        # Show current configuration
        config_panel = f"""
**API Configuration:**
- Gemini Model: {self.config.get('GEMINI_MODEL')}
- API Key: {'✅ Configured' if self.config.get('GEMINI_API_KEY') else '❌ Not Set'}

**Research Settings:**
- Confidence Threshold: {self.config.get('CONFIDENCE_THRESHOLD')}%
- Max Scraping Depth: {self.config.get('MAX_SCRAPING_DEPTH')} levels
- Max Search Results: {self.config.get('MAX_SEARCH_RESULTS')}
- Max Follow-up Questions: {self.config.get('MAX_FOLLOW_UP_QUESTIONS')}
- Max Remote Calls (Google Search): {self.config.get('MAX_REMOTE_CALLS')} (not configurable)

**Storage Paths:**
- Sessions: {self.config.get('SESSION_STORAGE_PATH')}
- Reports: {self.config.get('REPORTS_OUTPUT_PATH')}

**Report Settings:**
- Default Tone: {self.config.get('DEFAULT_REPORT_TONE')}
- Include Confidence Scores: {'Yes' if self.config.get('INCLUDE_CONFIDENCE_SCORES') else 'No'}
- Include Source Reliability: {'Yes' if self.config.get('INCLUDE_SOURCE_RELIABILITY') else 'No'}
        """

        self.console.print(Panel(Markdown(config_panel),
                           title="Current Configuration", border_style="blue"))

        # Show storage statistics
        stats = await self.storage.get_storage_stats()
        if "error" not in stats:
            stats_panel = f"""
**Storage Statistics:**
- Total Sessions: {stats.get('total_sessions', 0)}
- Storage Used: {stats.get('total_storage_size', 0) // 1024}KB
- Backup Count: {stats.get('backup_count', 0)}
- Backup Storage: {stats.get('backup_storage_size', 0) // 1024}KB
            """

            self.console.print(
                Panel(Markdown(stats_panel), title="Storage Statistics", border_style="green"))

    def _show_help(self):
        """Show help and documentation."""
        help_text = """
# 🔍 Odyssey Engine Help

## Getting Started
1. **Start New Research**: Begin a new research session with your question
2. **Follow-up Questions**: The engine may ask clarifying questions for better results
3. **Review Results**: Examine your comprehensive research report
4. **Save & Export**: Reports are automatically saved in markdown format

## Research Process
The engine follows a systematic approach:
1. **Intent Analysis**: Understanding what you really want to know
2. **Data Gathering**: Collecting information from multiple sources
3. **Analysis**: Synthesizing and analyzing the information
4. **Report Generation**: Creating a comprehensive report

## Tips for Better Results
- Be specific in your research questions
- Provide context when asked clarifying questions
- Review confidence scores to understand result reliability
- Use "Continue Research" to build on previous sessions

## Configuration
- Set GEMINI_API_KEY in your .env file
- Adjust confidence threshold and other settings as needed
- Reports are saved in the reports/ directory
- Sessions are stored in the sessions/ directory

## Support
For issues or questions:
- Check the README.md file
- Review error messages for guidance
- Ensure your API key is correctly configured
        """

        self.console.print(
            Panel(Markdown(help_text), title="Help & Documentation", border_style="yellow"))


@click.command()
@click.option('--query', '-q', help='Research query to start with')
@click.option('--session', '-s', help='Session ID to continue')
@click.option('--interactive/--no-interactive', default=True, help='Run in interactive mode')
def main(query: Optional[str], session: Optional[str], interactive: bool):
    """Odyssey Engine - Deep Research AI Command Line Interface."""
    cli = OdysseyCLI()

    if query and not interactive:
        # Non-interactive mode with direct query
        asyncio.run(cli._run_direct_query(query))
    elif session and not interactive:
        # Non-interactive mode continuing session
        asyncio.run(cli._run_continue_session(session))
    else:
        # Interactive mode (default)
        asyncio.run(cli.run())


if __name__ == "__main__":
    main()

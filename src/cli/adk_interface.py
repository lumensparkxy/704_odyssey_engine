"""
ADK-based CLI Interface for Odyssey Engine.

This module provides the CLI interface using Google ADK Runner for
executing the research pipeline.
"""

import os
import sys
import asyncio
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.live import Live

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import our root agent
from agents.odyssey import root_agent

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class OdysseyADKCLI:
    """ADK-powered CLI interface for Odyssey Engine."""

    APP_NAME = "odyssey_research_engine"

    def __init__(self):
        """Initialize the ADK CLI."""
        self.console = Console()
        self.config = self._load_config()

        # ADK services
        self.session_service = InMemorySessionService()
        self.runner: Optional[Runner] = None

        # User tracking
        self.user_id = f"user_{uuid.uuid4().hex[:8]}"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        return {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
            "REPORTS_OUTPUT_PATH": os.getenv("REPORTS_OUTPUT_PATH", "./reports"),
            "SESSION_STORAGE_PATH": os.getenv("SESSION_STORAGE_PATH", "./sessions"),
        }

    async def run(self):
        """Main CLI entry point."""
        try:
            self._show_welcome()
            await self._check_configuration()

            # Initialize ADK Runner
            self.runner = Runner(
                app_name=self.APP_NAME,
                agent=root_agent,
                session_service=self.session_service,
            )

            async with self.runner:
                await self._main_menu()

        except KeyboardInterrupt:
            self.console.print("\n[yellow]👋 Goodbye![/yellow]")
        except Exception as e:
            self.console.print(f"[red]❌ Error: {str(e)}[/red]")
            raise

    def _show_welcome(self):
        """Show welcome message."""
        welcome_text = """
# 🔍 Odyssey Engine - Deep Research AI

Welcome to your intelligent research assistant powered by **Google ADK**!

Odyssey Engine helps you conduct comprehensive research by:
- Understanding your research intent through conversation
- Gathering information from multiple sources in parallel
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
        self.console.print(
            f"[dim]Using ADK with agent: {root_agent.name}[/dim]")

    async def _main_menu(self):
        """Show main menu and handle user choices."""
        while True:
            self.console.print("\n" + "=" * 60)
            self.console.print(
                "[bold blue]🔍 Odyssey Engine - Main Menu[/bold blue]")
            self.console.print("=" * 60)

            options = [
                "1. Start New Research",
                "2. View Generated Reports",
                "3. Settings & Configuration",
                "4. Help & Documentation",
                "5. Exit"
            ]

            for option in options:
                self.console.print(f"  {option}")

            choice = Prompt.ask(
                "\n[bold]Select an option[/bold]",
                choices=["1", "2", "3", "4", "5"]
            )

            if choice == "1":
                await self._start_new_research()
            elif choice == "2":
                await self._view_reports()
            elif choice == "3":
                self._show_settings()
            elif choice == "4":
                self._show_help()
            elif choice == "5":
                self.console.print(
                    "[yellow]👋 Thank you for using Odyssey Engine![/yellow]")
                break

    async def _start_new_research(self):
        """Start a new research session using ADK Runner."""
        self.console.print(
            "\n[bold blue]🚀 Starting New Research Session[/bold blue]")

        # Get research query
        query = self._get_research_query()
        if not query.strip():
            self.console.print(
                "[red]❌ Please provide a research question.[/red]")
            return

        # Create ADK session
        session = await self.session_service.create_session(
            app_name=self.APP_NAME,
            user_id=self.user_id,
            state={"original_query": query},
        )

        self.console.print(f"[dim]Session ID: {session.id}[/dim]")

        # Create the user message
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        # Run the research pipeline
        self.console.print("\n[blue]🔄 Running research pipeline...[/blue]")

        events_collected = []
        final_response = None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("Processing...", total=None)

            try:
                async for event in self.runner.run_async(
                    user_id=self.user_id,
                    session_id=session.id,
                    new_message=user_message,
                ):
                    events_collected.append(event)

                    # Update progress based on event
                    if hasattr(event, 'author') and event.author:
                        agent_name = event.author
                        if "Intent" in agent_name:
                            progress.update(
                                task, description="📋 Analyzing research intent...")
                        elif "DataGathering" in agent_name or "Parallel" in agent_name:
                            progress.update(
                                task, description="🔍 Gathering data from sources...")
                        elif "Analysis" in agent_name:
                            progress.update(
                                task, description="🧠 Analyzing findings...")
                        elif "Report" in agent_name:
                            progress.update(
                                task, description="📝 Generating report...")

                    # Capture final response
                    if hasattr(event, 'content') and event.content:
                        final_response = event

            except Exception as e:
                progress.stop()
                self.console.print(
                    f"[red]❌ Error during research: {str(e)}[/red]")
                return

        # Show results
        await self._show_research_results(session, events_collected, final_response)

    def _get_research_query(self) -> str:
        """Get the user's research query."""
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
                return ""

        # multiline
        return self._read_multiline_input(
            title="Paste your multi-line research prompt",
            terminator="END",
        )

    def _read_multiline_input(self, title: str, terminator: str = "END") -> str:
        """Read a multi-line block from stdin."""
        instructions = (
            f"{title}\n\n"
            f"Paste your text. When finished, type [bold]{terminator}[/bold] on its own line.\n"
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

        return "\n".join(lines).strip("\n")

    async def _show_research_results(self, session, events: List, final_response):
        """Show research results to the user."""
        self.console.print("\n[green]✅ Research pipeline completed![/green]")

        # Extract state from session
        updated_session = await self.session_service.get_session(
            app_name=self.APP_NAME,
            user_id=self.user_id,
            session_id=session.id,
        )

        state = updated_session.state if updated_session else {}

        # Show summary panel
        summary_parts = []

        if state.get("intent_result"):
            intent = state.get("intent_result", {})
            if isinstance(intent, dict):
                summary_parts.append(
                    f"**Research Type:** {intent.get('research_type', 'N/A')}")
                summary_parts.append(
                    f"**Domain:** {intent.get('domain', 'N/A')}")

        if state.get("report_metadata"):
            metadata = state.get("report_metadata", {})
            if isinstance(metadata, dict):
                file_path = metadata.get("file_path", "")
                if file_path:
                    summary_parts.append(f"\n**Report saved:** `{file_path}`")

        if summary_parts:
            self.console.print(Panel(
                Markdown("\n".join(summary_parts)),
                title="Research Summary",
                border_style="green"
            ))

        # Show final response if available
        if final_response and hasattr(final_response, 'content') and final_response.content:
            content = final_response.content
            if hasattr(content, 'parts') and content.parts:
                response_text = ""
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text += part.text

                if response_text:
                    # Truncate if too long for display
                    if len(response_text) > 2000:
                        display_text = response_text[:2000] + \
                            "\n\n...[truncated]"
                    else:
                        display_text = response_text

                    self.console.print(Panel(
                        Markdown(display_text),
                        title="Research Output",
                        border_style="blue"
                    ))

        # Ask about next steps
        self.console.print("\n[bold]Pipeline Stages Completed:[/bold]")
        self.console.print(f"  • Events processed: {len(events)}")

        # Check for report
        report_path = None
        if state.get("report_metadata"):
            metadata = state["report_metadata"]
            # Handle both dict and string formats
            if isinstance(metadata, dict):
                report_path = metadata.get("file_path")
            elif isinstance(metadata, str):
                # Try to extract path from string - look for the path pattern
                import re
                path_match = re.search(r'/[^\s\n]+\.md', metadata)
                if path_match:
                    report_path = path_match.group(0)

        if report_path and Path(report_path).exists():
            if Confirm.ask("\n[bold]Would you like to view the generated report?[/bold]"):
                await self._display_report(report_path)

    async def _display_report(self, file_path: str):
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

                self.console.print("\n" + "=" * 60)
                self.console.print(Markdown(page_content))
                self.console.print("=" * 60)

                if i + lines_per_page < len(lines):
                    if not Confirm.ask("\n[bold]Continue reading?[/bold]", default=True):
                        break

        except Exception as e:
            self.console.print(f"[red]❌ Error reading report: {str(e)}[/red]")

    async def _view_reports(self):
        """View generated reports."""
        self.console.print("\n[bold blue]📄 Generated Reports[/bold blue]")

        reports_path = Path(self.config.get(
            "REPORTS_OUTPUT_PATH", "./reports"))

        if not reports_path.exists():
            self.console.print("[yellow]Reports directory not found.[/yellow]")
            return

        report_files = list(reports_path.glob("*.md"))

        if not report_files:
            self.console.print("[yellow]No reports found.[/yellow]")
            return

        # Create table of reports
        table = Table(title=f"Generated Reports ({len(report_files)} total)")
        table.add_column("Filename", style="cyan")
        table.add_column("Size", style="green")
        table.add_column("Modified", style="blue")

        from datetime import datetime
        for report_file in sorted(report_files, key=lambda x: x.stat().st_mtime, reverse=True):
            size_kb = report_file.stat().st_size // 1024
            modified_time = report_file.stat().st_mtime
            modified_str = datetime.fromtimestamp(
                modified_time).strftime("%Y-%m-%d %H:%M")

            table.add_row(
                report_file.name,
                f"{size_kb}KB",
                modified_str
            )

        self.console.print(table)

        if Confirm.ask("\n[bold]Would you like to view a report?[/bold]"):
            filename = Prompt.ask("[bold]Enter filename[/bold]")
            report_path = reports_path / filename

            if report_path.exists():
                await self._display_report(str(report_path))
            else:
                self.console.print("[red]❌ Report file not found[/red]")

    def _show_settings(self):
        """Show current settings and configuration."""
        self.console.print(
            "\n[bold blue]⚙️ Settings & Configuration[/bold blue]")

        config_panel = f"""
**API Configuration:**
- Gemini Model: {self.config.get('GEMINI_MODEL')}
- API Key: {'✅ Configured' if self.config.get('GEMINI_API_KEY') else '❌ Not Set'}

**ADK Configuration:**
- App Name: {self.APP_NAME}
- Root Agent: {root_agent.name}
- Sub-agents: {len(root_agent.sub_agents)}

**Storage Paths:**
- Reports: {self.config.get('REPORTS_OUTPUT_PATH')}

**Pipeline Stages:**
1. {root_agent.sub_agents[0].name if len(root_agent.sub_agents) > 0 else 'N/A'}
2. {root_agent.sub_agents[1].name if len(root_agent.sub_agents) > 1 else 'N/A'}
3. {root_agent.sub_agents[2].name if len(root_agent.sub_agents) > 2 else 'N/A'}
4. {root_agent.sub_agents[3].name if len(root_agent.sub_agents) > 3 else 'N/A'}
        """

        self.console.print(Panel(Markdown(config_panel),
                           title="Current Configuration", border_style="blue"))

    def _show_help(self):
        """Show help and documentation."""
        help_text = """
# 🔍 Odyssey Engine Help (ADK Version)

## Getting Started
1. **Start New Research**: Begin a new research session with your question
2. **ADK Pipeline**: The engine runs through 4 stages automatically
3. **Review Results**: Examine your comprehensive research report

## Research Pipeline (ADK)
The engine uses Google ADK with the following stages:

1. **Intent Analysis** (IntentClarificationLoop)
   - Understands your research intent
   - Asks clarifying questions if needed
   
2. **Data Gathering** (DataGatheringPipeline)
   - Internal Knowledge Agent
   - Google Search Agent  
   - Web Scraper Agent
   - Consolidator Agent
   
3. **Analysis** (AnalysisAgent)
   - Theme identification
   - Conflict detection
   - Synthesis generation
   
4. **Report Generation** (ReportGenerationPipeline)
   - Generates markdown report
   - Saves to reports/ directory

## Tips for Better Results
- Be specific in your research questions
- Provide context when possible
- Review the generated report for insights

## Configuration
- Set GEMINI_API_KEY in your .env file
- Reports are saved in the reports/ directory
        """

        self.console.print(Panel(Markdown(help_text),
                           title="Help & Documentation", border_style="yellow"))


async def run_adk_cli():
    """Entry point for ADK CLI."""
    cli = OdysseyADKCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(run_adk_cli())

"""
ADK-based CLI Interface for Odyssey Engine.

This module provides the CLI interface using Google ADK Runner for
executing the research pipeline with human-in-the-loop intent clarification.
"""

import json
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

# Import progress display components
from .progress_display import (
    ProgressTracker,
    LiveProgressPanel,
    extract_tool_info_from_event,
    get_agent_from_event,
)
from .messages import get_phase_header, get_tool_discovery_message

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import our agents - both full pipeline and individual phases
from agents.odyssey import (
    root_agent,
    intent_clarification_loop,
    data_gathering_pipeline,
    analysis_agent,
    report_generation_pipeline,
)
from agents.odyssey.tools import create_audit_logger, SessionAuditLogger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================================
# TIMEOUT CONFIGURATION
# ============================================================================
# These can be configured via environment variables

DATA_GATHERING_TIMEOUT = int(
    os.getenv("DATA_GATHERING_TIMEOUT", "300"))  # 5 minutes
ANALYSIS_TIMEOUT = int(os.getenv("ANALYSIS_TIMEOUT", "180"))  # 3 minutes
REPORT_GENERATION_TIMEOUT = int(
    os.getenv("REPORT_GENERATION_TIMEOUT", "180"))  # 3 minutes
INTENT_PHASE_TIMEOUT = int(
    os.getenv("INTENT_PHASE_TIMEOUT", "120"))  # 2 minutes per round


class OdysseyADKCLI:
    """ADK-powered CLI interface for Odyssey Engine with human-in-the-loop support."""

    APP_NAME = "odyssey_research_engine"

    def __init__(self):
        """Initialize the ADK CLI."""
        self.console = Console()
        self.config = self._load_config()

        # ADK services
        self.session_service = InMemorySessionService()

        # Runners for each phase (initialized in run())
        self.intent_runner: Optional[Runner] = None
        self.data_runner: Optional[Runner] = None
        self.analysis_runner: Optional[Runner] = None
        self.report_runner: Optional[Runner] = None
        self.runner: Optional[Runner] = None  # Legacy full pipeline runner

        # User tracking
        self.user_id = f"user_{uuid.uuid4().hex[:8]}"

        # Audit logger (initialized per session)
        self.audit_logger: Optional[SessionAuditLogger] = None

        # Phase timeout tracking
        self.phase_timeouts = {
            "data_gathering": DATA_GATHERING_TIMEOUT,
            "analysis": ANALYSIS_TIMEOUT,
            "report_generation": REPORT_GENERATION_TIMEOUT,
            "intent": INTENT_PHASE_TIMEOUT,
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        return {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
            "REPORTS_OUTPUT_PATH": os.getenv("REPORTS_OUTPUT_PATH", "./reports"),
            "SESSION_STORAGE_PATH": os.getenv("SESSION_STORAGE_PATH", "./sessions"),
            "AUDIT_LOG_PATH": os.getenv("AUDIT_LOG_PATH", "./logs/sessions"),
        }

    async def run(self):
        """Main CLI entry point."""
        try:
            self._show_welcome()
            await self._check_configuration()

            # Initialize phase-specific runners for human-in-the-loop execution
            self.intent_runner = Runner(
                app_name=f"{self.APP_NAME}_intent",
                agent=intent_clarification_loop,
                session_service=self.session_service,
            )
            self.data_runner = Runner(
                app_name=f"{self.APP_NAME}_data",
                agent=data_gathering_pipeline,
                session_service=self.session_service,
            )
            self.analysis_runner = Runner(
                app_name=f"{self.APP_NAME}_analysis",
                agent=analysis_agent,
                session_service=self.session_service,
            )
            self.report_runner = Runner(
                app_name=f"{self.APP_NAME}_report",
                agent=report_generation_pipeline,
                session_service=self.session_service,
            )
            # Legacy full pipeline runner
            self.runner = Runner(
                app_name=self.APP_NAME,
                agent=root_agent,
                session_service=self.session_service,
            )

            async with self.intent_runner, self.data_runner, self.analysis_runner, self.report_runner, self.runner:
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
- Understanding your research intent through **interactive clarification**
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
        """Start a new research session using ADK Runner with human-in-the-loop."""
        self.console.print(
            "\n[bold blue]🚀 Starting New Research Session[/bold blue]")

        # Get research query
        query = self._get_research_query()
        if not query.strip():
            self.console.print(
                "[red]❌ Please provide a research question.[/red]")
            return

        # Create main ADK session (for legacy runner)
        session = await self.session_service.create_session(
            app_name=self.APP_NAME,
            user_id=self.user_id,
            state={"original_query": query},
        )

        # Create intent phase session (primary session for phase-by-phase execution)
        await self.session_service.create_session(
            app_name=f"{self.APP_NAME}_intent",
            user_id=self.user_id,
            state={"original_query": query},
            session_id=session.id,  # Use same session ID for consistency
        )

        # Initialize audit logger
        self.audit_logger = create_audit_logger(session.id, self.user_id)
        self.audit_logger.log_original_query(query)

        self.console.print(f"[dim]Session ID: {session.id}[/dim]")

        # Create the user message
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        # Run the research pipeline with human-in-the-loop
        await self._run_pipeline_with_interaction(session, user_message)

    async def _run_pipeline_with_interaction(self, session, user_message):
        """
        Run the pipeline with human-in-the-loop interaction at each phase.

        Pipeline Phases:
        1. Intent Analysis - Clarify user's research intent (max 5 rounds)
        2. Data Gathering - Collect information from multiple sources
        3. Analysis - Analyze and synthesize findings
        4. Report Generation - Generate final research report

        Human checkpoint after each phase allows user to:
        - Review results
        - Provide feedback
        - Continue, modify, or cancel
        """
        self.console.print("\n[blue]🔄 Starting Research Pipeline...[/blue]")

        events_collected = []

        # ============ PHASE 1: Intent Analysis ============
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold cyan]📋 PHASE 1: Intent Analysis[/bold cyan]")
        self.console.print("=" * 60)

        intent_result = await self._run_intent_phase(session, user_message, events_collected)
        if intent_result == "cancel":
            return

        # ============ PHASE 2: Data Gathering ============
        proceed = await self._phase_checkpoint(
            session,
            phase_name="Data Gathering",
            phase_number=2,
            description="Collect information from internal knowledge, Google Search, and web sources",
            previous_phase_summary=self._get_intent_summary(session)
        )

        if not proceed:
            self.console.print("[yellow]Research cancelled by user.[/yellow]")
            return

        self.console.print("\n" + "=" * 60)
        self.console.print("[bold cyan]🔍 PHASE 2: Data Gathering[/bold cyan]")
        self.console.print("=" * 60)

        await self._run_data_gathering_phase(session, events_collected)

        # ============ PHASE 3: Analysis ============
        proceed = await self._phase_checkpoint(
            session,
            phase_name="Analysis",
            phase_number=3,
            description="Analyze gathered data, identify themes, conflicts, and synthesize findings",
            previous_phase_summary=await self._get_data_gathering_summary(session)
        )

        if not proceed:
            self.console.print("[yellow]Research cancelled by user.[/yellow]")
            return

        self.console.print("\n" + "=" * 60)
        self.console.print("[bold cyan]🧠 PHASE 3: Analysis[/bold cyan]")
        self.console.print("=" * 60)

        await self._run_analysis_phase(session, events_collected)

        # ============ PHASE 4: Report Generation ============
        proceed = await self._phase_checkpoint(
            session,
            phase_name="Report Generation",
            phase_number=4,
            description="Generate comprehensive research report in markdown format",
            previous_phase_summary=await self._get_analysis_summary(session)
        )

        if not proceed:
            self.console.print("[yellow]Research cancelled by user.[/yellow]")
            return

        # Collect report customization preferences before generation
        output_preferences = await self._collect_report_preferences(session)
        # Serialize to JSON string for ADK state injection
        await self._update_session_state(session, {
            "output_preferences": json.dumps(output_preferences, indent=2)
        })

        self.console.print("\n" + "=" * 60)
        self.console.print(
            "[bold cyan]📝 PHASE 4: Report Generation[/bold cyan]")
        self.console.print("=" * 60)

        final_response = await self._run_report_phase(session, events_collected)

        # Show final results
        await self._show_research_results(session, events_collected, final_response)

    async def _run_intent_phase(self, session, user_message, events_collected: List) -> str:
        """
        Run the intent clarification phase with max 5 rounds.

        Returns:
            "complete" - Intent phase completed successfully
            "cancel" - User cancelled
        """
        clarification_round = 0
        max_clarification_rounds = 5
        current_message = user_message  # Track current message for each round

        while clarification_round < max_clarification_rounds:
            clarification_round += 1

            self.console.print(
                f"\n[dim]Analyzing intent (round {clarification_round}/{max_clarification_rounds})...[/dim]")

            # Run intent analysis using phase-specific runner
            # ADK requires a new_message for each run_async call
            async for event in self.intent_runner.run_async(
                user_id=self.user_id,
                session_id=session.id,
                new_message=current_message,
            ):
                events_collected.append(event)
                self._update_progress_display(event)

            # Check session state (use intent runner app name)
            updated_session = await self.session_service.get_session(
                app_name=f"{self.APP_NAME}_intent",
                user_id=self.user_id,
                session_id=session.id,
            )
            state = updated_session.state if updated_session else {}

            # Check if user already confirmed
            if state.get("user_confirmed_proceed") or state.get("intent_phase_complete"):
                return "complete"

            # Check if we need user input
            if state.get("awaiting_user_input", False):
                action, user_response = await self._handle_human_input(session, state, clarification_round, max_clarification_rounds)

                if action == "cancel":
                    return "cancel"
                elif action == "proceed":
                    return "complete"
                elif action == "clarify":
                    # Build enriched query in CLI (before next loop iteration)
                    # This ensures IntentAnalyzer gets the full context
                    original_query = state.get("original_query", "")
                    clarification_questions = state.get(
                        "clarification_questions", [])

                    # Build cumulative context with all clarifications
                    enriched_query = self._build_enriched_query(
                        original_query,
                        user_response,
                        clarification_questions,
                        clarification_round
                    )

                    # Create a new message with the enriched query for the next round
                    current_message = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=enriched_query)]
                    )

                    # Update session state with enriched query for future reference
                    await self._update_session_state(session, {
                        "awaiting_user_input": False,
                        "response_processed": False,
                        "needs_reanalysis": False,
                        "original_query": enriched_query,  # Update for next round
                        "enriched_query": enriched_query,
                    })
                    continue
            else:
                # No user input needed, phase complete
                return "complete"

        # Max rounds reached
        self.console.print(
            f"[yellow]⚠️ Maximum clarification rounds ({max_clarification_rounds}) reached.[/yellow]")
        return "complete"

    async def _run_data_gathering_phase(self, session, events_collected: List):
        """Run the data gathering phase using phase-specific runner with live progress and timeout protection."""
        # Copy session state to data runner session
        await self._sync_session_to_phase(session, f"{self.APP_NAME}_data")

        # ADK requires a message to trigger the agent
        trigger_message = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="Proceed with data gathering based on the intent analysis.")]
        )

        # Initialize progress tracker for data gathering phase
        timeout = self.phase_timeouts["data_gathering"]
        tracker = ProgressTracker("DataGathering", timeout_seconds=timeout)
        panel = LiveProgressPanel(tracker, self.console)

        timed_out = False
        start_time = asyncio.get_event_loop().time()

        try:
            with Live(panel.render(), console=self.console, refresh_per_second=4) as live:
                async def run_with_progress():
                    nonlocal timed_out
                    async for event in self.data_runner.run_async(
                        user_id=self.user_id,
                        session_id=session.id,
                        new_message=trigger_message,
                    ):
                        events_collected.append(event)

                        # Update sub-agent if changed
                        agent_name = get_agent_from_event(event)
                        if agent_name:
                            tracker.set_sub_agent(agent_name)

                        # Extract and display tool activity (search queries, URLs)
                        tool_info = extract_tool_info_from_event(event)
                        if tool_info:
                            tracker.add_tool_activity(
                                tool_info['tool_name'],
                                tool_info['description']
                            )

                        # Update elapsed time in tracker
                        elapsed = asyncio.get_event_loop().time() - start_time
                        tracker.elapsed_seconds = elapsed

                        # Update the live display
                        live.update(panel.render())

                # Run with timeout
                try:
                    await asyncio.wait_for(run_with_progress(), timeout=timeout)
                except asyncio.TimeoutError:
                    timed_out = True
                    elapsed = asyncio.get_event_loop().time() - start_time
                    self.console.print(
                        f"\n[yellow]⚠️ Data gathering timed out after {elapsed:.0f}s (limit: {timeout}s)[/yellow]")
                    self.console.print(
                        "[yellow]Continuing with partial data...[/yellow]")

                    # Store timeout info in session state for consolidator
                    await self._update_session_state(session, {
                        "data_gathering_timeout": True,
                        "data_gathering_elapsed": elapsed,
                        "data_gathering_status": "partial_timeout"
                    })

        except Exception as e:
            self.console.print(
                f"\n[red]⚠️ Data gathering error: {str(e)}[/red]")
            self.console.print(
                "[yellow]Attempting to continue with available data...[/yellow]")

            # Store error info
            await self._update_session_state(session, {
                "data_gathering_error": str(e),
                "data_gathering_status": "error"
            })

        # Sync state back
        await self._sync_session_from_phase(session, f"{self.APP_NAME}_data")

        # Ensure consolidated_data exists even if data gathering failed/timed out
        await self._ensure_consolidated_data_exists(session, timed_out)

        if timed_out:
            self.console.print(
                "[dim]Pipeline will continue with whatever data was gathered.[/dim]")

    async def _run_analysis_phase(self, session, events_collected: List):
        """Run the analysis phase using phase-specific runner with live progress and timeout protection."""
        # Copy session state to analysis runner session
        await self._sync_session_to_phase(session, f"{self.APP_NAME}_analysis")

        # ADK requires a message to trigger the agent
        trigger_message = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="Proceed with analysis of the gathered data.")]
        )

        # Initialize progress tracker for analysis phase
        timeout = self.phase_timeouts["analysis"]
        tracker = ProgressTracker("Analysis", timeout_seconds=timeout)
        panel = LiveProgressPanel(tracker, self.console)

        start_time = asyncio.get_event_loop().time()

        try:
            with Live(panel.render(), console=self.console, refresh_per_second=4) as live:
                async def run_with_progress():
                    async for event in self.analysis_runner.run_async(
                        user_id=self.user_id,
                        session_id=session.id,
                        new_message=trigger_message,
                    ):
                        events_collected.append(event)

                        # Update sub-agent if changed
                        agent_name = get_agent_from_event(event)
                        if agent_name:
                            tracker.set_sub_agent(agent_name)

                        # Update elapsed time
                        elapsed = asyncio.get_event_loop().time() - start_time
                        tracker.elapsed_seconds = elapsed

                        # Update the live display
                        live.update(panel.render())

                try:
                    await asyncio.wait_for(run_with_progress(), timeout=timeout)
                except asyncio.TimeoutError:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    self.console.print(
                        f"\n[yellow]⚠️ Analysis timed out after {elapsed:.0f}s (limit: {timeout}s)[/yellow]")
                    self.console.print(
                        "[yellow]Continuing with partial analysis...[/yellow]")

                    await self._update_session_state(session, {
                        "analysis_timeout": True,
                        "analysis_status": "partial_timeout"
                    })

        except Exception as e:
            self.console.print(f"\n[red]⚠️ Analysis error: {str(e)}[/red]")
            await self._update_session_state(session, {
                "analysis_error": str(e),
                "analysis_status": "error"
            })
        # Sync state back
        await self._sync_session_from_phase(session, f"{self.APP_NAME}_analysis")

    async def _run_report_phase(self, session, events_collected: List):
        """Run the report generation phase using phase-specific runner with live progress and timeout protection."""
        # Copy session state to report runner session
        await self._sync_session_to_phase(session, f"{self.APP_NAME}_report")

        # ADK requires a message to trigger the agent
        trigger_message = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="Generate the final research report based on the analysis.")]
        )

        # Initialize progress tracker for report generation phase
        timeout = self.phase_timeouts["report_generation"]
        tracker = ProgressTracker("ReportGeneration", timeout_seconds=timeout)
        panel = LiveProgressPanel(tracker, self.console)

        start_time = asyncio.get_event_loop().time()

        final_response = None
        try:
            with Live(panel.render(), console=self.console, refresh_per_second=4) as live:
                async def run_with_progress():
                    nonlocal final_response
                    async for event in self.report_runner.run_async(
                        user_id=self.user_id,
                        session_id=session.id,
                        new_message=trigger_message,
                    ):
                        events_collected.append(event)

                        # Update sub-agent if changed
                        agent_name = get_agent_from_event(event)
                        if agent_name:
                            tracker.set_sub_agent(agent_name)

                        # Check for file save tool activity
                        tool_info = extract_tool_info_from_event(event)
                        if tool_info:
                            tracker.add_tool_activity(
                                tool_info['tool_name'],
                                tool_info['description']
                            )

                        # Update elapsed time
                        elapsed = asyncio.get_event_loop().time() - start_time
                        tracker.elapsed_seconds = elapsed

                        # Update the live display
                        live.update(panel.render())

                        if hasattr(event, 'content') and event.content:
                            final_response = event

                try:
                    await asyncio.wait_for(run_with_progress(), timeout=timeout)
                except asyncio.TimeoutError:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    self.console.print(
                        f"\n[yellow]⚠️ Report generation timed out after {elapsed:.0f}s (limit: {timeout}s)[/yellow]")
                    self.console.print(
                        "[yellow]Report may be incomplete.[/yellow]")

                    await self._update_session_state(session, {
                        "report_timeout": True,
                        "report_status": "partial_timeout"
                    })

        except Exception as e:
            self.console.print(
                f"\n[red]⚠️ Report generation error: {str(e)}[/red]")
            await self._update_session_state(session, {
                "report_error": str(e),
                "report_status": "error"
            })
        # Sync state back
        await self._sync_session_from_phase(session, f"{self.APP_NAME}_report")

        return final_response

    async def _phase_checkpoint(
        self,
        session,
        phase_name: str,
        phase_number: int,
        description: str,
        previous_phase_summary: str
    ) -> bool:
        """
        Display checkpoint between phases and get user confirmation.

        Returns:
            True to proceed, False to cancel
        """
        self.console.print("\n" + "-" * 60)
        self.console.print(
            f"[bold green]✅ Phase {phase_number - 1} Complete![/bold green]")
        self.console.print("-" * 60)

        if previous_phase_summary:
            self.console.print(Panel(
                Markdown(previous_phase_summary),
                title=f"Phase {phase_number - 1} Summary",
                border_style="green"
            ))

        self.console.print(
            f"\n[bold]Next: Phase {phase_number} - {phase_name}[/bold]")
        self.console.print(f"[dim]{description}[/dim]")

        choice = Prompt.ask(
            "\n[bold]Continue to next phase?[/bold]",
            choices=["yes", "no", "y", "n"],
            default="yes"
        )

        return choice.lower() in ["yes", "y"]

    def _get_intent_summary(self, session) -> str:
        """Get a summary of the intent analysis phase."""
        # This is synchronous, we'll get state from the session service later
        return """**Research Intent Analyzed**

The system has analyzed your research query and identified:
- Research type and scope
- Key entities to investigate
- Research questions to answer
- Success criteria for the research

Ready to gather data from multiple sources."""

    def _build_enriched_query(
        self,
        original_query: str,
        user_response: str,
        clarification_questions: List[str],
        round_number: int
    ) -> str:
        """
        Build an enriched query that includes the user's clarification.

        This is called by the CLI before the next intent analysis round,
        ensuring IntentAnalyzer receives the full context.

        Args:
            original_query: The current query (may already include previous clarifications)
            user_response: The user's latest clarification response
            clarification_questions: The questions that were asked
            round_number: Current clarification round number

        Returns:
            Enriched query string with all context
        """
        enriched_parts = []

        # Start with the original/current query
        enriched_parts.append(f"Research Request: {original_query}")
        enriched_parts.append("")

        # Add the clarification context
        enriched_parts.append(
            f"=== User Clarification (Round {round_number}) ===")

        if clarification_questions:
            enriched_parts.append("Questions asked:")
            for i, q in enumerate(clarification_questions, 1):
                enriched_parts.append(f"  {i}. {q}")
            enriched_parts.append("")

        enriched_parts.append(f"User's response: {user_response}")
        enriched_parts.append("")
        enriched_parts.append(
            "Please re-analyze the research intent with this additional context.")

        return "\n".join(enriched_parts)

    async def _get_data_gathering_summary(self, session) -> str:
        """Get a summary of the data gathering phase."""
        # Try data phase session first, then intent session
        updated_session = await self.session_service.get_session(
            app_name=f"{self.APP_NAME}_data",
            user_id=self.user_id,
            session_id=session.id,
        )
        if not updated_session:
            updated_session = await self.session_service.get_session(
                app_name=f"{self.APP_NAME}_intent",
                user_id=self.user_id,
                session_id=session.id,
            )
        state = updated_session.state if updated_session else {}

        consolidated = state.get("consolidated_information", "")
        if consolidated and len(consolidated) > 500:
            consolidated = consolidated[:500] + "..."

        summary = """**Data Collection Complete**

Information gathered from:
- 🧠 Internal Knowledge Base
- 🌐 Google Search Results
- 📄 Web Page Content

"""
        if consolidated:
            summary += f"**Preview:**\n{consolidated}"
        else:
            summary += "Data has been consolidated and is ready for analysis."

        return summary

    async def _get_analysis_summary(self, session) -> str:
        """Get a summary of the analysis phase."""
        # Try analysis phase session first, then data, then intent
        updated_session = await self.session_service.get_session(
            app_name=f"{self.APP_NAME}_analysis",
            user_id=self.user_id,
            session_id=session.id,
        )
        if not updated_session:
            updated_session = await self.session_service.get_session(
                app_name=f"{self.APP_NAME}_data",
                user_id=self.user_id,
                session_id=session.id,
            )
        if not updated_session:
            updated_session = await self.session_service.get_session(
                app_name=f"{self.APP_NAME}_intent",
                user_id=self.user_id,
                session_id=session.id,
            )
        state = updated_session.state if updated_session else {}

        analysis = state.get("analysis_result", "")
        if analysis and len(analysis) > 500:
            analysis = analysis[:500] + "..."

        summary = """**Analysis Complete**

The analysis phase has:
- Identified key themes and patterns
- Detected any conflicts or contradictions
- Synthesized findings into coherent insights

"""
        if analysis:
            summary += f"**Preview:**\n{analysis}"
        else:
            summary += "Analysis is complete and ready for report generation."

        return summary

    async def _collect_report_preferences(self, session) -> Dict[str, Any]:
        """
        Collect report customization preferences from the user before generation.
        
        Returns a dictionary with output preferences that will be passed to the
        report generation agent.
        """
        self.console.print("\n" + "-" * 60)
        self.console.print("[bold magenta]📝 Report Customization[/bold magenta]")
        self.console.print("-" * 60)
        
        # Check if user already has preferences from intent analysis
        intent_session = await self.session_service.get_session(
            app_name=f"{self.APP_NAME}_intent",
            user_id=self.user_id,
            session_id=session.id,
        )
        state = intent_session.state if intent_session else {}
        parsed_intent = state.get("parsed_intent", {})
        existing_prefs = parsed_intent.get("output_preferences", {}) if isinstance(parsed_intent, dict) else {}
        
        self.console.print(
            "\n[dim]Customize how your research report will be generated.[/dim]"
        )
        
        # Ask if user wants to customize or use defaults
        customize = Prompt.ask(
            "\n[bold]Would you like to customize the report format?[/bold]",
            choices=["yes", "no", "y", "n"],
            default="no"
        )
        
        if customize.lower() in ["no", "n"]:
            # Use defaults with any existing preferences
            default_prefs = {
                "report_length": existing_prefs.get("report_length", "standard"),
                "audience": existing_prefs.get("audience", "professional"),
                "format_style": existing_prefs.get("format_style", "executive"),
                "include_visuals": existing_prefs.get("include_visuals", True),
                "focus_areas": existing_prefs.get("focus_areas", []),
            }
            self.console.print(
                f"[green]✅ Using default format: {default_prefs['report_length']} report, "
                f"{default_prefs['audience']} audience, {default_prefs['format_style']} style[/green]"
            )
            return default_prefs
        
        # Collect preferences interactively
        preferences = {}
        
        # 1. Report Length
        self.console.print("\n[bold]Report Length:[/bold]")
        self.console.print("  • [cyan]brief[/cyan] - 1-2 pages, executive summary focus")
        self.console.print("  • [cyan]standard[/cyan] - 3-5 pages, balanced detail")
        self.console.print("  • [cyan]comprehensive[/cyan] - 6+ pages, full analysis")
        
        preferences["report_length"] = Prompt.ask(
            "Select length",
            choices=["brief", "standard", "comprehensive"],
            default=existing_prefs.get("report_length", "standard")
        )
        
        # 2. Target Audience
        self.console.print("\n[bold]Target Audience:[/bold]")
        self.console.print("  • [cyan]general[/cyan] - Non-technical, accessible language")
        self.console.print("  • [cyan]professional[/cyan] - Business/decision-maker focus")
        self.console.print("  • [cyan]technical[/cyan] - Expert-level, detailed terminology")
        
        preferences["audience"] = Prompt.ask(
            "Select audience",
            choices=["general", "professional", "technical"],
            default=existing_prefs.get("audience", "professional")
        )
        
        # 3. Format Style
        self.console.print("\n[bold]Report Style:[/bold]")
        self.console.print("  • [cyan]executive[/cyan] - Summary-focused, key insights first")
        self.console.print("  • [cyan]academic[/cyan] - Detailed citations, thorough analysis")
        self.console.print("  • [cyan]practical[/cyan] - Action-oriented, recommendations focus")
        
        preferences["format_style"] = Prompt.ask(
            "Select style",
            choices=["executive", "academic", "practical"],
            default=existing_prefs.get("format_style", "executive")
        )
        
        # 4. Include Visuals
        self.console.print("\n[bold]Include Visual Elements?[/bold]")
        self.console.print("  (Tables, ASCII diagrams, comparison charts)")
        
        include_visuals = Prompt.ask(
            "Include visuals",
            choices=["yes", "no"],
            default="yes" if existing_prefs.get("include_visuals", True) else "no"
        )
        preferences["include_visuals"] = include_visuals.lower() == "yes"
        
        # 5. Focus Areas (optional)
        self.console.print("\n[bold]Specific Focus Areas?[/bold] (optional)")
        self.console.print("  [dim]Enter comma-separated topics to emphasize, or press Enter to skip[/dim]")
        self.console.print("  [dim]Examples: cost analysis, performance comparison, risk assessment[/dim]")
        
        focus_input = Prompt.ask("Focus areas", default="")
        if focus_input.strip():
            preferences["focus_areas"] = [
                area.strip() for area in focus_input.split(",") if area.strip()
            ]
        else:
            preferences["focus_areas"] = existing_prefs.get("focus_areas", [])
        
        # Display summary
        self.console.print("\n" + "-" * 40)
        self.console.print("[bold green]Report Configuration:[/bold green]")
        self.console.print(f"  • Length: [cyan]{preferences['report_length']}[/cyan]")
        self.console.print(f"  • Audience: [cyan]{preferences['audience']}[/cyan]")
        self.console.print(f"  • Style: [cyan]{preferences['format_style']}[/cyan]")
        self.console.print(f"  • Visuals: [cyan]{'Yes' if preferences['include_visuals'] else 'No'}[/cyan]")
        if preferences.get("focus_areas"):
            self.console.print(f"  • Focus: [cyan]{', '.join(preferences['focus_areas'])}[/cyan]")
        
        return preferences

    def _update_progress_display(self, event):
        """
        Legacy progress display for intent phase (non-live updates).

        Note: Data Gathering, Analysis, and Report phases now use
        LiveProgressPanel for animated, engaging progress display.
        """
        if hasattr(event, 'author') and event.author:
            agent_name = event.author

            # Map agent names to user-friendly status messages
            status_map = {
                "Intent": "📋 Analyzing research intent...",
                "Confidence": "🎯 Checking confidence level...",
                "HumanInput": "👤 Preparing for user input...",
            }

            for key, message in status_map.items():
                if key in agent_name:
                    self.console.print(f"[dim]{message}[/dim]")
                    break

    async def _handle_human_input(self, session, state: Dict[str, Any], current_round: int = 1, max_rounds: int = 5) -> tuple:
        """
        Handle human input during intent clarification.

        Args:
            session: Current ADK session
            state: Current session state
            current_round: Current clarification round (1-indexed)
            max_rounds: Maximum allowed clarification rounds

        Returns:
            Tuple of (action, user_response):
            - ("proceed", None) - User confirmed, continue to data gathering
            - ("clarify", response_text) - User provided clarification, re-run intent analysis
            - ("cancel", None) - User cancelled the research
        """
        input_type = state.get("input_type", "confirmation")
        criteria_display = state.get("intent_criteria_display", {})
        clarification_questions = state.get("clarification_questions", [])
        current_confidence = state.get("current_confidence", 0)

        # Log iteration start
        if self.audit_logger:
            self.audit_logger.start_iteration()
            parsed_intent = state.get("parsed_intent", {})
            self.audit_logger.log_intent_analysis(parsed_intent)
            self.audit_logger.log_criteria_check(
                state.get("criteria_status", {}))

        self.console.print("\n" + "=" * 60)
        self.console.print(
            f"[bold yellow]📋 Intent Analysis - Round {current_round}/{max_rounds}[/bold yellow]")
        self.console.print("=" * 60)

        # Display the criteria checklist
        self._display_criteria_checklist(criteria_display)

        if input_type == "clarification" and clarification_questions:
            # Log clarification questions
            if self.audit_logger:
                self.audit_logger.log_clarification_questions(
                    clarification_questions)

            # Ask clarification questions
            response = await self._ask_clarification_questions(clarification_questions)

            if response is None:
                return ("cancel", None)  # User cancelled

            # Log user response
            if self.audit_logger:
                self.audit_logger.log_user_response(
                    "; ".join(clarification_questions),
                    response
                )

            # Update session state with user response
            await self._update_session_state(session, {
                "user_clarification_response": response,
                "awaiting_user_input": False,
                "response_processed": False,
            })

            if self.audit_logger:
                self.audit_logger.log_iteration_decision(
                    "continue", "User provided clarification")

            return ("clarify", response)

        else:
            # Ask for confirmation to proceed
            # _ask_confirmation_to_proceed already returns a tuple (action, response)
            return await self._ask_confirmation_to_proceed(session, state)

    def _display_criteria_checklist(self, criteria_display: Dict[str, Any]):
        """Display the intent analysis criteria checklist."""
        if not criteria_display:
            return

        criteria = criteria_display.get("criteria", [])
        confidence = criteria_display.get("confidence_score", 0)
        met_count = criteria_display.get("criteria_met_count", 0)
        total_count = criteria_display.get("criteria_total_count", 0)

        # Build criteria table
        table = Table(title="Understanding Your Research Request",
                      show_header=True)
        table.add_column("Status", style="cyan", width=3)
        table.add_column("Criterion", style="white")
        table.add_column("Value", style="green")

        for criterion in criteria:
            icon = criterion.get("icon", "❓")
            name = criterion.get("name", "Unknown")
            value = criterion.get("value", "Not specified")
            table.add_row(icon, name, value)

        self.console.print(table)

        # Confidence bar
        confidence_bar = self._build_confidence_bar(confidence)
        self.console.print(
            f"\n[bold]Confidence Score:[/bold] {confidence_bar} {confidence}%")
        self.console.print(
            f"[dim]Criteria met: {met_count}/{total_count}[/dim]")

        # Show missing information if any
        missing_info = criteria_display.get("missing_information", [])
        if missing_info:
            self.console.print("\n[yellow]⚠️ Missing Information:[/yellow]")
            for info in missing_info[:5]:
                self.console.print(f"  • {info}")

        # Show assumptions if any
        assumptions = criteria_display.get("assumptions", [])
        if assumptions:
            self.console.print("\n[blue]💭 Assumptions Made:[/blue]")
            for assumption in assumptions[:3]:
                self.console.print(f"  • {assumption}")

        # Show research questions
        research_questions = criteria_display.get("research_questions", [])
        if research_questions:
            self.console.print(
                "\n[green]📝 Research Questions Identified:[/green]")
            for i, question in enumerate(research_questions[:5], 1):
                self.console.print(f"  {i}. {question}")

    def _build_confidence_bar(self, confidence: int) -> str:
        """Build a visual confidence bar."""
        filled = int(confidence / 10)
        empty = 10 - filled

        if confidence >= 75:
            color = "green"
        elif confidence >= 50:
            color = "yellow"
        else:
            color = "red"

        return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"

    async def _ask_clarification_questions(self, questions: List[str]) -> Optional[str]:
        """
        Ask clarification questions and get user response.

        Returns:
            User's response text, or None if cancelled
        """
        self.console.print(
            "\n[bold yellow]❓ Clarification Needed[/bold yellow]")
        self.console.print(
            "[dim]Please provide additional information to improve the research:[/dim]\n")

        for i, question in enumerate(questions, 1):
            self.console.print(f"  [cyan]{i}.[/cyan] {question}")

        self.console.print()

        # Offer options
        choice = Prompt.ask(
            "[bold]Your choice[/bold]",
            choices=["answer", "skip", "cancel"],
            default="answer"
        )

        if choice == "cancel":
            return None
        elif choice == "skip":
            return "I'd like to proceed with the current understanding."
        else:
            # Get detailed response
            self.console.print(
                "\n[dim]Enter your clarification (type 'END' on a new line when done):[/dim]")
            response = self._read_multiline_input(
                title="Your Clarification",
                terminator="END"
            )
            return response if response.strip() else "No additional information provided."

    async def _ask_confirmation_to_proceed(self, session, state: Dict[str, Any]) -> tuple:
        """
        Ask user to confirm proceeding with research.

        Returns:
            Tuple of (action, user_response):
            - ("proceed", None) - User confirmed to proceed
            - ("clarify", response_text) - User wants to provide more info
            - ("cancel", None) - User cancelled
        """
        criteria_display = state.get("intent_criteria_display", {})
        confidence = criteria_display.get("confidence_score", 0)
        ready = criteria_display.get("ready_to_proceed", False)

        self.console.print("\n" + "-" * 40)

        if ready and confidence >= 75:
            self.console.print(
                "[green]✅ Research intent is clear and ready to proceed![/green]")
        else:
            self.console.print(
                "[yellow]⚠️ Some criteria are not fully met, but you can still proceed.[/yellow]")

        self.console.print("\n[bold]What would you like to do?[/bold]")
        self.console.print(
            "  1. [green]Proceed[/green] - Start the research with current understanding")
        self.console.print(
            "  2. [yellow]Clarify[/yellow] - Provide more information")
        self.console.print("  3. [red]Cancel[/red] - Cancel this research")

        choice = Prompt.ask(
            "\n[bold]Your choice[/bold]",
            choices=["1", "2", "3", "proceed", "clarify", "cancel"],
            default="1"
        )

        if choice in ["3", "cancel"]:
            if self.audit_logger:
                self.audit_logger.log_user_confirmation(
                    False, "User cancelled")
            return ("cancel", None)

        if choice in ["2", "clarify"]:
            # User wants to provide more info
            self.console.print(
                "\n[dim]Enter additional information or clarification:[/dim]")
            response = self._read_multiline_input(
                title="Additional Information",
                terminator="END"
            )

            if response.strip():
                if self.audit_logger:
                    self.audit_logger.log_user_response(
                        "User-initiated clarification", response)

                await self._update_session_state(session, {
                    "user_clarification_response": response,
                    "awaiting_user_input": False,
                    "response_processed": False,
                })

                if self.audit_logger:
                    self.audit_logger.log_iteration_decision(
                        "continue", "User provided additional clarification")
                return ("clarify", response)
            else:
                # Empty response, treat as proceed
                pass

        # User wants to proceed
        if self.audit_logger:
            self.audit_logger.log_user_confirmation(True)
            parsed_intent = state.get("parsed_intent", {})
            self.audit_logger.finalize(
                final_intent=parsed_intent,
                final_confidence=confidence,
                exit_reason="user_confirmed_proceed"
            )

        await self._update_session_state(session, {
            "user_confirmed_proceed": True,
            "awaiting_user_input": False,
        })

        self.console.print("\n[green]✅ Proceeding with research...[/green]")
        return ("proceed", None)

    async def _ensure_consolidated_data_exists(self, session, timed_out: bool = False):
        """
        Ensure consolidated_data exists in session state even if data gathering failed.

        This prevents the analysis phase from crashing with 'Context variable not found'.
        """
        # Check all possible session sources for consolidated_data
        data_session = await self.session_service.get_session(
            app_name=f"{self.APP_NAME}_data",
            user_id=self.user_id,
            session_id=session.id,
        )

        state = data_session.state if data_session else {}

        # Check if consolidated_data already exists and is valid
        if state.get("consolidated_data") and not state.get("consolidated_data", "").startswith("### "):
            # Has valid data, no need to create fallback
            return

        # Create fallback consolidated_data from whatever partial data we have
        fallback_parts = []
        fallback_parts.append("### Consolidated Research Data (Partial)\n")
        fallback_parts.append(
            "**Note:** Data gathering was interrupted or incomplete.\n\n")

        if timed_out:
            fallback_parts.append(
                "**Status:** ⚠️ Data gathering timed out. Working with partial data.\n\n")

        # Try to include any partial results that were gathered
        internal_knowledge = state.get("internal_knowledge_result", "")
        google_search = state.get("google_search_result", "")
        web_scraping = state.get("web_scraping_result", "")

        sources_found = 0

        if internal_knowledge and len(internal_knowledge) > 50:
            fallback_parts.append("## Internal Knowledge (Available)\n")
            fallback_parts.append(internal_knowledge[:3000] + "...\n\n" if len(
                internal_knowledge) > 3000 else internal_knowledge + "\n\n")
            sources_found += 1

        if google_search and len(google_search) > 50:
            fallback_parts.append("## Google Search Results (Available)\n")
            fallback_parts.append(
                google_search[:3000] + "...\n\n" if len(google_search) > 3000 else google_search + "\n\n")
            sources_found += 1

        if web_scraping and len(web_scraping) > 50:
            fallback_parts.append("## Web Content (Available)\n")
            fallback_parts.append(
                web_scraping[:3000] + "...\n\n" if len(web_scraping) > 3000 else web_scraping + "\n\n")
            sources_found += 1

        if sources_found == 0:
            fallback_parts.append(
                "**Warning:** No data sources completed successfully.\n")
            fallback_parts.append(
                "The analysis will proceed with limited information.\n")
            fallback_parts.append(
                "Consider retrying the research if results are unsatisfactory.\n")
        else:
            fallback_parts.append(
                f"\n**Data Sources Available:** {sources_found}/3\n")

        fallback_data = "".join(fallback_parts)

        # Update session state with fallback
        await self._update_session_state(session, {
            "consolidated_data": fallback_data,
            "consolidated_data_is_partial": True,
            "consolidated_data_sources_count": sources_found,
        })

        self.console.print(
            f"[dim]Created fallback consolidated data from {sources_found} source(s).[/dim]")

    async def _update_session_state(self, session, state_updates: Dict[str, Any]):
        """Update the session state with new values."""
        # Update the main session
        current_session = await self.session_service.get_session(
            app_name=self.APP_NAME,
            user_id=self.user_id,
            session_id=session.id,
        )

        if current_session:
            current_session.state.update(state_updates)

        # Also update the intent session (which is our primary session for phase-by-phase)
        intent_session = await self.session_service.get_session(
            app_name=f"{self.APP_NAME}_intent",
            user_id=self.user_id,
            session_id=session.id,
        )

        if intent_session:
            intent_session.state.update(state_updates)

    async def _sync_session_to_phase(self, main_session, phase_app_name: str):
        """
        Sync session state from main session to a phase-specific session.
        Creates the phase session if it doesn't exist.

        IMPORTANT: This also ensures intent_result contains the parsed intent
        (as a JSON string that downstream agents can read), not just the raw
        LLM output which may be malformed or confusing.

        Also ensures all required state variables have default values to prevent
        ADK from throwing 'Context variable not found' errors.
        """
        # Collect state from all possible sources (intent, data, analysis sessions)
        all_state = {}

        # Try to get state from all phase sessions
        for app_suffix in ["_intent", "_data", "_analysis", ""]:
            app_name = f"{self.APP_NAME}{app_suffix}" if app_suffix else self.APP_NAME
            sess = await self.session_service.get_session(
                app_name=app_name,
                user_id=self.user_id,
                session_id=main_session.id,
            )
            if sess and sess.state:
                all_state.update(sess.state)

        # If no state found, use main_session.state
        if not all_state:
            all_state = dict(main_session.state) if main_session.state else {}

        # FIX: Ensure intent_result contains the properly parsed intent
        parsed_intent = all_state.get("parsed_intent")
        if parsed_intent and isinstance(parsed_intent, dict):
            all_state["intent_result"] = json.dumps(parsed_intent, indent=2)
            self.console.print(
                f"[dim]📋 Intent synced: {parsed_intent.get('research_type', 'unknown')} - "
                f"{', '.join(parsed_intent.get('key_entities', ['N/A']))}[/dim]"
            )

        # FIX: Ensure all required state variables have defaults to prevent
        # 'Context variable not found' errors from ADK
        default_output_preferences = json.dumps({
            "report_length": "standard",
            "audience": "professional",
            "format_style": "executive",
            "include_visuals": True,
            "focus_areas": []
        })
        
        required_defaults = {
            "intent_result": json.dumps({"error": "Intent not available"}),
            "internal_knowledge_result": "No internal knowledge data available.",
            "google_search_result": "No Google search data available.",
            "web_scraping_result": "No web scraping data available.",
            "consolidated_data": "No consolidated data available.",
            "analysis_result": json.dumps({"error": "Analysis not available"}),
            "output_preferences": default_output_preferences,
        }

        for key, default_value in required_defaults.items():
            if key not in all_state or not all_state.get(key):
                all_state[key] = default_value

        # Get or create phase session
        phase_sess = await self.session_service.get_session(
            app_name=phase_app_name,
            user_id=self.user_id,
            session_id=main_session.id,
        )

        if phase_sess is None:
            # Create the phase session with the current state
            phase_sess = await self.session_service.create_session(
                app_name=phase_app_name,
                user_id=self.user_id,
                state=all_state,
                session_id=main_session.id,
            )
        else:
            # Update existing phase session with current state
            phase_sess.state.update(all_state)

    async def _sync_session_from_phase(self, main_session, phase_app_name: str):
        """
        Sync session state from a phase-specific session back to all sessions.
        This ensures state changes propagate across all phase runners.
        """
        # Get phase session state
        phase_sess = await self.session_service.get_session(
            app_name=phase_app_name,
            user_id=self.user_id,
            session_id=main_session.id,
        )

        if phase_sess is None:
            return

        phase_state = dict(phase_sess.state)

        # Update ALL phase sessions to ensure state propagates
        for app_suffix in ["_intent", "_data", "_analysis", "_report", ""]:
            app_name = f"{self.APP_NAME}{app_suffix}" if app_suffix else self.APP_NAME
            sess = await self.session_service.get_session(
                app_name=app_name,
                user_id=self.user_id,
                session_id=main_session.id,
            )
            if sess:
                sess.state.update(phase_state)

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
2. **Interactive Clarification**: Answer questions to refine your research intent
3. **ADK Pipeline**: The engine runs through 4 stages automatically
4. **Review Results**: Examine your comprehensive research report

## Research Pipeline (ADK)
The engine uses Google ADK with the following stages:

1. **Intent Analysis** (IntentClarificationLoop) - NEW: Interactive!
   - Analyzes your research query
   - Shows criteria checklist (research type, domain, entities, etc.)
   - Asks follow-up questions if confidence is low
   - Requires your confirmation before proceeding
   - Audit logs saved to logs/sessions/ for traceability
   
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

## Intent Clarification Features
- **Criteria Checklist**: See what the system understood
- **Confidence Score**: Visual indicator of understanding level
- **Follow-up Questions**: Clarify ambiguous aspects
- **User Confirmation**: You control when to proceed
- **Session Audit**: Full traceback of all interactions

## Tips for Better Results
- Be specific in your research questions
- Answer clarification questions thoroughly
- Review the criteria checklist before proceeding
- Check session logs in logs/sessions/ for debugging

## Configuration
- Set GEMINI_API_KEY in your .env file
- Reports are saved in the reports/ directory
- Session audits saved in logs/sessions/
- CONFIDENCE_THRESHOLD env var (default: 75)

## Timeout Configuration (Safety Nets)
The engine has built-in timeouts to prevent indefinite hangs:

| Phase              | Env Variable                | Default |
|--------------------|----------------------------|---------|
| Data Gathering     | DATA_GATHERING_TIMEOUT      | 5 min   |
| Analysis           | ANALYSIS_TIMEOUT            | 3 min   |
| Report Generation  | REPORT_GENERATION_TIMEOUT   | 3 min   |
| Intent Round       | INTENT_PHASE_TIMEOUT        | 2 min   |

If a phase times out:
- ⚠️ The pipeline continues with partial data
- The next phase works with whatever was gathered
- A complete report is still generated (may note limitations)
        """

        self.console.print(Panel(Markdown(help_text),
                           title="Help & Documentation", border_style="yellow"))


async def run_adk_cli():
    """Entry point for ADK CLI."""
    cli = OdysseyADKCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(run_adk_cli())

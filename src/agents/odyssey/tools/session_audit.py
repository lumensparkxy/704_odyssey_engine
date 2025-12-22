"""
Session Audit Logger Tool.

Records all intent analysis interactions for audit, traceback, and debugging purposes.
Logs: original query, clarification questions, user responses, confidence scores,
decision criteria, and state transitions.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


# Default audit log directory
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "./logs/sessions")


class SessionAuditLogger:
    """
    Audit logger for tracking intent analysis sessions.

    Records all interactions, decisions, and state changes during
    the intent clarification loop for debugging and compliance.
    """

    def __init__(self, session_id: str, user_id: str):
        """
        Initialize the audit logger.

        Args:
            session_id: Unique session identifier
            user_id: User identifier
        """
        self.session_id = session_id
        self.user_id = user_id
        self.start_time = datetime.now()

        # Audit log structure
        self.audit_log: Dict[str, Any] = {
            "session_id": session_id,
            "user_id": user_id,
            "started_at": self.start_time.isoformat(),
            "completed_at": None,
            "original_query": None,
            "intent_iterations": [],
            "final_intent": None,
            "final_confidence": None,
            "user_confirmed": False,
            "decision_criteria": {},
            "exit_reason": None,
        }

        self._current_iteration = 0

    def log_original_query(self, query: str) -> None:
        """
        Record the original user query.

        Args:
            query: The user's original research query
        """
        self.audit_log["original_query"] = query

    def start_iteration(self) -> int:
        """
        Start a new clarification iteration.

        Returns:
            The iteration number (1-indexed)
        """
        self._current_iteration += 1

        iteration_log = {
            "iteration": self._current_iteration,
            "timestamp": datetime.now().isoformat(),
            "intent_analysis": None,
            "confidence_score": None,
            "criteria_met": {},
            "clarification_questions": [],
            "user_responses": [],
            "decision": None,
        }

        self.audit_log["intent_iterations"].append(iteration_log)
        return self._current_iteration

    def log_intent_analysis(self, intent_result: Dict[str, Any]) -> None:
        """
        Record the intent analysis result for current iteration.

        Args:
            intent_result: The structured intent analysis from IntentAnalyzerAgent
        """
        if self.audit_log["intent_iterations"]:
            current = self.audit_log["intent_iterations"][-1]
            current["intent_analysis"] = intent_result
            current["confidence_score"] = intent_result.get("confidence", 0)

    def log_criteria_check(self, criteria: Dict[str, bool]) -> None:
        """
        Record which criteria are met/unmet.

        Args:
            criteria: Dictionary of criterion_name -> met (True/False)
        """
        if self.audit_log["intent_iterations"]:
            current = self.audit_log["intent_iterations"][-1]
            current["criteria_met"] = criteria

    def log_clarification_questions(self, questions: List[str]) -> None:
        """
        Record the clarification questions generated.

        Args:
            questions: List of clarification questions asked
        """
        if self.audit_log["intent_iterations"]:
            current = self.audit_log["intent_iterations"][-1]
            current["clarification_questions"] = questions

    def log_user_response(self, question: str, response: str) -> None:
        """
        Record a user's response to a clarification question.

        Args:
            question: The question that was asked
            response: The user's response
        """
        if self.audit_log["intent_iterations"]:
            current = self.audit_log["intent_iterations"][-1]
            current["user_responses"].append({
                "question": question,
                "response": response,
                "timestamp": datetime.now().isoformat(),
            })

    def log_iteration_decision(self, decision: str, reason: str) -> None:
        """
        Record the decision made at end of iteration.

        Args:
            decision: One of "continue", "proceed", "user_confirmed", "max_iterations"
            reason: Explanation for the decision
        """
        if self.audit_log["intent_iterations"]:
            current = self.audit_log["intent_iterations"][-1]
            current["decision"] = {
                "action": decision,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }

    def log_user_confirmation(self, confirmed: bool, user_comment: Optional[str] = None) -> None:
        """
        Record user's final confirmation to proceed.

        Args:
            confirmed: Whether user confirmed to proceed
            user_comment: Optional comment from user
        """
        self.audit_log["user_confirmed"] = confirmed
        if user_comment:
            self.audit_log["user_confirmation_comment"] = user_comment

    def finalize(
        self,
        final_intent: Dict[str, Any],
        final_confidence: int,
        exit_reason: str,
    ) -> Dict[str, Any]:
        """
        Finalize the audit log and save to file.

        Args:
            final_intent: The final intent analysis result
            final_confidence: The final confidence score
            exit_reason: Why the loop exited

        Returns:
            The complete audit log
        """
        self.audit_log["completed_at"] = datetime.now().isoformat()
        self.audit_log["final_intent"] = final_intent
        self.audit_log["final_confidence"] = final_confidence
        self.audit_log["exit_reason"] = exit_reason

        # Calculate decision criteria summary
        self.audit_log["decision_criteria"] = self._build_criteria_summary(
            final_intent)

        # Save to file
        self._save_to_file()

        return self.audit_log

    def _build_criteria_summary(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Build a summary of all decision criteria."""
        return {
            "has_research_type": bool(intent.get("research_type")),
            "has_domain": bool(intent.get("domain")),
            "has_scope": bool(intent.get("scope")),
            "has_key_entities": bool(intent.get("key_entities")) and len(intent.get("key_entities", [])) > 0,
            "has_research_questions": bool(intent.get("research_questions")) and len(intent.get("research_questions", [])) > 0,
            "has_decision_criteria": bool(intent.get("decision_criteria")),
            "has_success_criteria": bool(intent.get("success_criteria")),
            "missing_info_count": len(intent.get("missing_information", [])),
            "assumptions_count": len(intent.get("assumptions", [])),
            "confidence_threshold_met": intent.get("confidence", 0) >= 75,
        }

    def _save_to_file(self) -> str:
        """
        Save audit log to JSON file.

        Returns:
            Path to saved file
        """
        # Ensure directory exists
        log_dir = Path(AUDIT_LOG_PATH)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create filename with timestamp
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"session_audit_{self.session_id}_{timestamp}.json"
        file_path = log_dir / filename

        # Write JSON with pretty formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.audit_log, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def get_criteria_display(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a formatted criteria checklist for display.

        Args:
            intent: The current intent analysis

        Returns:
            Dictionary with criteria status for UI display
        """
        criteria = self._build_criteria_summary(intent)
        confidence = intent.get("confidence", 0)

        checklist = {
            "criteria": [
                {
                    "name": "Research Type",
                    "met": criteria["has_research_type"],
                    "value": intent.get("research_type", "Not specified"),
                },
                {
                    "name": "Domain/Subject Area",
                    "met": criteria["has_domain"],
                    "value": intent.get("domain", "Not specified"),
                },
                {
                    "name": "Research Scope",
                    "met": criteria["has_scope"],
                    "value": intent.get("scope", "Not specified"),
                },
                {
                    "name": "Key Entities Identified",
                    "met": criteria["has_key_entities"],
                    "value": ", ".join(intent.get("key_entities", [])) or "None identified",
                },
                {
                    "name": "Research Questions",
                    "met": criteria["has_research_questions"],
                    "value": f"{len(intent.get('research_questions', []))} questions defined",
                },
                {
                    "name": "Decision Criteria",
                    "met": criteria["has_decision_criteria"],
                    "value": f"{len(intent.get('decision_criteria', []))} criteria defined",
                },
                {
                    "name": "Success Criteria",
                    "met": criteria["has_success_criteria"],
                    "value": f"{len(intent.get('success_criteria', []))} criteria defined",
                },
            ],
            "confidence_score": confidence,
            "confidence_threshold": 75,
            "confidence_met": confidence >= 75,
            "missing_information": intent.get("missing_information", []),
            "assumptions": intent.get("assumptions", []),
            "ready_to_proceed": criteria["confidence_threshold_met"] and criteria["has_research_questions"],
        }

        # Count met criteria
        checklist["criteria_met_count"] = sum(
            1 for c in checklist["criteria"] if c["met"])
        checklist["criteria_total_count"] = len(checklist["criteria"])

        return checklist


def create_audit_logger(session_id: str, user_id: str) -> SessionAuditLogger:
    """
    Factory function to create an audit logger.

    Args:
        session_id: Session identifier
        user_id: User identifier

    Returns:
        Configured SessionAuditLogger instance
    """
    return SessionAuditLogger(session_id, user_id)

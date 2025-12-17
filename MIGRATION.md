# Odyssey Engine → ADK Migration Tracker

> **Branch:** `feature/adk-migration`  
> **Started:** 2025-12-17  
> **Status:** Phase 2 - Complete

## Architecture Overview

```
CURRENT (src/core/)                    ADK TARGET (src/agents/)
┌─────────────────────┐                ┌─────────────────────────────────────┐
│   ResearchEngine    │                │         SequentialAgent             │
│   (orchestrator)    │       →        │         (root_agent)                │
└─────────────────────┘                └─────────────────────────────────────┘
         │                                          │
         ▼                                          ▼
┌─────────────────────┐                ┌─────────────────────────────────────┐
│  IntentAnalyzer     │       →        │  IntentAnalyzerAgent (LlmAgent)     │
└─────────────────────┘                │  + LoopAgent (clarification)        │
         │                             │  + PolicyEngine (human-in-loop)     │
         ▼                             └─────────────────────────────────────┘
┌─────────────────────┐                             │
│   DataGatherer      │       →        ┌───────────▼───────────────────────┐
│  (sequential)       │                │      ParallelAgent (fan-out)       │
└─────────────────────┘                │  ├─ InternalKnowledgeAgent         │
         │                             │  ├─ GoogleSearchAgent              │
         ▼                             │  └─ WebScraperAgent                │
┌─────────────────────┐                └─────────────────────────────────────┘
│ _analyze_and_compile│       →                     │
└─────────────────────┘                ┌───────────▼───────────────────────┐
         │                             │      AnalysisAgent (LlmAgent)      │
         ▼                             │  (themes, conflicts, synthesis)    │
┌─────────────────────┐                └─────────────────────────────────────┘
│  ReportGenerator    │       →                     │
└─────────────────────┘                ┌───────────▼───────────────────────┐
                                       │    ReportGeneratorAgent (LlmAgent) │
                                       └─────────────────────────────────────┘
```

## File Mapping

| Current File | ADK Target | Notes |
|--------------|------------|-------|
| `src/core/engine.py` | `src/agents/agent.py` | Main orchestration → SequentialAgent |
| `src/core/intent_analyzer.py` | `src/agents/intent/agent.py` | → LlmAgent + LoopAgent |
| `src/core/data_gatherer.py` | `src/agents/data_gathering/agent.py` | → ParallelAgent |
| `src/core/report_generator.py` | `src/agents/report/agent.py` | → LlmAgent |
| `src/utils/gemini_client.py` | ADK built-in | Use ADK's model config |
| `src/utils/web_scraper.py` | `src/agents/tools/scraper.py` | → FunctionTool |
| `src/utils/confidence.py` | `src/agents/tools/confidence.py` | → FunctionTool |
| `src/utils/storage.py` | ADK SessionService | Use built-in services |

---

## Phase 1: Foundation + Intent + Analysis
**Tag:** `migration-phase-1-complete`  
**Goal:** ADK project setup, Intent and Analysis agents working as SequentialAgent

### 1.1 Project Setup
- [x] Install `google-adk` in `pyproject.toml`
- [x] Create `src/agents/` directory structure
- [x] Create `.env` template with `GOOGLE_API_KEY`
- [x] Add `USE_ADK` feature flag to `config/default.conf`
- [x] Update `main.py` to conditionally load ADK or legacy engine

### 1.2 Intent Analyzer Agent
- [x] Create `src/agents/intent/agent.py` with `LlmAgent`
- [x] Define `name="IntentAnalyzerAgent"`
- [x] Define `model` from config (default: `gemini-2.5-pro`)
- [x] Define `instruction` from current `IntentAnalyzer._build_analysis_prompt()`
- [x] Define `output_key="intent_result"`
- [x] Define `description` for agent routing

### 1.3 Clarification Loop with PolicyEngine
- [x] Create `src/agents/intent/clarification.py`
- [x] Implement `ClarificationPolicyEngine(BasePolicyEngine)`
- [x] Create `LoopAgent` wrapper for intent clarification
- [x] Create `ConfidenceCheckerAgent` (custom `BaseAgent`)

### 1.4 Analysis Agent
- [x] Create `src/agents/analysis/agent.py` with `LlmAgent`
- [x] Define `instruction` for theme/conflict identification
- [x] Define `output_key="analysis_result"`

### 1.5 Phase 1 Integration
- [x] Create `src/agents/agent.py` with phase 1 `SequentialAgent`
- [x] Verify with `adk run src/agents`
- [x] Verify with `adk web --port 8000`
- [x] Write integration test: `tests/test_adk_phase1.py`
- [x] **Gate:** All phase 1 tests pass (17 tests)
- [x] **Git tag:** `git tag migration-phase-1-complete`

---

## Phase 2: Parallel Data Gathering
**Tag:** `migration-phase-2-complete`  
**Goal:** Multi-source data collection with ParallelAgent

### 2.1 Data Gathering Tools
- [x] Create `src/agents/odyssey/tools/scraper.py` (wrap `WebScraper.scrape_url()`)
- [x] ADK built-in `google_search` tool for Google Search grounding

### 2.2 Data Gathering Sub-Agents
- [x] Create `src/agents/odyssey/data_gathering/internal_knowledge.py`
- [x] Create `src/agents/odyssey/data_gathering/google_search.py`
- [x] Create `src/agents/odyssey/data_gathering/web_scraper_agent.py`

### 2.3 ParallelAgent for Fan-Out
- [x] Create `src/agents/odyssey/data_gathering/parallel_gatherer.py` with `ParallelAgent`
- [x] Handle web scraping with custom FunctionTool

### 2.4 Data Consolidation Agent
- [x] Create `src/agents/odyssey/data_gathering/consolidator.py`

### 2.5 Phase 2 Integration
- [x] Update `src/agents/odyssey/agent.py` with data gathering pipeline
- [x] Verify with `adk web --port 8000`
- [x] Write integration test: `tests/test_adk_phase2.py`
- [x] **Gate:** All phase 2 tests pass (24 tests)
- [x] **Git tag:** `git tag migration-phase-2-complete`

---

## Phase 3: Report Generation + Full Pipeline
**Tag:** `migration-phase-3-complete`  
**Goal:** Complete research pipeline producing markdown reports

### 3.1 Report Generator Agent
- [ ] Create `src/agents/report/agent.py`
- [ ] Define report structure in instruction

### 3.2 Report Output Handling
- [ ] Create `src/agents/tools/file_writer.py`
- [ ] Create `ReportFinalizerAgent`

### 3.3 Confidence Scoring Integration
- [ ] Create `src/agents/tools/confidence.py`
- [ ] Add confidence scoring after each major stage

### 3.4 Full Pipeline Assembly
- [ ] Update `src/agents/agent.py` with complete pipeline
- [ ] Write full pipeline integration test
- [ ] **Gate:** Full pipeline produces valid research report
- [ ] **Git tag:** `git tag migration-phase-3-complete`

---

## Phase 4: CLI Migration + Legacy Cleanup
**Tag:** `migration-phase-4-complete`  
**Goal:** Remove legacy code, finalize CLI

### 4.1 CLI Updates
- [ ] Update `src/cli/interface.py` with ADK `Runner`
- [ ] Update `src/cli/entrypoint.py` with new flags
- [ ] Test CLI commands

### 4.2 Session Migration
- [ ] Create migration script for existing sessions
- [ ] Update session storage path config

### 4.3 Legacy Code Removal
- [ ] Remove `USE_ADK` feature flag
- [ ] Archive legacy files
- [ ] Update all imports

### 4.4 Documentation & Cleanup
- [ ] Update `README.md` with ADK architecture
- [ ] Update `DEVELOPMENT.md`
- [ ] Archive this `MIGRATION.md`

### 4.5 Final Validation
- [ ] Run full test suite
- [ ] Manual end-to-end test
- [ ] **Gate:** All tests pass, legacy code removed
- [ ] **Git tag:** `git tag migration-phase-4-complete`
- [ ] **Merge to main**

---

## Quick Reference

### Commands
```bash
# Development
adk run src/agents           # CLI test
adk web --port 8000          # Web UI test

# Testing
pytest tests/test_adk_*.py   # ADK-specific tests
pytest tests/                # Full suite

# Phase tags
git tag migration-phase-X-complete
git push origin --tags
```

### State Keys Reference
| Key | Set By | Used By |
|-----|--------|---------|
| `intent_result` | IntentAnalyzerAgent | ConfidenceCheckerAgent, DataGatherers, AnalysisAgent, ReportGenerator |
| `needs_clarification` | ConfidenceCheckerAgent | LoopAgent (escalate) |
| `internal_knowledge_result` | InternalKnowledgeAgent | ConsolidatorAgent |
| `google_search_result` | GoogleSearchAgent | WebScraperAgent, ConsolidatorAgent |
| `web_scraping_result` | WebScraperAgent | ConsolidatorAgent |
| `consolidated_data` | ConsolidatorAgent | AnalysisAgent, ReportGenerator |
| `analysis_result` | AnalysisAgent | ReportGenerator |
| `report_content` | ReportGeneratorAgent | ReportFinalizerAgent |
| `report_file_path` | ReportFinalizerAgent | CLI output |

### Rollback Procedure
```bash
# If phase N fails, rollback to phase N-1
git checkout migration-phase-(N-1)-complete
# Re-enable USE_ADK=false in config if needed
```

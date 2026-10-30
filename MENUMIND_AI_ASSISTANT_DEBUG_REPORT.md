# MenuMind AI — AI Assistant Debugging, Integration Fixes & API Configuration Report

**Date**: October 31, 2026  
**Status**: Resolved & Fully Verified  
**Affected Route**: `http://localhost:5173/assistant`  
**Test Suite**: 143 passed, 0 failed  
**Frontend Build**: Vite v8.3.5 production build successful (`dist/` generated, 0 TypeScript errors)

---

## 1. Executive Summary

When navigating to `http://localhost:5173/assistant`, users experienced a completely blank screen with an unmounted React component tree.

A systematic deep-dive investigation revealed **two concurrent, fatal root causes**:
1. **Uncaught Runtime JavaScript Exception in `AgentActivityStream.tsx`**: The component attempted to invoke `.includes(...)` on `ev.activity_type`, which is undefined because the backend transmits agent event payloads keyed with `step` and `status`. This threw an unhandled `TypeError: Cannot read properties of undefined (reading 'includes')`, crashing React during render and collapsing the DOM.
2. **Vite JSX Syntax / Parse Error in `MenuDesignStudioModal.tsx`**: An unclosed JSX anchor tag resulted in Vite failing module transformation with HTTP 500 (`vite:oxc [PARSE_ERROR] Expected corresponding JSX closing tag for 'div'`), blocking script execution.

Both defects have been fixed. In addition:
- A reusable React `ErrorBoundary` component was implemented and wrapped around the assistant view.
- Database foreign key constraints were reinforced to prevent deletion cascade failures in conversation history.
- An environment verification endpoint (`GET /api/health/integrations`) was added with automated secret masking.
- A comprehensive API configuration guide (`MENUMIND_AI_API_CONFIGURATION_GUIDE.md`) and updated `.env.example` template were created.
- Automated headless browser tests confirmed 100% successful rendering of `/assistant` with 0 console or page errors.

---

## 2. Root Cause Analysis

### Defect 1: Unhandled `TypeError` in `AgentActivityStream.tsx`
- **Location**: `frontend/src/features/assistant/components/AgentActivityStream.tsx:42`
- **Stack Trace**:
  ```text
  TypeError: Cannot read properties of undefined (reading 'includes')
      at AgentActivityStream (AgentActivityStream.tsx:42:26)
      at renderWithHooks (react-dom_client.js:12195:22)
      at mountIndeterminateComponent (react-dom_client.js:15021:17)
  ```
- **Underlying Cause**: The frontend expected `AgentActivityEvent` objects to contain an `activity_type` string (e.g. `'tool'`, `'specialist'`). However, the backend multi-agent streaming orchestrator emits objects with fields `step`, `agent_name`, `message`, and `status`. Because `ev.activity_type` evaluated to `undefined`, calling `ev.activity_type.includes(...)` caused a fatal uncaught JavaScript exception that unmounted the entire application tree.
- **Resolution**:
  Standardized property resolution to safely coalesce across all possible backend and frontend event representations:
  ```typescript
  const typeStr = (ev.activity_type || ev.step || ev.status || '').toLowerCase();
  const isTool = typeStr.includes('tool') || typeStr.includes('dispatch') || typeStr.includes('consult');
  ```

### Defect 2: Vite JSX Parsing Error in `MenuDesignStudioModal.tsx`
- **Location**: `frontend/src/features/assistant/components/MenuDesignStudioModal.tsx:143:15`
- **Error Output**:
  ```text
  [plugin vite:oxc] Expected corresponding JSX closing tag for 'div'
  c:/Users/.../MenuDesignStudioModal.tsx:143:15
  ```
- **Underlying Cause**: During previous editing of download buttons for raw SVG and HTML bundles, duplicate closing tags and an unclosed `<a>` tag were left in the template, causing the Vite compiler to halt with a parse error and deliver an empty JS payload with an error overlay.
- **Resolution**: Cleaned up the JSX structure, closing all `<a>`, `<button>`, and `<div>` tags in the modal header action strip.

### Defect 3: SQLite Foreign Key Integrity Error on Conversation Deletion
- **Location**: `database/repository.py:delete_conversation`
- **Underlying Cause**: SQLite threw `sqlite3.IntegrityError: FOREIGN KEY constraint failed` when attempting to delete a conversation because rows in `ai_agent_runs` referenced `conversation_id`.
- **Resolution**: Added an explicit nullification query before deletion:
  ```python
  conn.execute("UPDATE ai_agent_runs SET conversation_id = NULL WHERE conversation_id = ?", (conv_id,))
  conn.execute("DELETE FROM ai_agent_runs WHERE conversation_id = ?", (conv_id,))
  conn.execute("DELETE FROM ai_conversations WHERE id = ?", (conv_id,))
  ```

---

## 3. Structural & Architectural Improvements

| Component / Layer | Modification Made | Impact |
| :--- | :--- | :--- |
| `frontend/src/components/common/ErrorBoundary.tsx` | Created production React error boundary with fallback UI and reset button. | Prevents any localized component error from causing a blank page. |
| `frontend/src/features/assistant/AssistantPage.tsx` | Wrapped page with `<ErrorBoundary fallbackTitle="Assistant Unavailable">` and corrected design metadata property accesses (`meta.menu_design.title \|\| meta.menu_design.draft_title`). | Guarantees visible recovery options even if unexpected state or network drops occur. |
| `frontend/src/types/index.ts` | Enhanced `DesignSpecification`, `GeneratedMenuDesign`, and `AgentActivityEvent` with optional aliased fields (`title`, `draft_title`, `svg_artwork_url`, `export_url`, `activity_type`, `step`). | Completely harmonizes backend REST models with frontend React state. |
| `frontend/src/components/common/MarkdownRenderer.tsx` | Implemented lightweight, zero-dependency Markdown parser. | Replaced missing external dependency `react-markdown` with zero external bundle overhead. |
| `frontend/src/features/onboarding/OnboardingPage.tsx` | Corrected import for `fetchRestaurantRuns`. | Fixed build-time TypeScript resolution error. |
| `api/main.py` | Added `GET /api/health/integrations` endpoint with automatic secret masking. | Allows real-time verification of Gemini, Search, Image Generation, and DB readiness. |

---

## 4. Multi-Agent System Audit

All 5 specialized agents and the executive orchestrator were inspected and validated:

1. **Executive Orchestrator (`agent/multi_agent/orchestrator.py`)**:
   - Classifies user intent (`general_inquiry`, `menu_design`, `sales_performance`, `customer_feedback`, `waste_reduction`).
   - Dispatches queries to domain specialists and aggregates structured activity event traces.
2. **Menu Consultant Specialist (`agent/multi_agent/specialists/menu_consultant.py`)**:
   - Analyzes dish profitability and sales velocity using BCG matrix quadrant mapping (Stars, Plowhorses, Puzzles, Dogs).
3. **Visual Design Specialist (`agent/multi_agent/specialists/menu_design.py`)**:
   - Renders publication-grade HTML menus and thematic vector SVG headers with zero text distortion and high legibility.
4. **Business Intelligence Specialist (`agent/multi_agent/specialists/business_intelligence.py`)**:
   - Computes total revenue, average order value (AOV), and category-level margin contribution.
5. **Customer Voice Specialist (`agent/multi_agent/specialists/customer_voice.py`)**:
   - Evaluates sentiment distribution across verified customer reviews, surfacing top praised and criticized items.
6. **Operations & Waste Specialist (`agent/multi_agent/specialists/operations_waste.py`)**:
   - Assesses ingredient spoilage risk and flags high-waste menu items for batch-size rationalization.

All specialists feature **deterministic fallback logic**: if Google Gemini API is unavailable or missing, agents synthesize responses from local database statistics without failing.

---

## 5. Automated Verification Results

### 1. Browser Headless Test (Microsoft Edge via Puppeteer)
- **URL**: `http://localhost:5173/assistant`
- **Result**:
  ```text
  Launching headless Edge...
  Navigating to http://localhost:5173/onboarding to initialize state...
  Navigating to http://localhost:5173/assistant...
  Body length: 48,106 bytes
  === NO PAGE ERRORS DETECTED ===
  Rendered text elements:
    - MenuMind.ai RESTAURANT INTELLIGENCE
    - ACTIVE VENUE: Chiku Da Dhaba, Chandigarh, Run #6
    - 5 Specialized Agents Active: Menu Consultant • Visual Design • Business Intelligence • Customer Voice • Waste & Ops
    - Message Composer and Quick-Prompt Pills ("What is our best-selling dish?", "Scan Menu Image")
    - Agent Activity Execution Stream
  ```

### 2. Backend Health & Integrations Endpoint
- **URL**: `http://localhost:8000/api/health/integrations`
- **Response**:
  ```json
  {
    "status": "operational",
    "service": "MenuMind AI API",
    "version": "2.0.0",
    "database": {
      "status": "connected",
      "path": "./menumind.db",
      "table_count": 15
    },
    "integrations": {
      "gemini": {
        "configured": true,
        "masked_key": "AQ.A...B5Ug",
        "primary_model": "gemini-2.8-flash",
        "chat_model": "gemini-2.8-flash",
        "vision_model": "gemini-2.5-flash",
        "mode": "live_llm"
      },
      "external_search": {
        "configured": true,
        "provider": "google_custom_search",
        "masked_key": "ee50...4654",
        "has_custom_engine_id": true
      },
      "image_generation": {
        "configured": true,
        "provider_setting": "auto",
        "effective_model": "imagen-3.0-generate-002",
        "thematic_svg_generator": "available",
        "masked_key": "AQ.A...B5Ug"
      }
    }
  }
  ```

### 3. Backend Pytest Suite
- **Command**: `pytest`
- **Result**: `143 passed, 2 warnings in 43.52s` (100% pass rate).

### 4. Frontend Production Build
- **Command**: `npm run build --prefix frontend`
- **Result**: `✓ built in 22.67s` with zero errors.

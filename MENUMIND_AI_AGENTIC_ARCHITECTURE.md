# MenuMind AI – Agentic Multi-Agent Architecture & Engineering Specification

## Executive Summary

MenuMind AI has been transformed from a single-pipeline decision support tool into an autonomous, multi-agent restaurant intelligence platform. Built on FastAPI, React 19, TypeScript, and SQLite, MenuMind AI coordinates five specialized agents under a central orchestrator. It features an interactive conversational workspace (`/assistant`), a persistent floating assistant drawer, vision-based menu transcription, and a publication-grade visual menu design engine with zero hallucination.

---

## 1. Multi-Agent System Architecture

```mermaid
flowchart TD
    User([User / Restaurant Manager]) -->|Query / Menu Image| Orch[MultiAgentOrchestrator]
    
    subgraph MultiAgentCore [Multi-Agent Core Layer]
        Orch -->|Intent: Menu Strategy| Spec1[Menu Consultant Agent]
        Orch -->|Intent: Publication Design| Spec2[Menu Design Agent]
        Orch -->|Intent: Financial & Revenue| Spec3[Business Intelligence Agent]
        Orch -->|Intent: Customer Reputation| Spec4[Customer Voice Agent]
        Orch -->|Intent: Spoilage & Prevention| Spec5[Operations & Waste Agent]
    end

    subgraph DataExecution [Data & Service Execution]
        Spec1 --> Ingestion[Vision OCR / Structured Draft Engine]
        Spec2 --> ImageGen[Google Imagen / Thematic SVG Provider]
        Spec3 --> Analytics[Deterministic Analytics & Profitability Engine]
        Spec4 --> Sentiment[Sentiment Analysis & SerpApi Fallback]
        Spec5 --> Waste[Food Waste Service & Inventory Velocity]
    end

    subgraph Persistence [SQLite Database (menumind.db)]
        DB[(15 Normalized Tables)]
        Conv[ai_conversations]
        Msg[ai_messages]
        Assets[ai_generated_assets]
        Runs[ai_agent_runs]
    end

    MultiAgentCore --> Persistence
    DataExecution --> Persistence
    Orch -->|Stream Turn Response + Activity Events| User
```

---

## 2. Specialized Agents & Capabilities

### 1. Menu Consultant Agent (`agent/multi_agent/specialists/menu_consultant.py`)
- **Core Function**: Culinary strategy, new menu creation from natural language descriptions, menu portfolio auditing, recipe pricing rationale, and vision menu digitization.
- **Capabilities**:
  - `create_menu_from_scratch()`: Generates structured, balanced JSON menus categorized with names, prices, descriptions, and dietary tags.
  - `analyze_existing_menu()`: Performs catalog audit evaluating category coverage, price spread, and margin targets.
  - `_generate_fallback_menu()`: Provides deterministic, high-quality culinary drafts when offline or when LLM responses require validation.

### 2. Menu Design Agent (`agent/multi_agent/specialists/menu_design.py`)
- **Core Function**: Publication-grade visual menu design generation.
- **Hybrid Rendering Architecture**:
  - **Layer 1: Visual Theme Background**: Generates high-resolution vector artwork or generated imagery (via Google Imagen or Thematic SVG Artwork Provider) for 8 distinct culinary presets (Traditional Indian, Cafe & Bakery, Luxury Black & Gold, Modern Minimalist, Italian Trattoria, Mexican Cantina, Healthy Bowls, Asian Street Food).
  - **Layer 2: Deterministic Typography Overlay**: Positions exact item titles, prices, descriptions, dots/leaders, and currency symbols using CSS grid/flexbox. **Guarantees zero text distortion or numeric hallucination**.
  - **Export Formats**: Self-contained HTML bundle, raw scalable SVG, and print-ready layout.

### 3. Business Intelligence Agent (`agent/multi_agent/specialists/business_intelligence.py`)
- **Core Function**: Grounded financial and sales intelligence.
- **Capabilities**: Deterministic queries on revenue, units sold, ticket averages, top/weak item velocity, and contribution margins ($\text{Price} - \text{Unit Cost}$). Enforces strict grounding: will never fabricate dates or numbers.

### 4. Customer Voice Agent (`agent/multi_agent/specialists/customer_voice.py`)
- **Core Function**: Guest review and sentiment synthesis.
- **Capabilities**: Distinguishes verified customer reviews from external search snippets. Highlights recurring praises, complaints, and dish-level impressions.

### 5. Operations & Waste Agent (`agent/multi_agent/specialists/operations_waste.py`)
- **Core Function**: Kitchen food waste mitigation and spoilage risk detection.
- **Capabilities**: Evaluates physical waste audit records ($\text{Quantity} \times \text{Unit Cost}$) combined with sales consumption velocities to calculate weekly financial exposure and prescribe operational prep adjustments.

---

## 3. SQLite Database Schema & Extensions

MenuMind AI maintains complete backwards compatibility with all 11 existing tables while introducing 4 additive persistence tables:

```sql
-- Conversational Workspaces
CREATE TABLE IF NOT EXISTS ai_conversations (
    id TEXT PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    run_id INTEGER REFERENCES analysis_runs(id),
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Turn-by-Turn Messages & Multi-Agent Metadata
CREATE TABLE IF NOT EXISTS ai_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    attachments JSON DEFAULT '[]',
    agent_metadata JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Publication Designs & Vision Assets
CREATE TABLE IF NOT EXISTS ai_generated_assets (
    id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES ai_conversations(id),
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,
    title TEXT,
    content JSON,
    image_url TEXT,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Trace & Execution Logging
CREATE TABLE IF NOT EXISTS ai_agent_runs (
    id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES ai_conversations(id),
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    specialist_agent TEXT NOT NULL,
    intent TEXT NOT NULL,
    tools_called JSON DEFAULT '[]',
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    latency_ms REAL,
    status TEXT DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Seeded Demo Restaurants & Ground-Truth Profiles

The database is pre-seeded with four statistically distinct, verified restaurant profiles:

| ID | Restaurant Name | Cuisine / Concept | Verified Revenue | Units Sold | Top Selling Item |
|---|---|---|---|---|---|
| **4** | **Chiku Da Dhaba** | Traditional Punjabi North Indian | ₹2,15,420 | 973 units | Dum Chicken Biryani (₹48,000) |
| **5** | **Urban Brew Cafe** | Specialty Coffee, Brunch & Pastries | ₹1,02,745 | 529 units | Vanilla Bean Cold Brew (₹21,600) |
| **6** | **Napoli Kitchen** | Neapolitan Pizzeria & Wine Bar | ₹2,54,060 | 492 units | Margherita D.O.P. (₹49,600) |
| **7** | **Green Bowl Kitchen** | Fast-Casual Superfoods & Bowls | ₹1,39,930 | 494 units | Quinoa Harvest Power Bowl (₹34,800) |

---

## 5. Frontend User Experience & Integration

1. **Dedicated AI Workspace (`/assistant`)**:
   - Left drawer for past conversations with real-time title search and deletion.
   - Message timeline with specialist badges, intent tags, execution activity traces, and suggested followup chips.
   - Interactive Structured Menu Draft cards with one-click opening of the **Structured Menu Editor Modal**.
   - Interactive Design cards with one-click opening of the **Menu Design Studio Modal**.
   - Bottom composer supporting document/image attachments and one-click **Scan Menu Image** via Gemini Vision.
2. **Persistent Floating Assistant & Slide-Over Drawer**:
   - Floating forest-green button available across all pages.
   - Non-intrusive slide-over drawer enabling instant queries while viewing analytics or recommendations.
   - Seamless one-click promotion to full `/assistant` workspace.
3. **In-Context Recommendation Experiments**:
   - Recommendations page features action counter badges, bulk approval for high-confidence items ($\ge 80\%$), in-context experiment creation modals, and contextual "Ask Assistant" triggers.
4. **Dynamic Sales Analytics**:
   - Synchronous recalculation across all KPI cards, trends, and item tables upon selecting date filter pills (Full Period, Last 30 Days, Last 7 Days).
   - Category filtering, item search, and CSV export.

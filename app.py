"""
MenuMind AI — Main Streamlit Entry Point
"""
import streamlit as st

# Page config must be first Streamlit call
st.set_page_config(
    page_title="MenuMind AI",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize DB on startup
from database.connection import initialize_database
initialize_database()

from ui.dashboard import render_dashboard
from ui.upload_page import render_upload_page
from ui.analytics_page import render_analytics_page
from ui.review_page import render_review_page
from ui.recommendations_page import render_recommendations_page
from ui.experiments_page import render_experiments_page
from ui.reports_page import render_reports_page
from ui.food_waste_page import render_food_waste_page
from database import repository as repo

# ─── Premium Global Styles ────────────────────────────────────────────────────
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #f7f8fc;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #1b2a3f 55%, #0f3460 100%);
        border-right: 1px solid #ffffff12;
    }
    [data-testid="stSidebar"] * { color: #c8d6e5 !important; }
    [data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
    [data-testid="stSidebar"] .stRadio label {
        font-size: 0.92rem;
        padding: 9px 14px;
        border-radius: 8px;
        transition: background 0.18s, color 0.18s;
        cursor: pointer;
        display: block;
        font-weight: 500;
        letter-spacing: 0.01em;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,0.08) !important;
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] input[type="radio"]:checked + div label,
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] input:checked ~ div {
        background: rgba(56, 189, 163, 0.18) !important;
        color: #38bda3 !important;
        font-weight: 600;
    }
    [data-testid="stSidebar"] .stDivider { border-color: #ffffff18 !important; }

    /* ── Main content ── */
    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
        max-width: 1280px;
    }

    /* ── Page headings ── */
    h1 { font-size: 1.7rem !important; font-weight: 800 !important; color: #0d1b2a !important; }
    h2 { font-size: 1.25rem !important; font-weight: 700 !important; color: #1b2a3f !important; }
    h3 { font-size: 1.05rem !important; font-weight: 600 !important; color: #1b2a3f !important; }

    /* ── Metric cards ── */
    div[data-testid="metric-container"] {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px 18px;
        border: 1px solid #e8edf4;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        box-shadow: 0 4px 14px rgba(0,0,0,0.1);
    }
    div[data-testid="metric-container"] [data-testid="metric-label"] {
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        color: #6b7a8d !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    div[data-testid="metric-container"] [data-testid="metric-value"] {
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        color: #0d1b2a !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 8px 20px !important;
        transition: all 0.18s !important;
        border: 1.5px solid transparent !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0f3460, #0a4a7c) !important;
        color: #ffffff !important;
        border-color: transparent !important;
        box-shadow: 0 2px 8px rgba(15,52,96,0.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0a4a7c, #0f3460) !important;
        box-shadow: 0 4px 16px rgba(15,52,96,0.4) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        background: #ffffff !important;
        color: #0f3460 !important;
        border-color: #d0d9e8 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #0f3460 !important;
        background: #f0f4ff !important;
    }

    /* ── Forms & Inputs ── */
    .stTextInput input, .stSelectbox > div, .stDateInput input,
    .stTextArea textarea, .stNumberInput input {
        border-radius: 8px !important;
        border: 1.5px solid #d8e1ec !important;
        font-size: 0.9rem !important;
        background: #ffffff !important;
        transition: border 0.18s !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #0f3460 !important;
        box-shadow: 0 0 0 3px rgba(15,52,96,0.1) !important;
    }

    /* ── Tabs ── */
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        color: #6b7a8d !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 8px 18px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #0f3460 !important;
        border-bottom: 2.5px solid #38bda3 !important;
    }

    /* ── Expanders ── */
    details summary {
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        color: #1b2a3f !important;
        padding: 10px 0 !important;
    }
    details[open] {
        background: #fafbfd;
        border-radius: 10px;
        padding: 4px 12px;
        border: 1px solid #e8edf4;
    }

    /* ── Dataframe ── */
    .dataframe-container { border-radius: 10px !important; }

    /* ── Alerts ── */
    .stAlert { border-radius: 10px !important; font-size: 0.88rem !important; }

    /* ── Divider ── */
    hr { border-color: #e8edf4 !important; margin: 1.2rem 0 !important; }

    /* ── Plotly charts ── */
    .js-plotly-plot { border-radius: 12px; }

    /* ── Hide Streamlit chrome ── */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    [data-testid="stToolbar"] { visibility: hidden; }

    /* ── Teal accent chip ── */
    .badge-chip {
        display: inline-block;
        background: #e8f7f4;
        color: #1a7a65;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.76rem;
        font-weight: 600;
        letter-spacing: 0.03em;
    }

    /* ── KPI card custom ── */
    .kpi-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 20px 22px;
        border: 1px solid #e8edf4;
        box-shadow: 0 1px 5px rgba(0,0,0,0.05);
    }
    .kpi-card .kpi-label {
        font-size: 0.76rem;
        font-weight: 600;
        color: #8896a8;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 6px;
    }
    .kpi-card .kpi-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0d1b2a;
        line-height: 1.1;
    }
    .kpi-card .kpi-sub {
        font-size: 0.78rem;
        color: #8896a8;
        margin-top: 4px;
    }

    /* ── Section headers ── */
    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0d1b2a;
        margin: 0 0 14px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #e8edf4;
    }
</style>
""",
    unsafe_allow_html=True,
)

NAV_PAGES = [
    "🏠  Overview",
    "📁  Data Upload",
    "📈  Sales Analytics",
    "⭐  Review Insights",
    "♻️  Food Waste Intelligence",
    "🤖  AI Recommendations",
    "🧪  Experiments",
    "📄  Reports",
]

def resolve_nav_target(target: str, nav_pages: list[str] = NAV_PAGES) -> str:
    """
    Resolve programmatic navigation targets (e.g. 'Sales Analytics' or '📈  Sales Analytics')
    to the matching NAV_PAGES option. Defaults to nav_pages[0] if unmatched.
    """
    if not target:
        return nav_pages[0]
    t = target.strip().lower()
    for np in nav_pages:
        np_clean = np.lower()
        if t in np_clean or np_clean in t:
            return np
    return nav_pages[0]


# Sync programmatic page navigation
if "_nav_to" in st.session_state:
    target_nav = st.session_state.pop("_nav_to")
    st.session_state["nav_radio"] = resolve_nav_target(target_nav, NAV_PAGES)

if "nav_radio" not in st.session_state:
    st.session_state["nav_radio"] = NAV_PAGES[0]

# ─── Sidebar Navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding:20px 0 12px 0;">
            <div style="font-size:2.2em; margin-bottom:4px;">🍽️</div>
            <div style="font-size:1.18em; font-weight:800; color:#ffffff; letter-spacing:0.3px;">
                MenuMind AI
            </div>
            <div style="font-size:0.72em; color:#7a9abf; margin-top:4px; letter-spacing:0.05em;">
                RESTAURANT ANALYTICS
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    page = st.radio(
        "Navigate",
        options=NAV_PAGES,
        key="nav_radio",
        label_visibility="collapsed",
    )

    st.divider()

    # Active restaurant status card
    run_id = st.session_state.get("active_run_id")
    restaurant = st.session_state.get("restaurant_info", {})
    if run_id and restaurant:
        name = restaurant.get("name", "—")
        city = restaurant.get("city", "—")
        cat = restaurant.get("category", "")
        st.markdown(
            f"""
            <div style="background:#ffffff12; border-radius:10px; padding:12px 14px; font-size:0.82em; margin-bottom:12px;">
                <div style="color:#38bda3; font-weight:700; font-size:0.75em; text-transform:uppercase;
                     letter-spacing:0.07em; margin-bottom:6px;">Active Restaurant</div>
                <div style="color:#ffffff; font-weight:600; font-size:0.96em;">{name}</div>
                <div style="color:#7a9abf; font-size:0.82em; margin-top:2px;">{cat}{" · " if cat else ""}{city}</div>
                <div style="color:#38bda3; font-size:0.78em; margin-top:6px;">Run #{run_id}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div style="background:#ffffff08; border-radius:10px; padding:12px 14px;
                font-size:0.82em; color:#7a9abf; text-align:center; margin-bottom:12px;">
                No active restaurant<br>
                <span style="font-size:0.88em;">Set up on Overview or Data Upload</span>
            </div>""",
            unsafe_allow_html=True,
        )

    # Global restaurant switcher in sidebar
    all_rests = repo.list_restaurants()
    if all_rests:
        with st.expander("🏢 Switch Restaurant", expanded=False):
            switch_map = {f"{r['name']} ({r.get('city') or '—'})": r for r in all_rests}
            switch_choice = st.selectbox(
                "Select:",
                options=list(switch_map.keys()),
                key="sidebar_switch_rest",
                label_visibility="collapsed",
            )
            if st.button("Switch Active Restaurant", use_container_width=True, key="btn_switch_rest"):
                chosen_r = switch_map[switch_choice]
                c_id = chosen_r["id"]
                st.session_state["active_restaurant_id"] = c_id
                st.session_state["restaurant_info"] = dict(chosen_r)
                # Load latest completed run for this restaurant if available
                past_runs = repo.list_runs_for_restaurant(c_id)
                if past_runs:
                    st.session_state["active_run_id"] = past_runs[0]["id"]
                    recs = repo.list_recommendations(past_runs[0]["id"])
                    st.session_state["data_quality_score"] = past_runs[0].get("data_quality_score", 1.0)
                else:
                    st.session_state.pop("active_run_id", None)
                st.rerun()

# ─── Page Routing ─────────────────────────────────────────────────────────────
if "Overview" in page:
    render_dashboard()
elif "Data Upload" in page:
    render_upload_page()
elif "Sales Analytics" in page:
    render_analytics_page()
elif "Review Insights" in page:
    render_review_page()
elif "Food Waste" in page:
    render_food_waste_page()
elif "AI Recommendations" in page:
    render_recommendations_page()
elif "Experiments" in page:
    render_experiments_page()
elif "Reports" in page:
    render_reports_page()

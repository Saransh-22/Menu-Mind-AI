"""
Reports & Exports page — premium redesign.
All HTML report, CSV export, and experiments summary logic preserved.
"""
from __future__ import annotations

import io
import streamlit as st

from services.report_service import generate_html_report, recommendations_to_csv
from database import repository as repo


def _section(title: str):
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)


def _export_card(icon: str, title: str, desc: str, button_html: str):
    st.markdown(
        f"""<div style="background:#ffffff;border-radius:14px;padding:20px 22px;
            border:1px solid #e8edf4;box-shadow:0 1px 5px rgba(0,0,0,0.04);height:100%;">
            <div style="font-size:1.6em;margin-bottom:8px;">{icon}</div>
            <div style="font-weight:700;font-size:0.95rem;color:#0d1b2a;margin-bottom:4px;">{title}</div>
            <div style="color:#8896a8;font-size:0.82rem;margin-bottom:14px;">{desc}</div>
        </div>""",
        unsafe_allow_html=True,
    )
    return button_html


def render_reports_page():
    st.markdown(
        "<h1 style='margin-bottom:4px;'>📄 Reports & Exports</h1>"
        "<p style='color:#6b7a8d;font-size:0.92rem;margin-bottom:24px;'>Download reports and export data for your records.</p>",
        unsafe_allow_html=True,
    )

    run_id = st.session_state.get("active_run_id")
    restaurant_info = st.session_state.get("restaurant_info", {})
    restaurant_name = restaurant_info.get("name", "Unknown Restaurant")
    agent_state = st.session_state.get("agent_state")
    quality_reports = st.session_state.get("quality_reports", [])

    if not run_id:
        st.info("Create or load a restaurant on the Overview page first.", icon="ℹ️")
        return

    # ── Export Cards ──────────────────────────────────────────────────────
    _section("📥 Download Options")
    col1, col2, col3 = st.columns(3)

    # HTML Report
    with col1:
        st.markdown(
            """<div style="background:#ffffff;border-radius:14px;padding:20px 22px;
                border:1px solid #e8edf4;box-shadow:0 1px 5px rgba(0,0,0,0.04);">
                <div style="font-size:1.6em;margin-bottom:8px;">📋</div>
                <div style="font-weight:700;font-size:0.95rem;color:#0d1b2a;margin-bottom:4px;">Full Analysis Report</div>
                <div style="color:#8896a8;font-size:0.82rem;margin-bottom:14px;">
                    HTML report with all recommendations, sentiment findings and data quality.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        if agent_state:
            html = generate_html_report(restaurant_name, agent_state, quality_reports)
            st.download_button(
                "⬇️  Download HTML Report",
                data=html.encode("utf-8"),
                file_name=f"menumind_{restaurant_name.replace(' ','_')}_report.html",
                mime="text/html",
                use_container_width=True,
            )
        else:
            st.button("⬇️  Download HTML Report", disabled=True, use_container_width=True,
                      help="Run AI Analysis first to generate a full report.")

    # Recommendations CSV
    with col2:
        st.markdown(
            """<div style="background:#ffffff;border-radius:14px;padding:20px 22px;
                border:1px solid #e8edf4;box-shadow:0 1px 5px rgba(0,0,0,0.04);">
                <div style="font-size:1.6em;margin-bottom:8px;">💡</div>
                <div style="font-weight:700;font-size:0.95rem;color:#0d1b2a;margin-bottom:4px;">Recommendations CSV</div>
                <div style="color:#8896a8;font-size:0.82rem;margin-bottom:14px;">
                    All AI-generated menu recommendations in spreadsheet format.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        recs = agent_state.recommendations if agent_state else []
        if not recs:
            from agent.schemas import Recommendation, MenuAction, Priority
            db_recs_raw = repo.list_recommendations(run_id)
            recs = []
            for r in db_recs_raw:
                try:
                    recs.append(Recommendation(
                        item_id=r.get("item_id"),
                        item_name=r.get("item_name", ""),
                        action=MenuAction(r.get("action", "INSUFFICIENT_EVIDENCE")),
                        priority=Priority(r.get("priority", "low")),
                        confidence_score=r.get("confidence_score", 0.0),
                        reasoning=r.get("reasoning", ""),
                    ))
                except Exception:
                    pass

        if recs:
            csv_bytes = recommendations_to_csv(recs)
            st.download_button(
                "⬇️  Download Recommendations",
                data=csv_bytes,
                file_name=f"menumind_{restaurant_name.replace(' ','_')}_recommendations.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("⬇️  Download Recommendations", disabled=True, use_container_width=True,
                      help="Run AI Analysis first.")

    # Sales Data CSV
    with col3:
        st.markdown(
            """<div style="background:#ffffff;border-radius:14px;padding:20px 22px;
                border:1px solid #e8edf4;box-shadow:0 1px 5px rgba(0,0,0,0.04);">
                <div style="font-size:1.6em;margin-bottom:8px;">📈</div>
                <div style="font-weight:700;font-size:0.95rem;color:#0d1b2a;margin-bottom:4px;">Cleaned Sales Data</div>
                <div style="color:#8896a8;font-size:0.82rem;margin-bottom:14px;">
                    Validated and cleaned sales dataset as processed by MenuMind.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        sales_df = st.session_state.get("sales_df")
        if sales_df is not None:
            buf = io.BytesIO()
            sales_df.to_csv(buf, index=False)
            st.download_button(
                "⬇️  Download Sales CSV",
                data=buf.getvalue(),
                file_name="cleaned_sales.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("⬇️  Download Sales CSV", disabled=True, use_container_width=True,
                      help="Upload sales data first.")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Experiments Summary ───────────────────────────────────────────────
    experiments = repo.list_experiments(run_id)
    if experiments:
        import pandas as pd
        _section("🧪 Experiments Summary")
        df_exp = pd.DataFrame(experiments)
        show_cols = [c for c in ("id", "title", "status", "hypothesis", "baseline_start", "test_start", "test_end", "created_at") if c in df_exp.columns]
        st.dataframe(df_exp[show_cols], use_container_width=True, hide_index=True)

        buf = io.BytesIO()
        df_exp[show_cols].to_csv(buf, index=False)
        st.download_button(
            "⬇️  Download Experiments CSV",
            data=buf.getvalue(),
            file_name="experiments.csv",
            mime="text/csv",
        )

    # ── Data Quality Summary ──────────────────────────────────────────────
    if quality_reports:
        import pandas as pd
        _section("✅ Data Quality Summary")
        q_data = []
        for r in quality_reports:
            q_data.append({
                "File Type": getattr(r, "file_type", "—").capitalize(),
                "Total Records": getattr(r, "total_records", getattr(r, "total_rows", "—")),
                "Accepted": getattr(r, "accepted_records", getattr(r, "accepted_rows", "—")),
                "Rejected": getattr(r, "rejected_records", getattr(r, "rejected_rows", 0)),
                "Quality Score": f"{getattr(r, 'quality_score', 0):.0%}",
            })
        st.dataframe(pd.DataFrame(q_data), use_container_width=True, hide_index=True)

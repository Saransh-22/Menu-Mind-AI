"""
Data-access repository — thin wrappers around raw SQL for each entity.
All external code should use these functions rather than raw SQL.
Each function accepts an optional db_path for testing with isolated databases.
"""
import json
import logging
from typing import Optional

from database.connection import db_session, DATABASE_PATH as DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


def _db(db_path: Optional[str]) -> str:
    return db_path if db_path else DEFAULT_DB_PATH


# ──────────────────────────── Restaurants ────────────────────────────────────

def create_restaurant(name: str, city: str = "", location: str = "",
                      website: str = "", category: str = "",
                      db_path: Optional[str] = None) -> int:
    with db_session(_db(db_path)) as conn:
        cur = conn.execute(
            "INSERT INTO restaurants (name, city, location, website, category) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, city, location, website, category),
        )
        return cur.lastrowid


def get_restaurant(restaurant_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    with db_session(_db(db_path)) as conn:
        row = conn.execute(
            "SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)
        ).fetchone()
        return dict(row) if row else None


def list_restaurants(db_path: Optional[str] = None) -> list[dict]:
    with db_session(_db(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM restaurants ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def find_restaurant_by_name(name: str, city: str = "",
                            db_path: Optional[str] = None) -> Optional[dict]:
    """Find existing restaurant by name (case-insensitive) and city."""
    with db_session(_db(db_path)) as conn:
        clean_name = name.strip()
        clean_city = city.strip()
        if clean_city:
            row = conn.execute(
                "SELECT * FROM restaurants WHERE LOWER(TRIM(name)) = LOWER(?) AND LOWER(TRIM(city)) = LOWER(?) LIMIT 1",
                (clean_name, clean_city),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM restaurants WHERE LOWER(TRIM(name)) = LOWER(?) LIMIT 1",
                (clean_name,),
            ).fetchone()
        return dict(row) if row else None


def search_restaurants(query: str, limit: int = 5,
                       db_path: Optional[str] = None) -> list[dict]:
    """Search existing restaurants matching query substring."""
    with db_session(_db(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM restaurants WHERE LOWER(name) LIKE LOWER(?) ORDER BY name ASC LIMIT ?",
            (f"%{query.strip()}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_or_create_restaurant(name: str, city: str = "", location: str = "",
                            website: str = "", category: str = "",
                            db_path: Optional[str] = None) -> tuple[int, bool]:
    """
    Find existing restaurant by case-insensitive name and city, or create a new one.
    Returns: (restaurant_id, created_flag)
    """
    existing = find_restaurant_by_name(name, city, db_path=db_path)
    if existing:
        return existing["id"], False
    new_id = create_restaurant(
        name=name.strip(),
        city=city.strip(),
        location=location.strip(),
        website=website.strip(),
        category=category.strip(),
        db_path=db_path,
    )
    return new_id, True



# ──────────────────────────── Analysis Runs ──────────────────────────────────

def create_analysis_run(restaurant_id: int, period_start: str = "",
                        period_end: str = "", notes: str = "",
                        db_path: Optional[str] = None) -> int:
    with db_session(_db(db_path)) as conn:
        cur = conn.execute(
            "INSERT INTO analysis_runs (restaurant_id, period_start, period_end, notes) "
            "VALUES (?, ?, ?, ?)",
            (restaurant_id, period_start, period_end, notes),
        )
        return cur.lastrowid


def update_run_status(run_id: int, status: str,
                      data_quality_score: float = None,
                      db_path: Optional[str] = None) -> None:
    with db_session(_db(db_path)) as conn:
        if data_quality_score is not None:
            conn.execute(
                "UPDATE analysis_runs SET status=?, data_quality_score=?, "
                "completed_at=datetime('now') WHERE id=?",
                (status, data_quality_score, run_id),
            )
        else:
            conn.execute(
                "UPDATE analysis_runs SET status=? WHERE id=?",
                (status, run_id),
            )


def get_analysis_run(run_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    with db_session(_db(db_path)) as conn:
        row = conn.execute(
            "SELECT * FROM analysis_runs WHERE id=?", (run_id,)
        ).fetchone()
        return dict(row) if row else None


def list_runs_for_restaurant(restaurant_id: int,
                              db_path: Optional[str] = None) -> list[dict]:
    with db_session(_db(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM analysis_runs WHERE restaurant_id=? "
            "ORDER BY created_at DESC",
            (restaurant_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ──────────────────────────── Data Files ─────────────────────────────────────

def record_data_file(run_id: int, file_type: str, original_name: str,
                     row_count: int, accepted_rows: int, rejected_rows: int,
                     db_path: Optional[str] = None) -> int:
    with db_session(_db(db_path)) as conn:
        cur = conn.execute(
            "INSERT INTO data_files "
            "(run_id, file_type, original_name, row_count, accepted_rows, rejected_rows) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, file_type, original_name, row_count, accepted_rows, rejected_rows),
        )
        return cur.lastrowid


# ──────────────────────────── Recommendations ────────────────────────────────

def save_recommendation(run_id: int, rec: dict,
                        db_path: Optional[str] = None) -> int:
    with db_session(_db(db_path)) as conn:
        cur = conn.execute(
            """INSERT INTO recommendations
               (run_id, item_id, item_name, action, priority, confidence_score,
                reasoning, alternative_actions, expected_benefits, potential_risks,
                missing_information, next_steps, sales_metrics, review_themes,
                profitability, requires_approval, success_metrics)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id,
                rec.get("item_id"),
                rec.get("item_name"),
                rec.get("action"),
                rec.get("priority"),
                rec.get("confidence_score"),
                rec.get("reasoning"),
                json.dumps(rec.get("alternative_actions", [])),
                rec.get("expected_benefits"),
                rec.get("potential_risks"),
                rec.get("missing_information"),
                json.dumps(rec.get("next_steps", [])),
                json.dumps(rec.get("sales_metrics", {})),
                json.dumps(rec.get("review_themes", {})),
                json.dumps(rec.get("profitability", {})),
                int(rec.get("requires_approval", True)),
                rec.get("success_metrics"),
            ),
        )
        return cur.lastrowid


def list_recommendations(run_id: int,
                         db_path: Optional[str] = None) -> list[dict]:
    with db_session(_db(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE run_id=? ORDER BY priority, confidence_score DESC",
            (run_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for field in ("alternative_actions", "next_steps", "sales_metrics",
                          "review_themes", "profitability"):
                if d.get(field):
                    try:
                        d[field] = json.loads(d[field])
                    except Exception:
                        pass
            result.append(d)
        return result


# ──────────────────────────── Approvals ──────────────────────────────────────

def save_approval(recommendation_id: int, decision: str, notes: str = "",
                  db_path: Optional[str] = None) -> int:
    with db_session(_db(db_path)) as conn:
        cur = conn.execute(
            "INSERT INTO approvals (recommendation_id, decision, notes) VALUES (?,?,?)",
            (recommendation_id, decision, notes),
        )
        return cur.lastrowid


def get_approval(recommendation_id: int,
                 db_path: Optional[str] = None) -> Optional[dict]:
    with db_session(_db(db_path)) as conn:
        row = conn.execute(
            "SELECT * FROM approvals WHERE recommendation_id=? ORDER BY decided_at DESC LIMIT 1",
            (recommendation_id,),
        ).fetchone()
        return dict(row) if row else None


# ──────────────────────────── Experiments ────────────────────────────────────

def create_experiment(run_id: int, data: dict,
                      db_path: Optional[str] = None) -> int:
    with db_session(_db(db_path)) as conn:
        cur = conn.execute(
            """INSERT INTO experiments
               (run_id, recommendation_id, title, hypothesis, intervention,
                baseline_start, baseline_end, test_start, test_end,
                success_criteria, guardrail_metrics, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id,
                data.get("recommendation_id"),
                data.get("title"),
                data.get("hypothesis"),
                data.get("intervention"),
                data.get("baseline_start"),
                data.get("baseline_end"),
                data.get("test_start"),
                data.get("test_end"),
                data.get("success_criteria"),
                data.get("guardrail_metrics"),
                data.get("status", "proposed"),
            ),
        )
        return cur.lastrowid


def list_experiments(run_id: int,
                     db_path: Optional[str] = None) -> list[dict]:
    with db_session(_db(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM experiments WHERE run_id=? ORDER BY created_at DESC",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_experiment_status(experiment_id: int, status: str,
                              db_path: Optional[str] = None) -> None:
    with db_session(_db(db_path)) as conn:
        conn.execute(
            "UPDATE experiments SET status=? WHERE id=?", (status, experiment_id)
        )


def save_experiment_result(experiment_id: int, results: list[dict],
                            db_path: Optional[str] = None) -> None:
    with db_session(_db(db_path)) as conn:
        for r in results:
            conn.execute(
                """INSERT INTO experiment_results
                   (experiment_id, metric_name, baseline_value, test_value, change_pct, notes)
                   VALUES (?,?,?,?,?,?)""",
                (
                    experiment_id,
                    r.get("metric_name"),
                    r.get("baseline_value"),
                    r.get("test_value"),
                    r.get("change_pct"),
                    r.get("notes"),
                ),
            )


def get_experiment_results(experiment_id: int,
                            db_path: Optional[str] = None) -> list[dict]:
    with db_session(_db(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM experiment_results WHERE experiment_id=?",
            (experiment_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ──────────────────────────── Retrieval Metadata ─────────────────────────────

def save_retrieval_metadata(run_id: int, source: str, source_url: str,
                             review_count: int, attribution: str = "",
                             limitations: str = "",
                             db_path: Optional[str] = None) -> int:
    with db_session(_db(db_path)) as conn:
        cur = conn.execute(
            """INSERT INTO retrieval_metadata
               (run_id, source, source_url, review_count, attribution, limitations)
               VALUES (?,?,?,?,?,?)""",
            (run_id, source, source_url, review_count, attribution, limitations),
        )
        return cur.lastrowid


def list_retrieval_metadata(run_id: int,
                             db_path: Optional[str] = None) -> list[dict]:
    with db_session(_db(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM retrieval_metadata WHERE run_id=?", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ──────────────────────────── Food Waste ─────────────────────────────────────

def save_waste_record(run_id: int, data: dict,
                      db_path: Optional[str] = None) -> int:
    with db_session(_db(db_path)) as conn:
        cur = conn.execute(
            """INSERT INTO waste_records
               (run_id, ingredient_name, quantity, unit, unit_cost, waste_reason,
                associated_dish, image_item_name, image_confidence, verified_by_user)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, data.get("ingredient_name"), data.get("quantity"),
                data.get("unit", "kg"), data.get("unit_cost"),
                data.get("waste_reason", ""), data.get("associated_dish", ""),
                data.get("image_item_name"), data.get("image_confidence"),
                int(data.get("verified_by_user", True)),
            ),
        )
        return cur.lastrowid


def list_waste_records(run_id: int,
                       db_path: Optional[str] = None) -> list[dict]:
    with db_session(_db(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM waste_records WHERE run_id=? ORDER BY created_at DESC, id DESC",
            (run_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def save_waste_image(run_id: int, original_name: str, mime_type: str,
                     detected_items: list[dict], limitations: list[str],
                     db_path: Optional[str] = None) -> int:
    with db_session(_db(db_path)) as conn:
        cur = conn.execute(
            """INSERT INTO waste_images
               (run_id, original_name, mime_type, detected_items, limitations)
               VALUES (?,?,?,?,?)""",
            (run_id, original_name, mime_type, json.dumps(detected_items),
             json.dumps(limitations)),
        )
        return cur.lastrowid


# ──────────────────────────── AI Conversations & Chat ─────────────────────────

def create_conversation(conv_id: str, restaurant_id: int, run_id: Optional[int] = None,
                        title: str = "New Conversation", db_path: Optional[str] = None) -> str:
    with db_session(_db(db_path)) as conn:
        conn.execute(
            """INSERT INTO ai_conversations (id, restaurant_id, run_id, title)
               VALUES (?, ?, ?, ?)""",
            (conv_id, restaurant_id, run_id, title),
        )
        return conv_id


def list_conversations(restaurant_id: int, db_path: Optional[str] = None) -> list[dict]:
    with db_session(_db(db_path)) as conn:
        rows = conn.execute(
            """SELECT * FROM ai_conversations
               WHERE restaurant_id = ?
               ORDER BY updated_at DESC, created_at DESC""",
            (restaurant_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_conversation(conv_id: str, db_path: Optional[str] = None) -> Optional[dict]:
    with db_session(_db(db_path)) as conn:
        row = conn.execute(
            "SELECT * FROM ai_conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        return dict(row) if row else None


def update_conversation_title(conv_id: str, title: str, db_path: Optional[str] = None) -> None:
    with db_session(_db(db_path)) as conn:
        conn.execute(
            """UPDATE ai_conversations
               SET title = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (title, conv_id),
        )


def touch_conversation(conv_id: str, db_path: Optional[str] = None) -> None:
    with db_session(_db(db_path)) as conn:
        conn.execute(
            "UPDATE ai_conversations SET updated_at = datetime('now') WHERE id = ?",
            (conv_id,),
        )


def delete_conversation(conv_id: str, db_path: Optional[str] = None) -> None:
    with db_session(_db(db_path)) as conn:
        conn.execute("DELETE FROM ai_messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM ai_generated_assets WHERE conversation_id = ?", (conv_id,))
        conn.execute("UPDATE ai_agent_runs SET conversation_id = NULL WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM ai_conversations WHERE id = ?", (conv_id,))


def save_message(msg_id: str, conversation_id: str, role: str, content: str,
                 attachments: Optional[list] = None, agent_metadata: Optional[dict] = None,
                 db_path: Optional[str] = None) -> str:
    with db_session(_db(db_path)) as conn:
        conn.execute(
            """INSERT INTO ai_messages
               (id, conversation_id, role, content, attachments, agent_metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                msg_id,
                conversation_id,
                role,
                content,
                json.dumps(attachments or []),
                json.dumps(agent_metadata or {}),
            ),
        )
        conn.execute(
            "UPDATE ai_conversations SET updated_at = datetime('now') WHERE id = ?",
            (conversation_id,),
        )
        return msg_id


def list_messages(conversation_id: str, limit: int = 100, offset: int = 0,
                  db_path: Optional[str] = None) -> list[dict]:
    with db_session(_db(db_path)) as conn:
        rows = conn.execute(
            """SELECT * FROM ai_messages
               WHERE conversation_id = ?
               ORDER BY created_at ASC, rowid ASC
               LIMIT ? OFFSET ?""",
            (conversation_id, limit, offset),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("attachments"):
                try:
                    d["attachments"] = json.loads(d["attachments"])
                except Exception:
                    d["attachments"] = []
            else:
                d["attachments"] = []
            if d.get("agent_metadata"):
                try:
                    d["agent_metadata"] = json.loads(d["agent_metadata"])
                except Exception:
                    d["agent_metadata"] = {}
            else:
                d["agent_metadata"] = {}
            results.append(d)
        return results


# ──────────────────────────── AI Generated Assets ───────────────────────────

def save_generated_asset(asset_id: str, conversation_id: Optional[str],
                         restaurant_id: int, asset_type: str, title: str,
                         content: Optional[dict | list | str] = None,
                         image_url: Optional[str] = None,
                         status: str = "draft", db_path: Optional[str] = None) -> str:
    content_str = json.dumps(content) if isinstance(content, (dict, list)) else content
    with db_session(_db(db_path)) as conn:
        conn.execute(
            """INSERT INTO ai_generated_assets
               (id, conversation_id, restaurant_id, asset_type, title, content, image_url, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (asset_id, conversation_id, restaurant_id, asset_type, title, content_str, image_url, status),
        )
        return asset_id


def get_generated_asset(asset_id: str, db_path: Optional[str] = None) -> Optional[dict]:
    with db_session(_db(db_path)) as conn:
        row = conn.execute(
            "SELECT * FROM ai_generated_assets WHERE id = ?", (asset_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get("content"):
            try:
                d["content"] = json.loads(d["content"])
            except Exception:
                pass
        return d


def list_generated_assets(restaurant_id: int, asset_type: Optional[str] = None,
                          db_path: Optional[str] = None) -> list[dict]:
    with db_session(_db(db_path)) as conn:
        if asset_type:
            rows = conn.execute(
                """SELECT * FROM ai_generated_assets
                   WHERE restaurant_id = ? AND asset_type = ?
                   ORDER BY created_at DESC""",
                (restaurant_id, asset_type),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM ai_generated_assets
                   WHERE restaurant_id = ?
                   ORDER BY created_at DESC""",
                (restaurant_id,),
            ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("content"):
                try:
                    d["content"] = json.loads(d["content"])
                except Exception:
                    pass
            results.append(d)
        return results


def update_asset_status(asset_id: str, status: str, content: Optional[dict | list | str] = None,
                        image_url: Optional[str] = None, db_path: Optional[str] = None) -> None:
    with db_session(_db(db_path)) as conn:
        updates = ["status = ?", "updated_at = datetime('now')"]
        params = [status]
        if content is not None:
            updates.append("content = ?")
            params.append(json.dumps(content) if isinstance(content, (dict, list)) else content)
        if image_url is not None:
            updates.append("image_url = ?")
            params.append(image_url)
        params.append(asset_id)
        conn.execute(
            f"UPDATE ai_generated_assets SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )


def log_agent_run(run_id: str, conversation_id: Optional[str], restaurant_id: int,
                  agent_name: str, intent: Optional[str], tools_invoked: list[str],
                  status: str = "completed", execution_time_ms: int = 0,
                  db_path: Optional[str] = None) -> str:
    with db_session(_db(db_path)) as conn:
        conn.execute(
            """INSERT INTO ai_agent_runs
               (id, conversation_id, restaurant_id, agent_name, intent, tools_invoked, status, execution_time_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                conversation_id,
                restaurant_id,
                agent_name,
                intent,
                json.dumps(tools_invoked),
                status,
                execution_time_ms,
            ),
        )
        return run_id

"""Team mission creation, matching, collaboration, submission, and settlement."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from database import begin_write_transaction, get_db_connection
from experiment_events import record_event
from rewards import grant_agent_reward
from routes_shared import utc_now_iso_z
from team_matching import assign_roles, build_agent_features, form_team_groups
from team_scoring import (
    contribution_score_for_message,
    contribution_score_for_submission,
    score_team_results,
)


class TeamMissionError(ValueError):
    pass


class TeamMissionNotFound(TeamMissionError):
    pass


DEFAULT_TEAM_REWARDS = {"1": 80, "2": 40, "3": 20}
DEFAULT_REQUIRED_ROLES = ["lead", "analyst", "risk", "scribe"]


def _row_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None and not isinstance(row, dict) else (row or {})


def _model_dump(data: Any) -> dict[str, Any]:
    if data is None:
        return {}
    if isinstance(data, dict):
        return data
    if hasattr(data, "model_dump"):
        return data.model_dump()
    return dict(data)


def _json_dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception as exc:
        raise TeamMissionError(f"Invalid datetime: {value}") from exc


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_key(key: Optional[str], title: str, prefix: str) -> str:
    candidate = (key or "").strip().lower()
    if not candidate:
        candidate = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        candidate = f"{candidate[:44] or prefix}-{uuid.uuid4().hex[:8]}"
    candidate = re.sub(r"[^a-z0-9_\-]+", "-", candidate).strip("-_")
    if not candidate:
        raise TeamMissionError(f"{prefix}_key is required")
    return candidate[:90]


def _derive_status(start_at: str, due_at: str, requested_status: Optional[str] = None) -> str:
    if requested_status:
        normalized = requested_status.strip().lower()
        if normalized not in {"upcoming", "active", "settled", "canceled"}:
            raise TeamMissionError("Unsupported mission status")
        return normalized
    now = datetime.now(timezone.utc)
    if _parse_dt(start_at) > now:
        return "upcoming"
    return "active"


def _serialize_mission(row: Any, team_count: Optional[int] = None, participant_count: Optional[int] = None) -> dict[str, Any]:
    data = _row_dict(row)
    if not data:
        return {}
    data["required_roles"] = _json_loads(data.get("required_roles_json"), [])
    data["rules"] = _json_loads(data.get("rules_json"), {})
    if team_count is not None:
        data["team_count"] = team_count
    if participant_count is not None:
        data["participant_count"] = participant_count
    return data


def _serialize_team(row: Any, member_count: Optional[int] = None) -> dict[str, Any]:
    data = _row_dict(row)
    if member_count is not None:
        data["member_count"] = member_count
    return data


def refresh_mission_statuses(cursor: Any) -> None:
    now = utc_now_iso_z()
    cursor.execute(
        """
        UPDATE team_missions
        SET status = 'active', updated_at = ?
        WHERE status = 'upcoming' AND start_at <= ? AND submission_due_at > ?
        """,
        (now, now, now),
    )


def _load_mission(cursor: Any, *, mission_key: Optional[str] = None, mission_id: Optional[int] = None) -> dict[str, Any]:
    if mission_id is not None:
        cursor.execute("SELECT * FROM team_missions WHERE id = ?", (mission_id,))
    else:
        cursor.execute("SELECT * FROM team_missions WHERE mission_key = ?", (mission_key,))
    row = cursor.fetchone()
    if not row:
        raise TeamMissionNotFound("Team mission not found")
    return _row_dict(row)


def _load_team(cursor: Any, *, team_key: Optional[str] = None, team_id: Optional[int] = None) -> dict[str, Any]:
    if team_id is not None:
        cursor.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
    else:
        cursor.execute("SELECT * FROM teams WHERE team_key = ?", (team_key,))
    row = cursor.fetchone()
    if not row:
        raise TeamMissionNotFound("Team not found")
    return _row_dict(row)


def _resolve_variant(cursor: Any, experiment_key: Optional[str], agent_id: int, requested_variant: Optional[str]) -> Optional[str]:
    variant_key = (requested_variant or "").strip() or None
    if not experiment_key:
        return variant_key

    cursor.execute(
        """
        SELECT variant_key
        FROM experiment_assignments
        WHERE experiment_key = ? AND unit_type = 'agent' AND unit_id = ?
        """,
        (experiment_key, agent_id),
    )
    row = cursor.fetchone()
    if row:
        return row["variant_key"]
    if variant_key:
        cursor.execute(
            """
            INSERT INTO experiment_assignments
            (experiment_key, unit_type, unit_id, variant_key, assignment_reason, metadata_json, created_at)
            VALUES (?, 'agent', ?, ?, 'team_mission_join', ?, ?)
            """,
            (experiment_key, agent_id, variant_key, _json_dumps({"source": "team_mission_join"}), utc_now_iso_z()),
        )
    return variant_key


def create_team_mission(data: Any, created_by_agent_id: Optional[int] = None) -> dict[str, Any]:
    payload = _model_dump(data)
    title = (payload.get("title") or "").strip()
    if not title:
        raise TeamMissionError("title is required")
    market = (payload.get("market") or "").strip()
    if not market:
        raise TeamMissionError("market is required")

    now_dt = datetime.now(timezone.utc)
    start_at = _iso(_parse_dt(payload.get("start_at")) or now_dt)
    due_at = _iso(_parse_dt(payload.get("submission_due_at")) or (now_dt + timedelta(hours=24)))
    if _parse_dt(due_at) <= _parse_dt(start_at):
        raise TeamMissionError("submission_due_at must be after start_at")

    team_size_min = int(payload.get("team_size_min") or 2)
    team_size_max = int(payload.get("team_size_max") or max(2, team_size_min))
    if team_size_min <= 0 or team_size_max < team_size_min:
        raise TeamMissionError("Invalid team size settings")

    mission_key = _normalize_key(payload.get("mission_key"), title, "mission")
    required_roles = payload.get("required_roles_json") or DEFAULT_REQUIRED_ROLES
    rules = payload.get("rules_json") or {}
    if isinstance(required_roles, str):
        required_roles = _json_loads(required_roles, DEFAULT_REQUIRED_ROLES)
    if isinstance(rules, str):
        rules = _json_loads(rules, {})
    if "team_reward_points" not in rules and rules.get("grant_rewards", True):
        rules["team_reward_points"] = DEFAULT_TEAM_REWARDS
    if "contribution_reward_per_point" not in rules and rules.get("grant_rewards", True):
        rules["contribution_reward_per_point"] = 1

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        begin_write_transaction(cursor)
        cursor.execute(
            """
            INSERT INTO team_missions
            (mission_key, title, description, market, symbol, mission_type, status,
             team_size_min, team_size_max, assignment_mode, required_roles_json,
             start_at, submission_due_at, rules_json, experiment_key, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mission_key,
                title,
                payload.get("description"),
                market,
                (payload.get("symbol") or "").strip() or None,
                (payload.get("mission_type") or "consensus").strip(),
                _derive_status(start_at, due_at, payload.get("status")),
                team_size_min,
                team_size_max,
                (payload.get("assignment_mode") or "random").strip().lower(),
                _json_dumps(required_roles),
                start_at,
                due_at,
                _json_dumps(rules),
                (payload.get("experiment_key") or "").strip() or None,
                utc_now_iso_z(),
                utc_now_iso_z(),
            ),
        )
        mission_id = cursor.lastrowid
        record_event(
            "team_mission_created",
            actor_agent_id=created_by_agent_id,
            object_type="team_mission",
            object_id=mission_id,
            market=market,
            experiment_key=(payload.get("experiment_key") or "").strip() or None,
            metadata={"mission_key": mission_key, "assignment_mode": payload.get("assignment_mode") or "random"},
            cursor=cursor,
        )
        conn.commit()
        mission = _load_mission(cursor, mission_id=mission_id)
        return _serialize_mission(mission, team_count=0, participant_count=0)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_team_missions(status: Optional[str] = None, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        refresh_mission_statuses(cursor)
        conn.commit()
        params: list[Any] = []
        where = "1=1"
        if status:
            where = "tm.status = ?"
            params.append(status)
        cursor.execute(f"SELECT COUNT(*) AS total FROM team_missions tm WHERE {where}", params)
        total = cursor.fetchone()["total"]
        cursor.execute(
            f"""
            SELECT tm.*,
                   (SELECT COUNT(*) FROM teams t WHERE t.mission_id = tm.id) AS team_count,
                   (SELECT COUNT(*) FROM team_mission_participants tmp WHERE tmp.mission_id = tm.id) AS participant_count
            FROM team_missions tm
            WHERE {where}
            ORDER BY tm.start_at DESC, tm.id DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        )
        return {
            "missions": [
                _serialize_mission(row, row["team_count"], row["participant_count"])
                for row in cursor.fetchall()
            ],
            "total": total,
        }
    finally:
        conn.close()


def get_team_mission(mission_key: str) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        refresh_mission_statuses(cursor)
        conn.commit()
        mission = _load_mission(cursor, mission_key=mission_key)
        cursor.execute("SELECT COUNT(*) AS count FROM teams WHERE mission_id = ?", (mission["id"],))
        team_count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) AS count FROM team_mission_participants WHERE mission_id = ?", (mission["id"],))
        participant_count = cursor.fetchone()["count"]
        result = _serialize_mission(mission, team_count=team_count, participant_count=participant_count)
        result["teams"] = get_mission_teams(mission_key)["teams"]
        return result
    finally:
        conn.close()


def join_team_mission(mission_key: str, agent_id: int, data: Any = None) -> dict[str, Any]:
    payload = _model_dump(data)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        begin_write_transaction(cursor)
        refresh_mission_statuses(cursor)
        mission = _load_mission(cursor, mission_key=mission_key)
        if mission["status"] not in {"upcoming", "active"}:
            raise TeamMissionError("Mission is not joinable")
        variant_key = _resolve_variant(cursor, mission.get("experiment_key"), agent_id, payload.get("variant_key"))
        cursor.execute(
            """
            SELECT *
            FROM team_mission_participants
            WHERE mission_id = ? AND agent_id = ?
            """,
            (mission["id"], agent_id),
        )
        existing = cursor.fetchone()
        if existing:
            conn.commit()
            return {"joined": False, "idempotent": True, "participant": dict(existing)}
        cursor.execute(
            """
            INSERT INTO team_mission_participants
            (mission_id, agent_id, status, variant_key, joined_at)
            VALUES (?, ?, 'joined', ?, ?)
            """,
            (mission["id"], agent_id, variant_key, utc_now_iso_z()),
        )
        participant_id = cursor.lastrowid
        record_event(
            "team_mission_joined",
            actor_agent_id=agent_id,
            object_type="team_mission_participant",
            object_id=participant_id,
            market=mission["market"],
            experiment_key=mission.get("experiment_key"),
            variant_key=variant_key,
            metadata={"mission_key": mission["mission_key"], "mission_id": mission["id"]},
            cursor=cursor,
        )
        conn.commit()
        cursor.execute("SELECT * FROM team_mission_participants WHERE id = ?", (participant_id,))
        return {"joined": True, "idempotent": False, "participant": dict(cursor.fetchone())}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _insert_team(
    cursor: Any,
    mission: dict[str, Any],
    *,
    team_key: str,
    name: str,
    formation_method: str,
    variant_key: Optional[str],
) -> int:
    now = utc_now_iso_z()
    cursor.execute(
        """
        INSERT INTO teams
        (mission_id, team_key, name, status, formation_method, variant_key, created_at, updated_at)
        VALUES (?, ?, ?, 'active', ?, ?, ?, ?)
        """,
        (mission["id"], team_key, name, formation_method, variant_key, now, now),
    )
    team_id = cursor.lastrowid
    record_event(
        "team_created",
        object_type="team",
        object_id=team_id,
        market=mission["market"],
        experiment_key=mission.get("experiment_key"),
        variant_key=variant_key,
        metadata={"mission_key": mission["mission_key"], "team_key": team_key, "formation_method": formation_method},
        cursor=cursor,
    )
    return team_id


def _insert_team_member(
    cursor: Any,
    mission: dict[str, Any],
    team: dict[str, Any],
    agent_id: int,
    *,
    role: Optional[str],
    variant_key: Optional[str],
) -> Optional[int]:
    cursor.execute(
        """
        SELECT id
        FROM team_members
        WHERE team_id = ? AND agent_id = ?
        """,
        (team["id"], agent_id),
    )
    if cursor.fetchone():
        return None
    cursor.execute(
        """
        INSERT INTO team_members (team_id, agent_id, role, status, joined_at)
        VALUES (?, ?, ?, 'active', ?)
        """,
        (team["id"], agent_id, role, utc_now_iso_z()),
    )
    member_id = cursor.lastrowid
    record_event(
        "team_joined",
        actor_agent_id=agent_id,
        object_type="team_member",
        object_id=member_id,
        market=mission["market"],
        experiment_key=mission.get("experiment_key"),
        variant_key=variant_key,
        metadata={"mission_key": mission["mission_key"], "team_key": team["team_key"], "role": role},
        cursor=cursor,
    )
    if role:
        record_event(
            "team_role_assigned",
            actor_agent_id=agent_id,
            object_type="team_member",
            object_id=member_id,
            market=mission["market"],
            experiment_key=mission.get("experiment_key"),
            variant_key=variant_key,
            metadata={"mission_key": mission["mission_key"], "team_key": team["team_key"], "role": role},
            cursor=cursor,
        )
    return member_id


def create_team_for_mission(mission_key: str, agent_id: int, data: Any = None) -> dict[str, Any]:
    payload = _model_dump(data)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        begin_write_transaction(cursor)
        mission = _load_mission(cursor, mission_key=mission_key)
        if mission["status"] not in {"upcoming", "active"}:
            raise TeamMissionError("Mission is not accepting teams")
        requested_key = payload.get("team_key")
        team_name = (payload.get("name") or f"{mission['title']} Team").strip()
        team_key = _normalize_key(requested_key, team_name, "team")
        role = (payload.get("role") or "").strip() or None
        variant_key = _resolve_variant(cursor, mission.get("experiment_key"), agent_id, payload.get("variant_key"))
        cursor.execute(
            """
            SELECT id
            FROM team_mission_participants
            WHERE mission_id = ? AND agent_id = ?
            """,
            (mission["id"], agent_id),
        )
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO team_mission_participants
                (mission_id, agent_id, status, variant_key, joined_at)
                VALUES (?, ?, 'joined', ?, ?)
                """,
                (mission["id"], agent_id, variant_key, utc_now_iso_z()),
            )
        team_id = _insert_team(
            cursor,
            mission,
            team_key=team_key,
            name=team_name,
            formation_method="manual",
            variant_key=variant_key,
        )
        team = _load_team(cursor, team_id=team_id)
        _insert_team_member(cursor, mission, team, agent_id, role=role, variant_key=variant_key)
        conn.commit()
        return get_team(team_key)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def join_team(team_key: str, agent_id: int, data: Any = None) -> dict[str, Any]:
    payload = _model_dump(data)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        begin_write_transaction(cursor)
        team = _load_team(cursor, team_key=team_key)
        mission = _load_mission(cursor, mission_id=team["mission_id"])
        if mission["status"] not in {"upcoming", "active"}:
            raise TeamMissionError("Mission is not joinable")
        cursor.execute("SELECT COUNT(*) AS count FROM team_members WHERE team_id = ? AND status = 'active'", (team["id"],))
        if cursor.fetchone()["count"] >= int(mission["team_size_max"]):
            raise TeamMissionError("Team is full")
        role = (payload.get("role") or "").strip() or None
        variant_key = _resolve_variant(cursor, mission.get("experiment_key"), agent_id, payload.get("variant_key") or team.get("variant_key"))
        cursor.execute(
            """
            SELECT id
            FROM team_mission_participants
            WHERE mission_id = ? AND agent_id = ?
            """,
            (mission["id"], agent_id),
        )
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO team_mission_participants
                (mission_id, agent_id, status, variant_key, joined_at)
                VALUES (?, ?, 'joined', ?, ?)
                """,
                (mission["id"], agent_id, variant_key, utc_now_iso_z()),
            )
        member_id = _insert_team_member(cursor, mission, team, agent_id, role=role, variant_key=variant_key)
        conn.commit()
        return {"joined": member_id is not None, "idempotent": member_id is None, "team": get_team(team_key)}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def auto_form_teams(mission_key: str, assignment_mode: Optional[str] = None) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        begin_write_transaction(cursor)
        mission = _load_mission(cursor, mission_key=mission_key)
        mode = (assignment_mode or mission.get("assignment_mode") or "random").strip().lower()
        cursor.execute("SELECT COUNT(*) AS count FROM teams WHERE mission_id = ?", (mission["id"],))
        if cursor.fetchone()["count"]:
            conn.commit()
            return get_mission_teams(mission_key)

        cursor.execute(
            """
            SELECT agent_id, variant_key
            FROM team_mission_participants
            WHERE mission_id = ? AND status = 'joined'
            ORDER BY joined_at, id
            """,
            (mission["id"],),
        )
        participants = [dict(row) for row in cursor.fetchall()]
        if len(participants) < int(mission["team_size_min"]):
            raise TeamMissionError("Not enough participants to form teams")

        agent_ids = [item["agent_id"] for item in participants]
        features = build_agent_features(cursor, agent_ids)
        variant_by_agent = {item["agent_id"]: item.get("variant_key") for item in participants}
        team_size = max(int(mission["team_size_min"]), min(int(mission["team_size_max"]), int(mission["team_size_max"])))
        groups = form_team_groups(features, assignment_mode=mode, team_size=team_size, mission_key=mission["mission_key"])
        required_roles = _json_loads(mission.get("required_roles_json"), DEFAULT_REQUIRED_ROLES) or DEFAULT_REQUIRED_ROLES
        formed_team_ids: list[int] = []

        for index, group in enumerate(groups, start=1):
            team_key = _normalize_key(f"{mission['mission_key']}-{mode}-{index}", f"{mission['title']} {index}", "team")
            team_variant = variant_by_agent.get(group[0]["agent_id"])
            team_id = _insert_team(
                cursor,
                mission,
                team_key=team_key,
                name=f"{mission['title']} Team {index}",
                formation_method=mode,
                variant_key=team_variant,
            )
            team = _load_team(cursor, team_id=team_id)
            roles = assign_roles(group, required_roles)
            for member in group:
                _insert_team_member(
                    cursor,
                    mission,
                    team,
                    member["agent_id"],
                    role=roles.get(member["agent_id"]),
                    variant_key=variant_by_agent.get(member["agent_id"]),
                )
            formed_team_ids.append(team_id)

        conn.commit()
        result = get_mission_teams(mission_key)
        result["formed_team_ids"] = formed_team_ids
        result["assignment_mode"] = mode
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_mission_teams(mission_key: str) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        mission = _load_mission(cursor, mission_key=mission_key)
        cursor.execute(
            """
            SELECT t.*, COUNT(tm.id) AS member_count
            FROM teams t
            LEFT JOIN team_members tm ON tm.team_id = t.id AND tm.status = 'active'
            WHERE t.mission_id = ?
            GROUP BY t.id
            ORDER BY t.created_at, t.id
            """,
            (mission["id"],),
        )
        teams = [_serialize_team(row, row["member_count"]) for row in cursor.fetchall()]
        return {"mission": _serialize_mission(mission), "teams": teams}
    finally:
        conn.close()


def get_team(team_key: str) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        team = _load_team(cursor, team_key=team_key)
        mission = _load_mission(cursor, mission_id=team["mission_id"])
        cursor.execute(
            """
            SELECT tm.*, a.name AS agent_name
            FROM team_members tm
            JOIN agents a ON a.id = tm.agent_id
            WHERE tm.team_id = ?
            ORDER BY tm.joined_at, tm.id
            """,
            (team["id"],),
        )
        members = [dict(row) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT tmsg.*, a.name AS agent_name
            FROM team_messages tmsg
            JOIN agents a ON a.id = tmsg.agent_id
            WHERE tmsg.team_id = ?
            ORDER BY tmsg.created_at DESC, tmsg.id DESC
            LIMIT 100
            """,
            (team["id"],),
        )
        messages = [dict(row) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT ts.*, a.name AS submitted_by_agent_name
            FROM team_submissions ts
            JOIN agents a ON a.id = ts.submitted_by_agent_id
            WHERE ts.team_id = ?
            ORDER BY ts.created_at DESC, ts.id DESC
            """,
            (team["id"],),
        )
        submissions = [dict(row) for row in cursor.fetchall()]
        result = _serialize_team(team, len(members))
        result["mission"] = _serialize_mission(mission)
        result["members"] = members
        result["messages"] = messages
        result["submissions"] = submissions
        return result
    finally:
        conn.close()


def _assert_team_member(cursor: Any, team_id: int, agent_id: int) -> None:
    cursor.execute(
        """
        SELECT id
        FROM team_members
        WHERE team_id = ? AND agent_id = ? AND status = 'active'
        """,
        (team_id, agent_id),
    )
    if not cursor.fetchone():
        raise TeamMissionError("Agent must be a team member")


def link_signal_to_team(team_key: str, agent_id: int, data: Any) -> dict[str, Any]:
    payload = _model_dump(data)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        begin_write_transaction(cursor)
        team = _load_team(cursor, team_key=team_key)
        mission = _load_mission(cursor, mission_id=team["mission_id"])
        _assert_team_member(cursor, team["id"], agent_id)
        message = _insert_team_message(
            cursor,
            mission,
            team,
            agent_id,
            signal_id=payload.get("signal_id"),
            message_type=payload.get("message_type") or "signal",
            content=payload.get("content"),
            metadata=payload.get("metadata_json") or {},
        )
        conn.commit()
        return message
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _insert_team_message(
    cursor: Any,
    mission: dict[str, Any],
    team: dict[str, Any],
    agent_id: int,
    *,
    signal_id: Optional[int],
    message_type: str,
    content: Optional[str],
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    cursor.execute(
        """
        INSERT INTO team_messages
        (team_id, agent_id, signal_id, message_type, content, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (team["id"], agent_id, signal_id, message_type, content, _json_dumps(metadata or {}), utc_now_iso_z()),
    )
    message_id = cursor.lastrowid
    record_event(
        "team_signal_linked",
        actor_agent_id=agent_id,
        object_type="team_message",
        object_id=message_id,
        market=mission["market"],
        experiment_key=mission.get("experiment_key"),
        variant_key=team.get("variant_key"),
        metadata={"mission_key": mission["mission_key"], "team_key": team["team_key"], "signal_id": signal_id, "message_type": message_type},
        cursor=cursor,
    )
    return {
        "id": message_id,
        "team_id": team["id"],
        "agent_id": agent_id,
        "signal_id": signal_id,
        "message_type": message_type,
        "content": content,
    }


def _team_for_signal_binding(cursor: Any, *, mission_key: Optional[str], team_key: Optional[str], agent_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    if team_key:
        team = _load_team(cursor, team_key=team_key)
        mission = _load_mission(cursor, mission_id=team["mission_id"])
        _assert_team_member(cursor, team["id"], agent_id)
        if mission_key and mission["mission_key"] != mission_key:
            raise TeamMissionError("team_key does not belong to mission_key")
        return mission, team

    if not mission_key:
        raise TeamMissionError("mission_key or team_key is required")
    mission = _load_mission(cursor, mission_key=mission_key)
    cursor.execute(
        """
        SELECT t.*
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.id
        WHERE t.mission_id = ? AND tm.agent_id = ? AND tm.status = 'active'
        ORDER BY t.created_at DESC, t.id DESC
        LIMIT 1
        """,
        (mission["id"], agent_id),
    )
    team_row = cursor.fetchone()
    if not team_row:
        raise TeamMissionError("Agent is not assigned to a team for this mission")
    return mission, dict(team_row)


def record_team_message_from_signal(
    cursor: Any,
    *,
    mission_key: Optional[str],
    team_key: Optional[str],
    agent_id: int,
    signal_id: int,
    message_type: str,
    content: Optional[str],
) -> Optional[dict[str, Any]]:
    if not mission_key and not team_key:
        return None
    mission, team = _team_for_signal_binding(cursor, mission_key=mission_key, team_key=team_key, agent_id=agent_id)
    return _insert_team_message(
        cursor,
        mission,
        team,
        agent_id,
        signal_id=signal_id,
        message_type=message_type,
        content=content,
        metadata={"source": "signal_publish"},
    )


def record_team_reply_from_parent_signal(
    cursor: Any,
    *,
    parent_signal_id: int,
    reply_id: int,
    agent_id: int,
    content: str,
) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT DISTINCT tmsg.team_id, t.*
        FROM team_messages tmsg
        JOIN teams t ON t.id = tmsg.team_id
        WHERE tmsg.signal_id = ?
        """,
        (parent_signal_id,),
    )
    teams = [dict(row) for row in cursor.fetchall()]
    recorded = []
    for team in teams:
        mission = _load_mission(cursor, mission_id=team["mission_id"])
        recorded.append(_insert_team_message(
            cursor,
            mission,
            team,
            agent_id,
            signal_id=parent_signal_id,
            message_type="reply",
            content=content,
            metadata={"reply_id": reply_id, "source": "signal_reply"},
        ))
    return recorded


def submit_team(team_key: str, agent_id: int, data: Any) -> dict[str, Any]:
    payload = _model_dump(data)
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()
    if not title or not content:
        raise TeamMissionError("title and content are required")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        begin_write_transaction(cursor)
        team = _load_team(cursor, team_key=team_key)
        mission = _load_mission(cursor, mission_id=team["mission_id"])
        _assert_team_member(cursor, team["id"], agent_id)
        cursor.execute(
            """
            INSERT INTO team_submissions
            (mission_id, team_id, submitted_by_agent_id, title, content, prediction_json, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mission["id"],
                team["id"],
                agent_id,
                title,
                content,
                _json_dumps(payload.get("prediction_json")),
                payload.get("confidence"),
                utc_now_iso_z(),
            ),
        )
        submission_id = cursor.lastrowid
        record_event(
            "team_submission_created",
            actor_agent_id=agent_id,
            object_type="team_submission",
            object_id=submission_id,
            market=mission["market"],
            experiment_key=mission.get("experiment_key"),
            variant_key=team.get("variant_key"),
            metadata={"mission_key": mission["mission_key"], "team_key": team["team_key"], "confidence": payload.get("confidence")},
            cursor=cursor,
        )
        submission = {
            "id": submission_id,
            "mission_id": mission["id"],
            "team_id": team["id"],
            "submitted_by_agent_id": agent_id,
            "title": title,
            "content": content,
            "confidence": payload.get("confidence"),
        }
        _score_submission_contribution(cursor, mission, team, submission)
        conn.commit()
        return submission
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_team_submissions(team_key: str) -> dict[str, Any]:
    team = get_team(team_key)
    return {"team": team, "submissions": team.get("submissions", [])}


def _contribution_exists(cursor: Any, source_type: str, source_id: Any) -> bool:
    cursor.execute(
        """
        SELECT id
        FROM team_contributions
        WHERE source_type = ? AND source_id = ?
        LIMIT 1
        """,
        (source_type, str(source_id)),
    )
    return cursor.fetchone() is not None


def _insert_contribution(
    cursor: Any,
    mission: dict[str, Any],
    team: dict[str, Any],
    agent_id: int,
    *,
    source_type: str,
    source_id: Any,
    contribution_type: str,
    contribution_score: float,
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[int]:
    if _contribution_exists(cursor, source_type, source_id):
        return None
    cursor.execute(
        """
        INSERT INTO team_contributions
        (mission_id, team_id, agent_id, source_type, source_id, contribution_type,
         contribution_score, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mission["id"],
            team["id"],
            agent_id,
            source_type,
            str(source_id),
            contribution_type,
            contribution_score,
            _json_dumps(metadata or {}),
            utc_now_iso_z(),
        ),
    )
    contribution_id = cursor.lastrowid
    record_event(
        "team_contribution_scored",
        actor_agent_id=agent_id,
        object_type="team_contribution",
        object_id=contribution_id,
        market=mission["market"],
        experiment_key=mission.get("experiment_key"),
        variant_key=team.get("variant_key"),
        metadata={"mission_key": mission["mission_key"], "team_key": team["team_key"], "score": contribution_score, "contribution_type": contribution_type},
        cursor=cursor,
    )
    return contribution_id


def _score_message_contribution(cursor: Any, mission: dict[str, Any], team: dict[str, Any], message: dict[str, Any]) -> Optional[int]:
    score = contribution_score_for_message(message)
    return _insert_contribution(
        cursor,
        mission,
        team,
        message["agent_id"],
        source_type="team_message",
        source_id=message["id"],
        contribution_type=message["message_type"],
        contribution_score=score,
        metadata={"signal_id": message.get("signal_id")},
    )


def _score_submission_contribution(cursor: Any, mission: dict[str, Any], team: dict[str, Any], submission: dict[str, Any]) -> Optional[int]:
    score = contribution_score_for_submission(submission)
    return _insert_contribution(
        cursor,
        mission,
        team,
        submission["submitted_by_agent_id"],
        source_type="team_submission",
        source_id=submission["id"],
        contribution_type="submission",
        contribution_score=score,
        metadata={"confidence": submission.get("confidence")},
    )


def score_team_contributions(mission_key: Optional[str] = None) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    inserted = 0
    try:
        begin_write_transaction(cursor)
        mission_filter = ""
        params: list[Any] = []
        if mission_key:
            mission_filter = "WHERE tm.mission_key = ?"
            params.append(mission_key)
        cursor.execute(
            f"""
            SELECT
                tmsg.id AS message_id,
                tmsg.team_id,
                tmsg.agent_id,
                tmsg.signal_id,
                tmsg.message_type,
                tmsg.content,
                t.team_key,
                t.variant_key,
                tm.id AS mission_id,
                tm.mission_key,
                tm.market,
                tm.experiment_key
            FROM team_messages tmsg
            JOIN teams t ON t.id = tmsg.team_id
            JOIN team_missions tm ON tm.id = t.mission_id
            {mission_filter}
            ORDER BY tmsg.id
            """,
            params,
        )
        for row in cursor.fetchall():
            data = dict(row)
            mission = {"id": data["mission_id"], "mission_key": data["mission_key"], "market": data["market"], "experiment_key": data["experiment_key"]}
            team = {"id": data["team_id"], "team_key": data["team_key"], "variant_key": data["variant_key"]}
            message = {
                "id": data["message_id"],
                "agent_id": data["agent_id"],
                "signal_id": data["signal_id"],
                "message_type": data["message_type"],
                "content": data["content"],
            }
            if _score_message_contribution(cursor, mission, team, message):
                inserted += 1

        cursor.execute(
            f"""
            SELECT ts.*, t.team_key, t.variant_key, tm.mission_key, tm.market, tm.experiment_key
            FROM team_submissions ts
            JOIN teams t ON t.id = ts.team_id
            JOIN team_missions tm ON tm.id = ts.mission_id
            {mission_filter}
            ORDER BY ts.id
            """,
            params,
        )
        for row in cursor.fetchall():
            data = dict(row)
            mission = {"id": data["mission_id"], "mission_key": data["mission_key"], "market": data["market"], "experiment_key": data["experiment_key"]}
            team = {"id": data["team_id"], "team_key": data["team_key"], "variant_key": data["variant_key"]}
            submission = {
                "id": data["id"],
                "submitted_by_agent_id": data["submitted_by_agent_id"],
                "content": data["content"],
                "confidence": data["confidence"],
            }
            if _score_submission_contribution(cursor, mission, team, submission):
                inserted += 1

        conn.commit()
        return {"inserted": inserted}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _fetch_settlement_inputs(cursor: Any, mission_id: int):
    cursor.execute("SELECT * FROM teams WHERE mission_id = ? ORDER BY id", (mission_id,))
    teams = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT tm.*, a.name AS agent_name
        FROM team_members tm
        JOIN agents a ON a.id = tm.agent_id
        WHERE tm.team_id IN (SELECT id FROM teams WHERE mission_id = ?)
        ORDER BY tm.team_id, tm.id
        """,
        (mission_id,),
    )
    members_by_team: dict[int, list[dict[str, Any]]] = {}
    member_rows = [dict(row) for row in cursor.fetchall()]
    features_by_agent = {item["agent_id"]: item for item in build_agent_features(cursor, [row["agent_id"] for row in member_rows])}
    for member in member_rows:
        member.update(features_by_agent.get(member["agent_id"], {}))
        members_by_team.setdefault(member["team_id"], []).append(member)

    cursor.execute("SELECT * FROM team_submissions WHERE mission_id = ? ORDER BY id", (mission_id,))
    submissions_by_team: dict[int, list[dict[str, Any]]] = {}
    for row in cursor.fetchall():
        item = dict(row)
        submissions_by_team.setdefault(item["team_id"], []).append(item)

    cursor.execute("SELECT * FROM team_contributions WHERE mission_id = ? ORDER BY id", (mission_id,))
    contributions_by_team: dict[int, list[dict[str, Any]]] = {}
    for row in cursor.fetchall():
        item = dict(row)
        contributions_by_team.setdefault(item["team_id"], []).append(item)

    return teams, members_by_team, submissions_by_team, contributions_by_team


def _team_reward_for_rank(rules: dict[str, Any], rank: int) -> int:
    rewards = rules.get("team_reward_points", DEFAULT_TEAM_REWARDS)
    if isinstance(rewards, list):
        return int(rewards[rank - 1]) if rank - 1 < len(rewards) else 0
    if isinstance(rewards, dict):
        return int(rewards.get(str(rank), rewards.get(rank, 0)) or 0)
    return 0


def settle_team_mission(mission_key: str, *, force: bool = False) -> dict[str, Any]:
    score_team_contributions(mission_key)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        begin_write_transaction(cursor)
        mission = _load_mission(cursor, mission_key=mission_key)
        if mission["status"] == "settled" and not force:
            conn.commit()
            return get_team_mission_leaderboard(mission_key)
        if force:
            cursor.execute("DELETE FROM team_results WHERE mission_id = ?", (mission["id"],))

        teams, members_by_team, submissions_by_team, contributions_by_team = _fetch_settlement_inputs(cursor, mission["id"])
        results = score_team_results(mission, teams, members_by_team, submissions_by_team, contributions_by_team)
        now = utc_now_iso_z()

        for result in results:
            cursor.execute(
                """
                INSERT INTO team_results
                (mission_id, team_id, return_pct, prediction_score, quality_score,
                 consensus_gain, final_score, rank, metrics_json, settled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mission["id"],
                    result["team_id"],
                    result["return_pct"],
                    result["prediction_score"],
                    result["quality_score"],
                    result["consensus_gain"],
                    result["final_score"],
                    result["rank"],
                    result["metrics_json"],
                    now,
                ),
            )

        rules = _json_loads(mission.get("rules_json"), {}) or {}
        if rules.get("grant_rewards", True):
            for result in results:
                team_reward = _team_reward_for_rank(rules, result["rank"])
                for member in members_by_team.get(result["team_id"], []):
                    if team_reward > 0:
                        grant_agent_reward(
                            member["agent_id"],
                            team_reward,
                            f"team_mission_rank_{result['rank']}",
                            source_type="team_mission_team",
                            source_id=result["team_id"],
                            experiment_key=mission.get("experiment_key"),
                            metadata={"mission_key": mission["mission_key"], "team_id": result["team_id"], "rank": result["rank"]},
                            cursor=cursor,
                        )
                        record_event(
                            "team_reward_granted",
                            actor_agent_id=member["agent_id"],
                            object_type="team_result",
                            object_id=result["team_id"],
                            market=mission["market"],
                            experiment_key=mission.get("experiment_key"),
                            metadata={"mission_key": mission["mission_key"], "reward_type": "team_rank", "points": team_reward, "rank": result["rank"]},
                            cursor=cursor,
                        )

            contribution_multiplier = int(rules.get("contribution_reward_per_point") or 0)
            if contribution_multiplier > 0:
                cursor.execute("SELECT * FROM team_contributions WHERE mission_id = ?", (mission["id"],))
                for contribution in cursor.fetchall():
                    points = int(round(float(contribution["contribution_score"] or 0) * contribution_multiplier))
                    if points <= 0:
                        continue
                    grant_agent_reward(
                        contribution["agent_id"],
                        points,
                        "team_mission_contribution",
                        source_type="team_contribution",
                        source_id=contribution["id"],
                        experiment_key=mission.get("experiment_key"),
                        metadata={"mission_key": mission["mission_key"], "contribution_id": contribution["id"]},
                        cursor=cursor,
                    )
                    record_event(
                        "team_reward_granted",
                        actor_agent_id=contribution["agent_id"],
                        object_type="team_contribution",
                        object_id=contribution["id"],
                        market=mission["market"],
                        experiment_key=mission.get("experiment_key"),
                        metadata={"mission_key": mission["mission_key"], "reward_type": "contribution", "points": points},
                        cursor=cursor,
                    )

        cursor.execute("UPDATE teams SET status = 'settled', updated_at = ? WHERE mission_id = ?", (now, mission["id"]))
        cursor.execute("UPDATE team_missions SET status = 'settled', settled_at = ?, updated_at = ? WHERE id = ?", (now, now, mission["id"]))
        record_event(
            "team_mission_settled",
            object_type="team_mission",
            object_id=mission["id"],
            market=mission["market"],
            experiment_key=mission.get("experiment_key"),
            metadata={"mission_key": mission["mission_key"], "team_count": len(teams)},
            cursor=cursor,
        )
        conn.commit()
        return get_team_mission_leaderboard(mission_key)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_team_mission_leaderboard(mission_key: str) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        mission = _load_mission(cursor, mission_key=mission_key)
        cursor.execute(
            """
            SELECT tr.*, t.team_key, t.name AS team_name,
                   (SELECT COUNT(*) FROM team_members tm WHERE tm.team_id = t.id AND tm.status = 'active') AS member_count,
                   (SELECT COUNT(*) FROM team_submissions ts WHERE ts.team_id = t.id) AS submission_count,
                   (SELECT COUNT(*) FROM team_contributions tc WHERE tc.team_id = t.id) AS contribution_count
            FROM team_results tr
            JOIN teams t ON t.id = tr.team_id
            WHERE tr.mission_id = ?
            ORDER BY COALESCE(tr.rank, 999999), tr.final_score DESC, tr.id
            """,
            (mission["id"],),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        if rows:
            return {"mission": _serialize_mission(mission), "leaderboard": rows, "provisional": False}

        teams, members_by_team, submissions_by_team, contributions_by_team = _fetch_settlement_inputs(cursor, mission["id"])
        provisional = score_team_results(mission, teams, members_by_team, submissions_by_team, contributions_by_team)
        team_by_id = {team["id"]: team for team in teams}
        for row in provisional:
            row["team_key"] = team_by_id.get(row["team_id"], {}).get("team_key")
            row["team_name"] = team_by_id.get(row["team_id"], {}).get("name")
            row["member_count"] = len(members_by_team.get(row["team_id"], []))
            row["submission_count"] = len(submissions_by_team.get(row["team_id"], []))
            row["contribution_count"] = len(contributions_by_team.get(row["team_id"], []))
        return {"mission": _serialize_mission(mission), "leaderboard": provisional, "provisional": True}
    finally:
        conn.close()


def settle_due_team_missions(limit: int = 20) -> list[dict[str, Any]]:
    now = utc_now_iso_z()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        refresh_mission_statuses(cursor)
        conn.commit()
        cursor.execute(
            """
            SELECT mission_key
            FROM team_missions
            WHERE status = 'active' AND submission_due_at <= ?
            ORDER BY submission_due_at ASC
            LIMIT ?
            """,
            (now, max(1, min(limit, 100))),
        )
        mission_keys = [row["mission_key"] for row in cursor.fetchall()]
    finally:
        conn.close()
    return [settle_team_mission(key) for key in mission_keys]


def form_due_team_missions(limit: int = 20) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        refresh_mission_statuses(cursor)
        conn.commit()
        cursor.execute(
            """
            SELECT mission_key
            FROM team_missions tm
            WHERE tm.status = 'active'
              AND NOT EXISTS (SELECT 1 FROM teams t WHERE t.mission_id = tm.id)
              AND (SELECT COUNT(*) FROM team_mission_participants tmp WHERE tmp.mission_id = tm.id) >= tm.team_size_min
            ORDER BY tm.start_at ASC
            LIMIT ?
            """,
            (max(1, min(limit, 100)),),
        )
        mission_keys = [row["mission_key"] for row in cursor.fetchall()]
    finally:
        conn.close()
    formed = []
    for key in mission_keys:
        try:
            formed.append(auto_form_teams(key))
        except TeamMissionError:
            continue
    return formed


def get_agent_team_missions(agent_id: int) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        refresh_mission_statuses(cursor)
        conn.commit()
        cursor.execute(
            """
            SELECT tm.*, t.team_key, t.name AS team_name, memb.role,
                   (SELECT COUNT(*) FROM teams count_t WHERE count_t.mission_id = tm.id) AS team_count,
                   (SELECT COUNT(*) FROM team_mission_participants tmp WHERE tmp.mission_id = tm.id) AS participant_count
            FROM team_missions tm
            LEFT JOIN team_mission_participants tmp ON tmp.mission_id = tm.id AND tmp.agent_id = ?
            LEFT JOIN team_members memb ON memb.agent_id = ? AND memb.status = 'active'
            LEFT JOIN teams t ON t.id = memb.team_id AND t.mission_id = tm.id
            WHERE tmp.agent_id IS NOT NULL OR memb.agent_id IS NOT NULL
            ORDER BY tm.status = 'active' DESC, tm.start_at DESC, tm.id DESC
            """,
            (agent_id, agent_id),
        )
        missions = []
        for row in cursor.fetchall():
            item = _serialize_mission(row, row["team_count"], row["participant_count"])
            item["team_key"] = row["team_key"]
            item["team_name"] = row["team_name"]
            item["role"] = row["role"]
            missions.append(item)
        return {"missions": missions}
    finally:
        conn.close()

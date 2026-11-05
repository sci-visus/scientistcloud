#!/usr/bin/env python3
"""Mongo helpers for the portal administrator dashboard.

Invoked by includes/portal_admin_store.php. Reads one JSON command on stdin
and writes one JSON object on stdout. Connection settings come from the
environment (MONGO_URL, PORTAL_DB_NAME), not from the command body.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pymongo import MongoClient


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _parse_time(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _gb_to_bytes(doc: dict) -> int:
    meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}

    def positive(val: Any) -> Optional[float]:
        try:
            if val is None:
                return None
            number = float(val)
            return number if number > 0 else None
        except (TypeError, ValueError):
            return None

    for src in (doc, meta):
        for key in ("data_size", "total_size"):
            gb = positive(src.get(key))
            if gb is not None:
                return int(gb * (1024 ** 3))
    for src in (doc, meta):
        for key in ("raw_size", "total_size_bytes", "file_size", "size_bytes"):
            raw = positive(src.get(key))
            if raw is not None:
                return int(raw)
    return 0


def _owner_email(doc: dict) -> str:
    for key in ("user_email", "user", "owner"):
        value = doc.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return ""


def _is_public(doc: dict) -> bool:
    value = doc.get("is_public")
    if value is None and isinstance(doc.get("metadata"), dict):
        value = doc["metadata"].get("is_public")
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "public")
    return bool(value)


def _client():
    url = os.environ.get("MONGO_URL") or ""
    name = os.environ.get("PORTAL_DB_NAME") or ""
    if not url or not name:
        raise RuntimeError("MONGO_URL and PORTAL_DB_NAME are required")
    client = MongoClient(url, serverSelectionTimeoutMS=8000)
    return client, client[name]


def _ensure_indexes(db) -> None:
    db["portal_usage"].create_index("stay_id", unique=True)
    db["portal_usage"].create_index([("user_email", 1), ("started_at", -1)])
    db["portal_usage"].create_index("dataset_uuid")
    db["portal_usage"].create_index("dashboard_id")
    db["portal_allocations"].create_index(
        [("subject_type", 1), ("subject_id", 1)], unique=True
    )
    db["portal_workflows"].create_index("team_uuid", unique=True)


def _stay_public(doc: dict) -> dict:
    return {
        "stay_id": doc.get("stay_id"),
        "user_email": doc.get("user_email"),
        "dataset_id": doc.get("dataset_id"),
        "dataset_uuid": doc.get("dataset_uuid"),
        "dataset_name": doc.get("dataset_name"),
        "dashboard_id": doc.get("dashboard_id"),
        "started_at": _iso(doc.get("started_at")),
        "loaded_at": _iso(doc.get("loaded_at")),
        "load_ms": doc.get("load_ms"),
        "ended_at": _iso(doc.get("ended_at")),
        "dwell_ms": doc.get("dwell_ms"),
        "last_seen_at": _iso(doc.get("last_seen_at")),
    }


def _close_open_stays(db, email: str, now: datetime) -> None:
    cursor = db["portal_usage"].find({"user_email": email, "ended_at": None})
    for doc in cursor:
        started = doc.get("started_at") or now
        if isinstance(started, datetime) and started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        dwell = max(0, int((now - started).total_seconds() * 1000))
        db["portal_usage"].update_one(
            {"_id": doc["_id"]},
            {"$set": {"ended_at": now, "dwell_ms": dwell, "last_seen_at": now}},
        )


def usage_start(db, cmd: dict) -> dict:
    email = (cmd.get("user_email") or "").strip().lower()
    if not email:
        raise RuntimeError("user_email is required")
    now = _utcnow()
    _close_open_stays(db, email, now)
    stay_id = str(uuid.uuid4())
    doc = {
        "stay_id": stay_id,
        "user_email": email,
        "dataset_id": cmd.get("dataset_id") or "",
        "dataset_uuid": cmd.get("dataset_uuid") or "",
        "dataset_name": cmd.get("dataset_name") or "",
        "dashboard_id": None,
        "started_at": now,
        "loaded_at": None,
        "load_ms": None,
        "ended_at": None,
        "dwell_ms": None,
        "last_seen_at": now,
    }
    db["portal_usage"].insert_one(doc)
    return {"stay_id": stay_id, "started_at": _iso(now)}


def _owned_stay(db, email: str, stay_id: str) -> Optional[dict]:
    if not stay_id:
        return None
    return db["portal_usage"].find_one({"stay_id": stay_id, "user_email": email})


def usage_dashboard(db, cmd: dict) -> dict:
    email = (cmd.get("user_email") or "").strip().lower()
    stay = _owned_stay(db, email, cmd.get("stay_id") or "")
    if not stay:
        raise RuntimeError("Stay not found")
    if stay.get("ended_at") is not None:
        return {"stay_id": stay.get("stay_id"), "closed": True}
    now = _utcnow()
    dashboard_id = (cmd.get("dashboard_id") or "").strip()
    started = stay.get("started_at") or now
    if isinstance(started, datetime) and started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    load_ms = cmd.get("load_ms")
    try:
        load_ms = int(load_ms) if load_ms is not None else int((now - started).total_seconds() * 1000)
    except (TypeError, ValueError):
        load_ms = int((now - started).total_seconds() * 1000)
    load_ms = max(0, load_ms)
    updates = {
        "dashboard_id": dashboard_id or stay.get("dashboard_id"),
        "last_seen_at": now,
    }
    if cmd.get("dataset_uuid"):
        updates["dataset_uuid"] = cmd.get("dataset_uuid")
    if cmd.get("dataset_id"):
        updates["dataset_id"] = cmd.get("dataset_id")
    if cmd.get("dataset_name"):
        updates["dataset_name"] = cmd.get("dataset_name")
    if stay.get("loaded_at") is None:
        updates["loaded_at"] = now
        updates["load_ms"] = load_ms
    db["portal_usage"].update_one({"_id": stay["_id"]}, {"$set": updates})
    return {"stay_id": stay.get("stay_id"), "dashboard_id": updates["dashboard_id"], "load_ms": updates.get("load_ms", stay.get("load_ms"))}


def usage_heartbeat(db, cmd: dict) -> dict:
    email = (cmd.get("user_email") or "").strip().lower()
    stay = _owned_stay(db, email, cmd.get("stay_id") or "")
    if not stay or stay.get("ended_at") is not None:
        return {"ok": False}
    now = _utcnow()
    db["portal_usage"].update_one({"_id": stay["_id"]}, {"$set": {"last_seen_at": now}})
    return {"ok": True, "last_seen_at": _iso(now)}


def usage_end(db, cmd: dict) -> dict:
    email = (cmd.get("user_email") or "").strip().lower()
    stay = _owned_stay(db, email, cmd.get("stay_id") or "")
    if not stay:
        return {"ok": False}
    if stay.get("ended_at") is not None:
        return {"ok": True, "dwell_ms": stay.get("dwell_ms"), "already_closed": True}
    now = _utcnow()
    started = stay.get("started_at") or now
    if isinstance(started, datetime) and started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    dwell = max(0, int((now - started).total_seconds() * 1000))
    db["portal_usage"].update_one(
        {"_id": stay["_id"]},
        {"$set": {"ended_at": now, "dwell_ms": dwell, "last_seen_at": now}},
    )
    return {"ok": True, "dwell_ms": dwell}


def usage_query(db, cmd: dict) -> dict:
    query: dict[str, Any] = {}
    email = (cmd.get("user_email") or "").strip().lower()
    dataset = (cmd.get("dataset") or "").strip()
    dashboard = (cmd.get("dashboard") or "").strip()
    if email:
        query["user_email"] = email
    if dataset:
        query["$or"] = [
            {"dataset_uuid": dataset},
            {"dataset_id": dataset},
            {"dataset_name": dataset},
        ]
    if dashboard:
        query["dashboard_id"] = dashboard
    start = _parse_time(cmd.get("from"))
    end = _parse_time(cmd.get("to"))
    if start or end:
        bounds = {}
        if start:
            bounds["$gte"] = start
        if end:
            bounds["$lte"] = end
        query["started_at"] = bounds
    limit = cmd.get("limit") or 100
    try:
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        limit = 100
    rows = list(db["portal_usage"].find(query).sort("started_at", -1).limit(limit))
    by_user: dict[str, dict] = {}
    by_dataset: dict[str, dict] = {}
    by_dashboard: dict[str, dict] = {}
    for doc in rows:
        dwell = int(doc.get("dwell_ms") or 0)
        user = doc.get("user_email") or ""
        bucket = by_user.setdefault(user, {"user_email": user, "opens": 0, "dwell_ms": 0})
        bucket["opens"] += 1
        bucket["dwell_ms"] += dwell
        ds_key = doc.get("dataset_uuid") or doc.get("dataset_id") or doc.get("dataset_name") or ""
        ds = by_dataset.setdefault(ds_key, {
            "dataset_uuid": doc.get("dataset_uuid") or "",
            "dataset_name": doc.get("dataset_name") or "",
            "opens": 0,
            "dwell_ms": 0,
        })
        ds["opens"] += 1
        ds["dwell_ms"] += dwell
        dash = doc.get("dashboard_id") or "(none)"
        dash_bucket = by_dashboard.setdefault(dash, {"dashboard_id": dash, "opens": 0, "dwell_ms": 0})
        dash_bucket["opens"] += 1
        dash_bucket["dwell_ms"] += dwell
    return {
        "rows": [_stay_public(doc) for doc in rows],
        "by_user": sorted(by_user.values(), key=lambda item: item["dwell_ms"], reverse=True),
        "by_dataset": sorted(by_dataset.values(), key=lambda item: item["dwell_ms"], reverse=True),
        "by_dashboard": sorted(by_dashboard.values(), key=lambda item: item["dwell_ms"], reverse=True),
    }


def _allocation_public(doc: dict) -> dict:
    return {
        "subject_type": doc.get("subject_type"),
        "subject_id": doc.get("subject_id"),
        "space_bytes": doc.get("space_bytes"),
        "seat_limit": doc.get("seat_limit"),
        "usd_per_gb_month": doc.get("usd_per_gb_month"),
        "usd_per_viewer_hour": doc.get("usd_per_viewer_hour"),
        "updated_at": _iso(doc.get("updated_at")),
    }


def allocations_list(db, _cmd: dict) -> dict:
    docs = list(db["portal_allocations"].find().sort([("subject_type", 1), ("subject_id", 1)]))
    return {"allocations": [_allocation_public(doc) for doc in docs]}


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    return float(value)


def allocation_save(db, cmd: dict) -> dict:
    subject_type = (cmd.get("subject_type") or "").strip().lower()
    subject_id = (cmd.get("subject_id") or "").strip()
    if subject_type not in ("user", "team") or not subject_id:
        raise RuntimeError("subject_type and subject_id are required")
    if subject_type == "user":
        subject_id = subject_id.lower()
    doc = {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "space_bytes": _optional_int(cmd.get("space_bytes")),
        "seat_limit": _optional_int(cmd.get("seat_limit")),
        "usd_per_gb_month": _optional_float(cmd.get("usd_per_gb_month")),
        "usd_per_viewer_hour": _optional_float(cmd.get("usd_per_viewer_hour")),
        "updated_at": _utcnow(),
    }
    db["portal_allocations"].update_one(
        {"subject_type": subject_type, "subject_id": subject_id},
        {"$set": doc},
        upsert=True,
    )
    return {"allocation": _allocation_public(doc)}


def _dataset_groups(db) -> tuple[dict, dict, list]:
    by_user: dict[str, dict] = {}
    by_team: dict[str, dict] = {}
    docs = []
    cursor = db["visstoredatas"].find(
        {},
        {
            "uuid": 1,
            "name": 1,
            "user": 1,
            "user_email": 1,
            "owner": 1,
            "team_uuid": 1,
            "team_id": 1,
            "is_public": 1,
            "metadata.is_public": 1,
            "data_size": 1,
            "total_size": 1,
            "raw_size": 1,
            "total_size_bytes": 1,
            "file_size": 1,
            "size_bytes": 1,
            "shared_with": 1,
        },
    )
    for doc in cursor:
        docs.append(doc)
        nbytes = _gb_to_bytes(doc)
        owner = _owner_email(doc)
        if owner:
            bucket = by_user.setdefault(owner, {"user_email": owner, "bytes": 0, "datasets": 0})
            bucket["bytes"] += nbytes
            bucket["datasets"] += 1
        team = doc.get("team_uuid") or doc.get("team_id") or ""
        if isinstance(team, str) and team:
            tb = by_team.setdefault(team, {"team_uuid": team, "bytes": 0, "datasets": 0})
            tb["bytes"] += nbytes
            tb["datasets"] += 1
    return by_user, by_team, docs


def storage_summary(db, _cmd: dict) -> dict:
    by_user, by_team, _docs = _dataset_groups(db)
    teams = {}
    for team in db["teams"].find({}, {"uuid": 1, "team_name": 1, "emails": 1, "owner": 1}):
        team_uuid = team.get("uuid") or ""
        if team_uuid:
            teams[team_uuid] = team.get("team_name") or team_uuid
    rows_team = []
    for team_uuid, bucket in by_team.items():
        bucket["team_name"] = teams.get(team_uuid, "")
        rows_team.append(bucket)
    return {
        "users": sorted(by_user.values(), key=lambda item: item["bytes"], reverse=True),
        "teams": sorted(rows_team, key=lambda item: item["bytes"], reverse=True),
    }


def space_check(db, cmd: dict) -> dict:
    # Upload size is not capped. Large datasets are the product.
    return {"ok": True}


def seat_check(db, cmd: dict) -> dict:
    team_uuid = (cmd.get("team_uuid") or "").strip()
    emails = cmd.get("emails") or []
    if not isinstance(emails, list):
        emails = []
    unique = []
    seen = set()
    for item in emails:
        if not isinstance(item, str):
            continue
        mail = item.strip().lower()
        if mail and mail not in seen:
            seen.add(mail)
            unique.append(mail)
    alloc = db["portal_allocations"].find_one({
        "subject_type": "team",
        "subject_id": team_uuid,
    }) if team_uuid else None
    if not alloc or alloc.get("seat_limit") is None:
        return {"ok": True, "seats": len(unique)}
    limit = int(alloc["seat_limit"])
    if len(unique) > limit:
        return {
            "ok": False,
            "seats": len(unique),
            "seat_limit": limit,
            "message": f"This team is at its seat limit ({limit} users).",
        }
    return {"ok": True, "seats": len(unique), "seat_limit": limit}


def access_summary(db, _cmd: dict) -> dict:
    shared_users = set()
    for doc in db["shared_user"].find({}, {"uuid": 1}):
        if doc.get("uuid"):
            shared_users.add(doc["uuid"])
    shared_teams = set()
    for doc in db["shared_team"].find({}, {"uuid": 1}):
        if doc.get("uuid"):
            shared_teams.add(doc["uuid"])
    counts = {"public": 0, "shared": 0, "private": 0}
    listing = []
    _by_user, _by_team, docs = _dataset_groups(db)
    for doc in docs:
        uuid_value = doc.get("uuid") or ""
        if _is_public(doc):
            state = "public"
        elif uuid_value in shared_users or uuid_value in shared_teams or (isinstance(doc.get("shared_with"), list) and doc.get("shared_with")):
            state = "shared"
        else:
            state = "private"
        counts[state] += 1
        if len(listing) < 300:
            listing.append({
                "uuid": uuid_value,
                "name": doc.get("name") or "",
                "owner_email": _owner_email(doc),
                "team_uuid": doc.get("team_uuid") or doc.get("team_id") or "",
                "access": state,
                "bytes": _gb_to_bytes(doc),
            })
    return {"counts": counts, "datasets": listing, "truncated": len(docs) > len(listing)}


def _enabled_list(value: Any) -> list:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def workflows_list(db, _cmd: dict) -> dict:
    teams = []
    for team in db["teams"].find({}, {"uuid": 1, "team_name": 1, "emails": 1, "owner": 1}):
        teams.append({
            "team_uuid": team.get("uuid") or "",
            "team_name": team.get("team_name") or "",
            "emails": team.get("emails") or [],
            "owner": team.get("owner") or "",
        })
    saved = []
    for doc in db["portal_workflows"].find():
        saved.append({
            "team_uuid": doc.get("team_uuid") or "",
            "restricted": bool(doc.get("restricted")),
            "enabled": _enabled_list(doc.get("enabled")),
        })
    return {"teams": teams, "workflows": saved}


def workflow_save(db, cmd: dict) -> dict:
    team_uuid = (cmd.get("team_uuid") or "").strip()
    if not team_uuid:
        raise RuntimeError("team_uuid is required")
    restricted = bool(cmd.get("restricted"))
    enabled = _enabled_list(cmd.get("enabled"))
    doc = {
        "team_uuid": team_uuid,
        "restricted": restricted,
        "enabled": enabled,
        "updated_at": _utcnow(),
    }
    db["portal_workflows"].update_one({"team_uuid": team_uuid}, {"$set": doc}, upsert=True)
    return {"workflow": {"team_uuid": team_uuid, "restricted": restricted, "enabled": enabled}}


def _user_team_uuids(db, email: str) -> list:
    if not email:
        return []
    found = []
    for team in db["teams"].find({}, {"uuid": 1, "emails": 1, "owner": 1}):
        emails = [str(item).strip().lower() for item in (team.get("emails") or []) if isinstance(item, str)]
        owner = str(team.get("owner") or "").strip().lower()
        if email == owner or email in emails:
            if team.get("uuid"):
                found.append(team["uuid"])
    return found


def _workflow_allows(doc: Optional[dict], dashboard_id: str) -> bool:
    if not doc or not doc.get("restricted"):
        return True
    wanted = dashboard_id.strip().lower()
    for item in _enabled_list(doc.get("enabled")):
        if item.lower() == wanted:
            return True
    return False


def dashboard_allowed(db, cmd: dict) -> dict:
    email = (cmd.get("user_email") or "").strip().lower()
    dashboard_id = (cmd.get("dashboard_id") or "").strip()
    dataset_team = (cmd.get("team_uuid") or "").strip()
    if not dashboard_id:
        return {"allowed": True}
    if dataset_team:
        doc = db["portal_workflows"].find_one({"team_uuid": dataset_team})
        allowed = _workflow_allows(doc, dashboard_id)
        return {
            "allowed": allowed,
            "reason": "" if allowed else "This dashboard is turned off for the dataset's team.",
        }
    team_uuids = _user_team_uuids(db, email)
    if not team_uuids:
        return {"allowed": True}
    docs = list(db["portal_workflows"].find({"team_uuid": {"$in": team_uuids}}))
    restricted = [doc for doc in docs if doc.get("restricted")]
    if not restricted or len(restricted) < len(team_uuids):
        return {"allowed": True}
    allowed = any(_workflow_allows(doc, dashboard_id) for doc in restricted)
    return {
        "allowed": allowed,
        "reason": "" if allowed else "This dashboard is turned off for your teams.",
    }


def cost_report(db, cmd: dict) -> dict:
    start = _parse_time(cmd.get("from"))
    end = _parse_time(cmd.get("to"))
    if start is None or end is None:
        raise RuntimeError("from and to are required")
    usage_query = {"started_at": {"$gte": start, "$lt": end}}
    dwell_by_user: dict[str, int] = {}
    for doc in db["portal_usage"].find(usage_query, {"user_email": 1, "dwell_ms": 1}):
        email = (doc.get("user_email") or "").strip().lower()
        if not email:
            continue
        dwell_by_user[email] = dwell_by_user.get(email, 0) + int(doc.get("dwell_ms") or 0)
    by_user, by_team, _docs = _dataset_groups(db)
    allocations = list(db["portal_allocations"].find())
    user_rates = {}
    team_rates = {}
    for alloc in allocations:
        if alloc.get("subject_type") == "user":
            user_rates[alloc.get("subject_id")] = alloc
        elif alloc.get("subject_type") == "team":
            team_rates[alloc.get("subject_id")] = alloc
    rows = []
    emails = set(by_user) | set(dwell_by_user)
    for email in sorted(emails):
        used = by_user.get(email, {}).get("bytes", 0)
        dwell = dwell_by_user.get(email, 0)
        rate = user_rates.get(email) or {}
        gb_rate = rate.get("usd_per_gb_month")
        hour_rate = rate.get("usd_per_viewer_hour")
        space_cost = None
        time_cost = None
        if gb_rate is not None:
            space_cost = (used / (1024 ** 3)) * float(gb_rate)
        if hour_rate is not None:
            time_cost = (dwell / 3600000.0) * float(hour_rate)
        total = None
        if space_cost is not None or time_cost is not None:
            total = (space_cost or 0) + (time_cost or 0)
        rows.append({
            "subject_type": "user",
            "subject_id": email,
            "bytes": used,
            "dwell_ms": dwell,
            "usd_per_gb_month": gb_rate,
            "usd_per_viewer_hour": hour_rate,
            "space_cost": space_cost,
            "time_cost": time_cost,
            "total_cost": total,
        })
    team_names = {}
    for team in db["teams"].find({}, {"uuid": 1, "team_name": 1}):
        if team.get("uuid"):
            team_names[team["uuid"]] = team.get("team_name") or ""
    team_rows = []
    for team_uuid, bucket in by_team.items():
        rate = team_rates.get(team_uuid) or {}
        gb_rate = rate.get("usd_per_gb_month")
        space_cost = None if gb_rate is None else (bucket["bytes"] / (1024 ** 3)) * float(gb_rate)
        team_rows.append({
            "subject_type": "team",
            "subject_id": team_uuid,
            "team_name": team_names.get(team_uuid, ""),
            "bytes": bucket["bytes"],
            "usd_per_gb_month": gb_rate,
            "space_cost": space_cost,
            "total_cost": space_cost,
        })
    return {"from": _iso(start), "to": _iso(end), "users": rows, "teams": team_rows}


OPS = {
    "usage_start": usage_start,
    "usage_dashboard": usage_dashboard,
    "usage_heartbeat": usage_heartbeat,
    "usage_end": usage_end,
    "usage_query": usage_query,
    "allocations_list": allocations_list,
    "allocation_save": allocation_save,
    "storage_summary": storage_summary,
    "space_check": space_check,
    "seat_check": seat_check,
    "access_summary": access_summary,
    "workflows_list": workflows_list,
    "workflow_save": workflow_save,
    "dashboard_allowed": dashboard_allowed,
    "cost_report": cost_report,
}


def main() -> int:
    raw = sys.stdin.read()
    try:
        cmd = json.loads(raw or "{}")
        op = cmd.get("op")
        if op not in OPS:
            raise RuntimeError("Unknown operation")
        client, db = _client()
        try:
            _ensure_indexes(db)
            result = OPS[op](db, cmd)
        finally:
            client.close()
        sys.stdout.write(json.dumps({"ok": True, "result": result}))
        return 0
    except Exception as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.database import get_connection

router = APIRouter(prefix="/status_audit", tags=["status_audit"])

class SystemAuditEntry(BaseModel):
    actor_username: str
    actor_role: str
    action_type: str
    target_module: str
    target_id: Optional[str] = None
    description: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None


def generate_field_diffs(action_type: str, old_val: Optional[dict], new_val: Optional[dict]) -> List[str]:
    diffs = []
    old_val = old_val or {}
    new_val = new_val or {}
    
    ignored_fields = {
        'updated_at', 'changed_at', 'timestamp', 'id', 'created_at', 
        'work_id', 'serial_no', 'language_id', 'is_deleted', 'availability_status',
        'status', 'approved_by', 'approved_at', 'approval_reason', 'total_copies', 'copies'
    }

    if action_type == 'INSERT':
        details = []
        for k in sorted(new_val.keys()):
            if k in ignored_fields:
                continue
            v = new_val.get(k)
            if v is not None and str(v).strip() != "":
                display_key = k.replace('_', ' ').lower()
                details.append(f"{display_key}: \"{v}\"")
        if details:
            return [f"Created record entry initialization state -> {', '.join(details)}"]
        return ["Registered new catalog reference entity data entry."]
        
    if action_type == 'DELETE':
        return ["Removed entry from tracking registry history completely."]

    all_keys = set(old_val.keys()).union(set(new_val.keys()))
    for key in sorted(all_keys):
        if key in ignored_fields:
            continue
        v_old = old_val.get(key)
        v_new = new_val.get(key)
        if v_old != v_new:
            display_key = key.replace('_', ' ').lower()
            diffs.append(f"Changed {display_key} from [{v_old if v_old is not None else 'None'}] to [{v_new if v_new is not None else 'None'}]")
            
    return diffs

@router.get("/system-logs")
def list_system_audit_logs(
    limit: int = 100, 
    offset: int = 0, 
    action_filter: Optional[str] = None,
    actor_filter: Optional[str] = None
):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT 
                id, actor_username, actor_role, user_id, action_type, 
                target_module, target_id, old_value, new_value, 
                device_id, ip_address, change_reason,
                to_char(timezone('Asia/Kolkata', COALESCE(timestamp, NOW())), 'DD-MM-YYYY HH24:MI:SS') as timestamp
            FROM public.system_audit_log
        """
        where_clauses = []
        params = []

        if action_filter:
            where_clauses.append("action_type = %s")
            params.append(action_filter.upper())
        if actor_filter:
            where_clauses.append("actor_username ILIKE %s")
            params.append(f"%{actor_filter}%")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY id DESC"
        
        cursor.execute(query, tuple(params))
        raw_rows = cursor.fetchall()

        normalized_rows = []
        try:
            for r in raw_rows:
                normalized_rows.append(dict(r))
        except (TypeError, ValueError):
            for r in raw_rows:
                normalized_rows.append({
                    "id": r[0], "actor_username": r[1], "actor_role": r[2], "user_id": r[3],
                    "action_type": r[4], "target_module": r[5], "target_id": r[6],
                    "old_value": r[7], "new_value": r[8], "device_id": r[9],
                    "ip_address": r[10], "change_reason": r[11], "timestamp": r[12]
                })

        grouped_logs = []
        skip_indices = set()

        for i, current in enumerate(normalized_rows):
            if i in skip_indices:
                continue

            initial_diffs = generate_field_diffs(current["action_type"], current["old_value"], current["new_value"])
            seen_diffs = set(initial_diffs)
            combined_diffs = list(initial_diffs)
            
            target_id_display = current["target_id"]
            resolved_reason = current["change_reason"]
            
            for j in range(i + 1, min(i + 8, len(normalized_rows))):
                candidate = normalized_rows[j]
                if (current["timestamp"] == candidate["timestamp"] and current["actor_username"] == candidate["actor_username"]):
                    skip_indices.add(j)
                    
                    if candidate["change_reason"] and candidate["change_reason"] not in (
                        "Routine operational adjustment", "New registration initialization sequencing"
                    ):
                        resolved_reason = candidate["change_reason"]
                        
                    more_diffs = generate_field_diffs(candidate["action_type"], candidate["old_value"], candidate["new_value"])
                    for diff_line in more_diffs:
                        if diff_line not in seen_diffs:
                            seen_diffs.add(diff_line)
                            combined_diffs.append(diff_line)
                            
                    if candidate["target_module"] == "items":
                        target_id_display = candidate["target_id"]

            title_context = current["new_value"].get("title") if current["new_value"] else None
            if not title_context and current["old_value"]:
                title_context = current["old_value"].get("title")

            if title_context:
                summary_desc = f"Modified record metrics for asset: \"{title_context}\""
            elif current["action_type"] == "INSERT":
                summary_desc = f"Registered new entity item configuration sequence under index #{target_id_display}"
            else:
                summary_desc = f"Executed configuration update adjustments inside {current['target_module']}"

            if not resolved_reason or resolved_reason in ("Routine operational adjustment", "New registration initialization sequencing"):
                resolved_reason = current["change_reason"] or "New registration initialization sequencing"

            # Strict final output check to ensure no identical strings display twice within the tray panel line mapping index
            final_deduplicated_diffs = []
            final_seen = set()
            for line in combined_diffs:
                if line not in final_seen:
                    final_seen.add(line)
                    final_deduplicated_diffs.append(line)

            grouped_logs.append({
                "id": current["id"],
                "timestamp": current["timestamp"],
                "actor_username": current["actor_username"],
                "actor_role": current["actor_role"],
                "user_id": current["user_id"] or 3,
                "action_type": "CREATE" if current["action_type"] == "INSERT" else current["action_type"],
                "target_id": target_id_display,
                "summary": summary_desc,
                "detailed_diffs": final_deduplicated_diffs,
                "change_reason": resolved_reason,
                "device_id": current["device_id"] or "Desktop Browser Workstation",
                "ip_address": current["ip_address"] or "127.0.0.1"
            })

        return grouped_logs[offset : offset + limit]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
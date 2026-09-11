# scripts/test_ledger_tamper.py

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_connection
from app.services.audit_service import verify_audit_ledger


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f" >>> {title}")
    print("=" * 70)


def run_penetration_test():
    conn = get_connection()
    cur = conn.cursor()

    trigger_disabled = False

    try:
        # -------------------------------------------------------------
        # PHASE 1: Baseline Integrity Verification
        # -------------------------------------------------------------
        print_banner("PHASE 1: Baseline Ledger Verification")
        baseline = verify_audit_ledger()
        print(f"Verifier Baseline: {baseline}")

        is_valid = baseline.get("status") in ("VALID", "VERIFIED", "OK")
        if not is_valid:
            print("❌ Baseline ledger already corrupted. Halting test.")
            return
        print(f"✅ Baseline verified: {baseline.get('inspected_count')} nodes with valid SHA-256 continuity.")

        # -------------------------------------------------------------
        # PHASE 2: Target Selection
        # -------------------------------------------------------------
        print_banner("PHASE 2: Target Selection for Superuser Attack")
        cur.execute("""
            SELECT sequence_id, id, action_type, user_id, justification, record_hash
            FROM audit_activities
            WHERE record_hash IS NOT NULL
            ORDER BY sequence_id DESC
            LIMIT 1
        """)
        target = cur.fetchone()

        if not target:
            print("❌ No audit records found.")
            return

        seq_id, act_id, act_type, user_id, orig_justification, orig_hash = target
        print(f"Selected Target Sequence ID : #{seq_id} (UUID: {act_id})")
        print(f"Target Action               : {act_type}")
        print(f"Target Actor                : {user_id}")
        print(f"Original Record Hash        : {orig_hash}")
        print(f"Original Justification      : {orig_justification}")

        # -------------------------------------------------------------
        # PHASE 3: Rogue Superuser Simulation (Trigger Bypass)
        # -------------------------------------------------------------
        print_banner("PHASE 3: Simulating Rogue DBA (Disabling Triggers & Injecting Tamper)")
        
        # Disabling table triggers to simulate superuser privilege escalation
        cur.execute("ALTER TABLE audit_activities DISABLE TRIGGER ALL;")
        conn.commit()
        trigger_disabled = True
        print("⚠️  [ALERT] PostgreSQL triggers temporarily disabled by superuser.")

        malicious_payload = "MALICIOUS_TAMPER: Bypassed database trigger with superuser privs"
        cur.execute("""
            UPDATE audit_activities
            SET justification = %s
            WHERE sequence_id = %s
        """, (malicious_payload, seq_id))
        conn.commit()
        print(f"⚠️  Injected tampered justification into row #{seq_id} directly.")

        # -------------------------------------------------------------
        # PHASE 4: Execute Tamper-Detection Engine
        # -------------------------------------------------------------
        print_banner("PHASE 4: Cryptographic Tamper-Detection Execution")
        tamper_audit = verify_audit_ledger()
        print(f"Tamper Verification Output:\n{tamper_audit}")

        status = str(tamper_audit.get("status", "")).upper()
        compromised = (
            status in ("COMPROMISED", "INVALID", "TAMPERED", "CORRUPTED", "FAILED")
            or tamper_audit.get("is_valid") is False
            or "compromised_sequence" in tamper_audit
            or "mismatch" in str(tamper_audit).lower()
        )

        if compromised:
            print("\n🛡️  SUCCESS: Cryptographic layer caught the attack despite disabled database triggers!")
            if "compromised_sequence" in tamper_audit:
                print(f"    --> Pinpointed Compromised Sequence: #{tamper_audit.get('compromised_sequence')}")
        else:
            print("\n🚨 CRITICAL ALERT: Tamper test failed! Ledger reported valid despite altered data.")

        # -------------------------------------------------------------
        # INTERACTIVE INSPECTION PAUSE FOR UI VERIFICATION
        # -------------------------------------------------------------
        print("\n" + "=" * 70)
        print(" ⏸️  SIMULATION PAUSED: TAMPER IS CURRENTLY PERSISTED IN DATABASE")
        print("=" * 70)
        print(f"👉 Go to your Athenaeum desktop app now:")
        print(f"   1. Click the refresh (🔄) button on your status pill.")
        print(f"   2. Observe the pill turn RED: [🔴 Compromised: Node #{seq_id}].")
        print(f"   3. Click the pill to test redirection to /audit-trail?highlight={seq_id}.")
        print("=" * 70)
        input("\nPress [ENTER] here once you are done inspecting to revert the attack...")

        # -------------------------------------------------------------
        # PHASE 5: Remediation & Re-Enabling Triggers
        # -------------------------------------------------------------
        print_banner("PHASE 5: Remediation & Security Arming")
        cur.execute("""
            UPDATE audit_activities
            SET justification = %s
            WHERE sequence_id = %s
        """, (orig_justification, seq_id))
        conn.commit()
        print(f"✅ Reverted row #{seq_id} back to original payload.")

        cur.execute("ALTER TABLE audit_activities ENABLE TRIGGER ALL;")
        conn.commit()
        trigger_disabled = False
        print("✅ [ARMED] PostgreSQL immutability triggers re-enabled.")

        clean_audit = verify_audit_ledger()
        print(f"Final Verification Output: {clean_audit}")

        if clean_audit.get("status") == "VALID":
            print("✅ Production ledger integrity fully restored.")
        else:
            print("❌ Ledger continuity did not return to VALID state.")

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        conn.rollback()

    finally:
        # Guarantee trigger re-activation under any failure
        if trigger_disabled:
            try:
                cur.execute("ALTER TABLE audit_activities ENABLE TRIGGER ALL;")
                conn.commit()
                print("🔒 [SAFETY GUARD] Verified immutability triggers re-enabled in finally block.")
            except Exception as trigger_err:
                print(f"🚨 CRITICAL: Could not re-enable triggers: {trigger_err}")
        cur.close()
        conn.close()


if __name__ == "__main__":
    run_penetration_test()
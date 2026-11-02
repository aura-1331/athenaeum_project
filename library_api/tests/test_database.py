"""Database rule tests. They run on a throwaway Postgres, never on Neon."""
import psycopg2
import pytest

from app.database import get_connection

EXPECTED_TABLES = [
    "users", "refresh_tokens", "works", "items", "audit_ledger",
    "audit_activities", "audit_logs", "system_config", "identity_registry",
    "loans", "fines", "review_notes", "correction_requests",
]


@pytest.fixture
def conn():
    connection = get_connection()
    yield connection
    connection.rollback()
    connection.close()


def test_connection_and_audit_context_work(conn):
    cur = conn.cursor()
    cur.execute("SELECT 1")
    assert cur.fetchone()[0] == 1


@pytest.mark.parametrize("table", EXPECTED_TABLES)
def test_core_table_exists(conn, table):
    cur = conn.cursor()
    cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
    assert cur.fetchone()[0] is not None, f"table {table} is missing"


def _insert_ledger_row(cur):
    cur.execute(
        """
        INSERT INTO audit_ledger
            (actor_id, actor_name, actor_role, action_type,
             target_entity, target_id, justification)
        VALUES ('1', 'Test', 'The Chief', 'TEST', 'works', '1', 'unit test')
        RETURNING id
        """
    )
    return cur.fetchone()[0]


def test_audit_ledger_rejects_update(conn):
    cur = conn.cursor()
    row_id = _insert_ledger_row(cur)
    with pytest.raises(psycopg2.Error):
        cur.execute("UPDATE audit_ledger SET justification = 'changed' WHERE id = %s", (row_id,))


def test_audit_ledger_rejects_delete(conn):
    cur = conn.cursor()
    row_id = _insert_ledger_row(cur)
    with pytest.raises(psycopg2.Error):
        cur.execute("DELETE FROM audit_ledger WHERE id = %s", (row_id,))


def test_audit_activities_is_append_only(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT count(*) FROM pg_trigger
        WHERE tgrelid = 'public.audit_activities'::regclass AND NOT tgisinternal
        """
    )
    assert cur.fetchone()[0] >= 2


def _insert_user(cur, role, expires_at):
    cur.execute(
        """
        INSERT INTO users (name, email, role, status, operator_id, expires_at)
        VALUES ('Test User', 'test@example.com', %s, 'APPROVED', 'ATHTEST1', %s)
        """,
        (role, expires_at),
    )


def test_valid_roles_can_be_created(conn):
    cur = conn.cursor()
    _insert_user(cur, "The Keeper", None)


def test_invalid_role_rejected(conn):
    cur = conn.cursor()
    with pytest.raises(psycopg2.errors.CheckViolation):
        _insert_user(cur, "The Emperor", None)


def test_seeker_without_expiry_rejected(conn):
    cur = conn.cursor()
    with pytest.raises(psycopg2.errors.CheckViolation):
        _insert_user(cur, "The Seeker", None)


def test_permanent_role_with_expiry_rejected(conn):
    cur = conn.cursor()
    with pytest.raises(psycopg2.errors.CheckViolation):
        _insert_user(cur, "The Chief", "2099-01-01")

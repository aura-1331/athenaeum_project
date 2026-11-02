--
-- PostgreSQL database dump
--


-- Dumped from database version 17.11 (0bfbbeb)
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


--
-- Name: fuzzystrmatch; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS fuzzystrmatch WITH SCHEMA public;


--
-- Name: EXTENSION fuzzystrmatch; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION fuzzystrmatch IS 'determine similarities and distance between strings';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: user_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_status AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'BANNED',
    'REVOKED'
);


--
-- Name: audit_activities_block_change(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.audit_activities_block_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'audit_activities is append-only: % is not allowed', TG_OP;
END;
$$;


--
-- Name: block_audit_tampering(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.block_audit_tampering() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'SECURITY BREACH: audit_activities records are permanent and append-only.';
END;
$$;


--
-- Name: correction_requests_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.correction_requests_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'correction_requests rows cannot be deleted';
    END IF;

    IF NEW.entity IS DISTINCT FROM OLD.entity
       OR NEW.entity_id IS DISTINCT FROM OLD.entity_id
       OR NEW.requested_by IS DISTINCT FROM OLD.requested_by
       OR NEW.field_names IS DISTINCT FROM OLD.field_names
       OR NEW.requested_at IS DISTINCT FROM OLD.requested_at THEN
        RAISE EXCEPTION 'correction_requests: only status/resolution columns may change';
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: current_user_role(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.current_user_role() RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE r TEXT;
BEGIN
  r := (SELECT role FROM users
        WHERE user_id = current_setting('app.user_id', true)::INTEGER);
  IF r IS NULL THEN
    RAISE EXCEPTION 'Acting user not set or invalid';
  END IF;
  RETURN r;
END;
$$;


--
-- Name: enforce_owner_only_delete(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.enforce_owner_only_delete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF current_user_role() <> 'OWNER' THEN
    RAISE EXCEPTION 'Only OWNER can hard-delete items';
  END IF;
  RETURN OLD;
END;
$$;


--
-- Name: enforce_owner_only_overrides(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.enforce_owner_only_overrides() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE role TEXT;
BEGIN
  role := current_user_role();

  IF OLD.status IN ('GREYED','WITHDRAWN')
     AND NEW.status = 'AVAILABLE'
     AND role <> 'OWNER' THEN
    RAISE EXCEPTION 'Only OWNER can restore items to AVAILABLE';
  END IF;

  RETURN NEW;
END;
$$;


--
-- Name: enforce_status_reason(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.enforce_status_reason() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF NEW.status <> OLD.status
     AND NEW.status IN ('GREYED','WITHDRAWN')
     AND (NEW.status_reason IS NULL OR NEW.status_reason = '') THEN
    RAISE EXCEPTION
      'Changing status from % to % requires a reason',
      OLD.status, NEW.status;
  END IF;
  RETURN NEW;
END;
$$;


--
-- Name: fix_system_audit_log_actor(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fix_system_audit_log_actor() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    v_accession VARCHAR(100);
BEGIN
    IF NEW.actor_username = 'UNKNOWN_ACTOR' OR NEW.actor_username = 'SYSTEM_UNKNOWN' THEN
        SELECT name INTO NEW.actor_username FROM public.users WHERE user_id = 3;
    END IF;

    IF NEW.description LIKE 'Modified master registry metrics%' AND NEW.target_id ~ '^[0-9]+$' THEN
        SELECT accession_no INTO v_accession 
        FROM public.items 
        WHERE serial_no = NEW.target_id::integer;
        
        IF v_accession IS NOT NULL THEN
            NEW.target_id := v_accession;
        END IF;
    END IF;

    RETURN NEW;
END;
$_$;


--
-- Name: generate_next_accession_no(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.generate_next_accession_no(lang_id text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    prefix TEXT;
    next_num INT;
BEGIN
    prefix := UPPER(SUBSTRING(lang_id FROM 1 FOR 2));
    
    SELECT COALESCE(MAX(CAST(SUBSTRING(accession_no FROM 4) AS INT)), 0) + 1
    INTO next_num
    FROM items
    WHERE accession_no LIKE prefix || '-%';
    
    RETURN prefix || '-' || next_num;
END;
$$;


--
-- Name: log_status_change(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.log_status_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE acting_user_id INTEGER;
BEGIN
  acting_user_id := current_setting('app.user_id', true)::INTEGER;
  IF acting_user_id IS NULL THEN
    RAISE EXCEPTION 'app.user_id must be set before updating status';
  END IF;

  INSERT INTO status_history
    (item_id, old_status, new_status, reason, changed_by)
  VALUES
    (NEW.item_id, OLD.status, NEW.status, COALESCE(NEW.status_reason,''), acting_user_id);

  RETURN NEW;
END;
$$;


--
-- Name: next_item_serial_no(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.next_item_serial_no() RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    candidate INTEGER;
BEGIN
    PERFORM pg_advisory_xact_lock(84001602::bigint);

    SELECT
        CASE
            WHEN NOT EXISTS (
                SELECT 1
                FROM public.items
                WHERE serial_no = 1
            )
            THEN 1
            ELSE COALESCE(
                (
                    SELECT MIN(i.serial_no + 1)
                    FROM public.items i
                    LEFT JOIN public.items n
                      ON n.serial_no = i.serial_no + 1
                    WHERE i.serial_no > 0
                      AND i.serial_no < 2147483647
                      AND n.serial_no IS NULL
                ),
                (
                    SELECT COALESCE(MAX(serial_no), 0) + 1
                    FROM public.items
                )
            )
        END
    INTO candidate;

    RETURN candidate;
END;
$$;


--
-- Name: next_work_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.next_work_id() RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    candidate integer;
BEGIN
    LOOP
        candidate := nextval('public.work_id_never_reuse_seq');
        EXIT WHEN NOT EXISTS (
            SELECT 1 FROM public.works WHERE work_id = candidate
        );
    END LOOP;
    RETURN candidate;
END;
$$;


--
-- Name: process_automatic_audit(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.process_automatic_audit() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_actor VARCHAR(100);
    v_role VARCHAR(100);
    v_user_id INTEGER;
    v_target_id VARCHAR(100);
    v_formatted_time VARCHAR(30);
    v_reason TEXT;
    v_device VARCHAR(100);
    v_ip VARCHAR(45);
    v_old_json JSONB := NULL;
    v_new_json JSONB := NULL;
BEGIN

    -- ============================================================
    -- 1. RESOLVE SESSION ACTOR
    -- ============================================================

    v_actor := NULLIF(
        current_setting('request.jwt.claim.username', true),
        ''
    );

    v_role := NULLIF(
        current_setting('request.jwt.claim.role', true),
        ''
    );

    BEGIN
        v_user_id :=
            NULLIF(
                current_setting(
                    'request.jwt.claim.user_id',
                    true
                ),
                ''
            )::integer;
    EXCEPTION
        WHEN OTHERS THEN
            v_user_id := NULL;
    END;

    v_role := COALESCE(v_role, 'SYSTEM');

    -- If username is missing, resolve from user_id.
    IF v_actor IS NULL AND v_user_id IS NOT NULL THEN
        SELECT name
        INTO v_actor
        FROM public.users
        WHERE user_id = v_user_id;
    END IF;

    -- Never allow NULL into the audit table.
    v_actor := COALESCE(v_actor, 'SYSTEM');

    -- ============================================================
    -- 2. REQUEST METADATA
    -- ============================================================

    v_reason := NULLIF(
        current_setting(
            'request.custom.change_reason',
            true
        ),
        ''
    );

    v_reason := COALESCE(
        v_reason,
        'Routine operational adjustment'
    );

    v_device := NULLIF(
        current_setting(
            'request.custom.device_id',
            true
        ),
        ''
    );

    v_device := COALESCE(
        v_device,
        'Desktop Browser Workstation'
    );

    v_ip := NULLIF(
        current_setting(
            'request.custom.ip_address',
            true
        ),
        ''
    );

    v_ip := COALESCE(
        v_ip,
        '127.0.0.1'
    );

    -- ============================================================
    -- 3. TARGET ID
    -- ============================================================

    IF TG_TABLE_NAME = 'works' THEN

        IF TG_OP = 'DELETE' THEN
            v_target_id := OLD.work_id::text;
        ELSE
            v_target_id := NEW.work_id::text;
        END IF;

    ELSIF TG_TABLE_NAME = 'items' THEN

        IF TG_OP = 'DELETE' THEN
            v_target_id := OLD.accession_no::text;
        ELSE
            v_target_id := NEW.accession_no::text;
        END IF;

    ELSIF TG_TABLE_NAME = 'authority_records' THEN

        IF TG_OP = 'DELETE' THEN
            v_target_id := OLD.authority_code::text;
        ELSE
            v_target_id := NEW.authority_code::text;
        END IF;

    ELSIF TG_TABLE_NAME = 'authority_variants' THEN

        IF TG_OP = 'DELETE' THEN
            v_target_id := OLD.variant_id::text;
        ELSE
            v_target_id := NEW.variant_id::text;
        END IF;

    ELSIF TG_TABLE_NAME = 'work_authorities' THEN

        IF TG_OP = 'DELETE' THEN
            v_target_id := OLD.work_authority_id::text;
        ELSE
            v_target_id := NEW.work_authority_id::text;
        END IF;

    ELSE

        BEGIN
            IF TG_OP = 'DELETE' THEN
                v_target_id := OLD.id::text;
            ELSE
                v_target_id := NEW.id::text;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                v_target_id := 'SYSTEM';
        END;

    END IF;

    -- ============================================================
    -- 4. CAPTURE OLD / NEW STATE
    -- ============================================================

    IF TG_OP = 'UPDATE' THEN

        v_old_json := to_jsonb(OLD);
        v_new_json := to_jsonb(NEW);

    ELSIF TG_OP = 'INSERT' THEN

        v_new_json := to_jsonb(NEW);

    ELSIF TG_OP = 'DELETE' THEN

        v_old_json := to_jsonb(OLD);

    END IF;

    -- ============================================================
    -- 5. IST DISPLAY TIME
    -- ============================================================

    v_formatted_time :=
        to_char(
            timezone('Asia/Kolkata', NOW()),
            'DD-MM-YYYY HH24:MI:SS'
        );

    -- ============================================================
    -- 6. WRITE IMMUTABLE AUDIT EVENT
    -- ============================================================

    INSERT INTO public.system_audit_log (
        actor_username,
        actor_role,
        user_id,
        action_type,
        target_module,
        target_id,
        description,
        old_value,
        new_value,
        change_reason,
        device_id,
        ip_address,
        ist_display_time
    )
    VALUES (
        v_actor,
        v_role,
        v_user_id,
        TG_OP,
        TG_TABLE_NAME,
        v_target_id,
        'Database state change on ' || TG_TABLE_NAME,
        v_old_json,
        v_new_json,
        v_reason,
        v_device,
        v_ip,
        v_formatted_time
    );

    -- ============================================================
    -- 7. RETURN
    -- ============================================================

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;

END;
$$;


--
-- Name: register_accession_no(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.register_accession_no() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  INSERT INTO number_registry (number_type, value)
  VALUES ('ACCESSION', NEW.accession_no);
  RETURN NEW;
END;
$$;


--
-- Name: review_notes_block_change(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.review_notes_block_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'review_notes is append-only: % is not allowed', TG_OP;
END;
$$;


--
-- Name: set_audit_session_context(text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_audit_session_context(target_user text, target_role text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM set_config('request.jwt.claim.username', target_user, false);
    PERFORM set_config('request.jwt.claim.role', target_role, false);
END;
$$;


--
-- Name: set_audit_session_context(character varying, character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_audit_session_context(target_user character varying, target_role character varying) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    PERFORM set_config('request.jwt.claim.username', target_user, true);
    PERFORM set_config('request.jwt.claim.role', target_role, true);
END;
$$;


--
-- Name: update_works_timestamp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_works_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: access_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.access_requests (
    request_id integer NOT NULL,
    full_name character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    organization character varying(255),
    purpose text NOT NULL,
    requested_role character varying(100) NOT NULL,
    temporary_access boolean DEFAULT false,
    temporary_expiry timestamp without time zone,
    status character varying(50) DEFAULT 'PENDING'::character varying,
    keeper_recommendation character varying(50),
    keeper_notes text,
    chief_decision character varying(50),
    chief_notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: access_requests_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.access_requests_request_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: access_requests_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.access_requests_request_id_seq OWNED BY public.access_requests.request_id;


--
-- Name: activity_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.activity_log (
    log_id integer NOT NULL,
    user_id integer NOT NULL,
    action text NOT NULL,
    entity text NOT NULL,
    entity_id integer,
    details text,
    "timestamp" timestamp without time zone DEFAULT now()
);


--
-- Name: activity_log_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.activity_log_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: activity_log_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.activity_log_log_id_seq OWNED BY public.activity_log.log_id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: application_error_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.application_error_log (
    error_id bigint NOT NULL,
    error_reference text NOT NULL,
    request_id text,
    occurred_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id integer,
    role text,
    endpoint text NOT NULL,
    http_method text NOT NULL,
    status_code integer NOT NULL,
    operation text,
    failed_stage text,
    error_type text,
    sqlstate text,
    error_message text,
    traceback text,
    client_ip text,
    user_agent text,
    application_version text,
    git_revision text,
    technical_context jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: application_error_log_error_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.application_error_log ALTER COLUMN error_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.application_error_log_error_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: archive_incidents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.archive_incidents (
    incident_id integer NOT NULL,
    serial_no integer NOT NULL,
    incident_type character varying(50) NOT NULL,
    severity character varying(20) DEFAULT 'MEDIUM'::character varying,
    reported_by integer NOT NULL,
    assigned_to integer,
    status character varying(30) DEFAULT 'OPEN'::character varying,
    description text,
    resolution_notes text,
    reported_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    resolved_at timestamp without time zone
);


--
-- Name: archive_incidents_incident_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.archive_incidents_incident_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: archive_incidents_incident_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.archive_incidents_incident_id_seq OWNED BY public.archive_incidents.incident_id;


--
-- Name: audit_activities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_activities (
    id character varying(36) NOT NULL,
    session_id character varying(36),
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    user_id character varying(64) NOT NULL,
    username character varying(128) NOT NULL,
    role character varying(64) NOT NULL,
    designation character varying(128) NOT NULL,
    machine_name character varying(128) NOT NULL,
    ip_address character varying(45) NOT NULL,
    category character varying(32) NOT NULL,
    action_type character varying(64) NOT NULL,
    target_entity character varying(64),
    target_id character varying(64),
    endpoint character varying(255),
    http_method character varying(10),
    justification text,
    diff_payload jsonb,
    extra_metadata jsonb,
    sequence_id bigint NOT NULL,
    prev_hash character varying(64),
    record_hash character varying(64)
);


--
-- Name: audit_activities_sequence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_activities_sequence_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_activities_sequence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_activities_sequence_id_seq OWNED BY public.audit_activities.sequence_id;


--
-- Name: audit_ledger; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_ledger (
    id bigint NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    actor_id text NOT NULL,
    actor_name text NOT NULL,
    actor_role text NOT NULL,
    action_type text NOT NULL,
    target_entity text NOT NULL,
    target_id text NOT NULL,
    state_before jsonb,
    state_after jsonb,
    justification text NOT NULL
);


--
-- Name: audit_ledger_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_ledger_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_ledger_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_ledger_id_seq OWNED BY public.audit_ledger.id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    log_id integer NOT NULL,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    admin_name character varying(255),
    action_type character varying(100),
    serial_number character varying(20),
    old_value text,
    new_value text,
    valid_reason text NOT NULL,
    user_id integer,
    target_id character varying(100),
    details text,
    ip_address character varying(45),
    equipment character varying(20)
);


--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_log_id_seq OWNED BY public.audit_logs.log_id;


--
-- Name: authority_code_p_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.authority_code_p_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: authority_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.authority_records (
    authority_id integer NOT NULL,
    authority_code text NOT NULL,
    preferred_name text NOT NULL,
    authority_type text NOT NULL,
    status text DEFAULT 'PROVISIONAL'::text NOT NULL,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by integer,
    updated_by integer,
    verified_at timestamp without time zone,
    verified_by integer,
    original_name text,
    malayalam_name text,
    full_name character varying(255),
    CONSTRAINT authority_records_preferred_name_check CHECK ((btrim(preferred_name) <> ''::text)),
    CONSTRAINT authority_records_status_check CHECK ((status = ANY (ARRAY['PROVISIONAL'::text, 'VERIFIED'::text, 'REJECTED'::text, 'RETIRED'::text]))),
    CONSTRAINT authority_records_type_check CHECK ((authority_type = ANY (ARRAY['PERSON'::text, 'HISTORICAL'::text, 'TRADITIONAL'::text, 'CORPORATE'::text, 'FAMILY'::text, 'UNKNOWN'::text, 'ANONYMOUS'::text, 'UNCONTROLLED'::text])))
);


--
-- Name: authority_records_authority_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.authority_records ALTER COLUMN authority_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.authority_records_authority_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: authority_variants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.authority_variants (
    variant_id integer NOT NULL,
    authority_id integer NOT NULL,
    variant_name text NOT NULL,
    variant_type text DEFAULT 'OTHER'::text NOT NULL,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by integer,
    CONSTRAINT authority_variants_name_check CHECK ((btrim(variant_name) <> ''::text)),
    CONSTRAINT authority_variants_type_check CHECK ((variant_type = ANY (ARRAY['ALTERNATE_NAME'::text, 'INITIALISM'::text, 'PEN NAME'::text, 'TRANSLITERATION'::text, 'TRANSLATED_NAME'::text, 'FORMER_NAME'::text, 'OTHER'::text])))
);


--
-- Name: authority_variants_variant_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.authority_variants ALTER COLUMN variant_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.authority_variants_variant_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: chief_notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chief_notifications (
    notification_id integer NOT NULL,
    identity_id integer,
    message text NOT NULL,
    is_read boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: chief_notifications_notification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chief_notifications_notification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chief_notifications_notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chief_notifications_notification_id_seq OWNED BY public.chief_notifications.notification_id;


--
-- Name: correction_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.correction_requests (
    request_id bigint NOT NULL,
    entity text NOT NULL,
    entity_id integer NOT NULL,
    requested_by integer NOT NULL,
    requested_by_name text NOT NULL,
    field_names text[] NOT NULL,
    status text DEFAULT 'OPEN'::text NOT NULL,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone,
    resolved_by integer,
    CONSTRAINT correction_requests_entity_check CHECK ((entity = ANY (ARRAY['WORK'::text, 'ITEM'::text]))),
    CONSTRAINT correction_requests_field_names_check CHECK ((cardinality(field_names) > 0)),
    CONSTRAINT correction_requests_status_check CHECK ((status = ANY (ARRAY['OPEN'::text, 'RESOLVED'::text])))
);


--
-- Name: correction_requests_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.correction_requests_request_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: correction_requests_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.correction_requests_request_id_seq OWNED BY public.correction_requests.request_id;


--
-- Name: fines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fines (
    fine_id integer NOT NULL,
    loan_id integer,
    user_id integer,
    amount numeric(10,2) NOT NULL,
    status character varying(20) DEFAULT 'UNPAID'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    paid_at timestamp without time zone,
    waived_reason text,
    processed_by integer
);


--
-- Name: fines_fine_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.fines_fine_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: fines_fine_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.fines_fine_id_seq OWNED BY public.fines.fine_id;


--
-- Name: identity_registry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.identity_registry (
    identity_id integer NOT NULL,
    full_name text NOT NULL,
    primary_email text,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: identity_registry_identity_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.identity_registry_identity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: identity_registry_identity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.identity_registry_identity_id_seq OWNED BY public.identity_registry.identity_id;


--
-- Name: item_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.item_locations (
    location_id integer NOT NULL,
    serial_no integer NOT NULL,
    location_name character varying(100) NOT NULL,
    moved_by integer NOT NULL,
    moved_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
);


--
-- Name: item_locations_location_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.item_locations_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: item_locations_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.item_locations_location_id_seq OWNED BY public.item_locations.location_id;


--
-- Name: items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.items (
    item_id integer NOT NULL,
    serial_no integer DEFAULT public.next_item_serial_no() NOT NULL,
    accession_no text,
    title text,
    author text,
    language_id text,
    category text,
    original_language text,
    translation_compilation text,
    genre text,
    ddc text,
    call_no text,
    isbn text,
    shelf text,
    publisher text,
    year integer,
    notes text,
    work_id integer,
    copies integer DEFAULT 1,
    availability_status character varying(20) DEFAULT 'AVAILABLE'::character varying,
    is_deleted boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    deletion_reason text,
    proposed_by integer,
    physical_condition text,
    binding_type text,
    provenance_source text,
    artifactual_notes text,
    access_restrictions text,
    extent_page_count text,
    physical_dimensions text,
    date_acquired date,
    collection_fonds text,
    digital_scan_available boolean DEFAULT false,
    ocr_status text
);


--
-- Name: items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.items_id_seq OWNED BY public.items.item_id;


--
-- Name: language_registry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_registry (
    language text NOT NULL,
    prefix text NOT NULL,
    last_number integer DEFAULT 0
);


--
-- Name: loans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.loans (
    loan_id integer NOT NULL,
    serial_no integer,
    user_id integer,
    issue_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    due_date timestamp without time zone NOT NULL,
    return_date timestamp without time zone,
    status character varying(20) DEFAULT 'ACTIVE'::character varying,
    issued_by integer,
    notes text
);


--
-- Name: loans_loan_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.loans_loan_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: loans_loan_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.loans_loan_id_seq OWNED BY public.loans.loan_id;


--
-- Name: login_audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.login_audit_log (
    id integer NOT NULL,
    login_id integer,
    role character varying,
    login_name character varying,
    action character varying,
    device_used character varying,
    ip_address character varying,
    "timestamp" timestamp without time zone DEFAULT now()
);


--
-- Name: login_audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.login_audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: login_audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.login_audit_log_id_seq OWNED BY public.login_audit_log.id;


--
-- Name: number_registry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.number_registry (
    registry_id integer NOT NULL,
    number_type text NOT NULL,
    value text NOT NULL,
    assigned_at timestamp without time zone DEFAULT now(),
    retired boolean DEFAULT false,
    CONSTRAINT number_registry_number_type_check CHECK ((number_type = ANY (ARRAY['ACCESSION'::text, 'DDC'::text, 'CALLNO'::text])))
);


--
-- Name: number_registry_registry_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.number_registry_registry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: number_registry_registry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.number_registry_registry_id_seq OWNED BY public.number_registry.registry_id;


--
-- Name: print_audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.print_audit_log (
    audit_id integer NOT NULL,
    item_id integer,
    serial_no integer NOT NULL,
    accession_no character varying(64),
    operator_id character varying(64) NOT NULL,
    operator_name character varying(128),
    operator_role character varying(64),
    machine_uuid character varying(128) NOT NULL,
    station_ip character varying(64),
    checksum character varying(32) NOT NULL,
    print_run_count integer DEFAULT 1 NOT NULL,
    dossier_type character varying(64),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: print_audit_log_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.print_audit_log_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: print_audit_log_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.print_audit_log_audit_id_seq OWNED BY public.print_audit_log.audit_id;


--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_tokens (
    token_id text NOT NULL,
    user_id text NOT NULL,
    expires_at timestamp without time zone NOT NULL
);


--
-- Name: review_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.review_notes (
    note_id bigint NOT NULL,
    entity text NOT NULL,
    entity_id integer NOT NULL,
    request_id bigint,
    author_id integer NOT NULL,
    author_name text NOT NULL,
    author_role text NOT NULL,
    kind text NOT NULL,
    body text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT review_notes_body_check CHECK ((length(btrim(body)) > 0)),
    CONSTRAINT review_notes_entity_check CHECK ((entity = ANY (ARRAY['WORK'::text, 'ITEM'::text]))),
    CONSTRAINT review_notes_kind_check CHECK ((kind = ANY (ARRAY['CHIEF_CORRECTION_NOTE'::text, 'CHIEF_NOTE'::text, 'KEEPER_NOTE'::text])))
);


--
-- Name: review_notes_note_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.review_notes_note_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: review_notes_note_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.review_notes_note_id_seq OWNED BY public.review_notes.note_id;


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    rating integer NOT NULL,
    comment text
);


--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
-- Name: security_incidents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.security_incidents (
    id integer NOT NULL,
    incident_type character varying(64) DEFAULT 'CHAIN_INTEGRITY_BREACH'::character varying NOT NULL,
    severity character varying(16) DEFAULT 'CRITICAL'::character varying NOT NULL,
    compromised_sequence_id integer,
    detected_at timestamp with time zone DEFAULT now(),
    details text,
    resolved boolean DEFAULT false
);


--
-- Name: security_incidents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.security_incidents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: security_incidents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.security_incidents_id_seq OWNED BY public.security_incidents.id;


--
-- Name: status_audit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.status_audit (
    id integer NOT NULL,
    accession_no text,
    old_status text,
    new_status text,
    changed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    changed_by text DEFAULT 'ADMIN'::text
);


--
-- Name: status_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.status_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: status_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.status_audit_id_seq OWNED BY public.status_audit.id;


--
-- Name: status_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.status_history (
    history_id integer NOT NULL,
    item_id integer NOT NULL,
    old_status text,
    new_status text NOT NULL,
    reason text,
    changed_by integer NOT NULL,
    changed_at timestamp without time zone DEFAULT now()
);


--
-- Name: status_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.status_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: status_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.status_history_history_id_seq OWNED BY public.status_history.history_id;


--
-- Name: system_audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_audit_log (
    id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    actor_username character varying(100) NOT NULL,
    actor_role character varying(50) NOT NULL,
    action_type character varying(50) NOT NULL,
    target_module character varying(100) NOT NULL,
    target_id character varying(100),
    description text NOT NULL,
    old_value jsonb,
    new_value jsonb,
    device_id character varying(100),
    ip_address character varying(45),
    ist_display_time character varying(30),
    user_id integer,
    change_reason text
);


--
-- Name: system_audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.system_audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: system_audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.system_audit_log_id_seq OWNED BY public.system_audit_log.id;


--
-- Name: system_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_config (
    config_key character varying(50) NOT NULL,
    config_value numeric(10,2) NOT NULL,
    description text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_by integer
);


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sessions (
    id character varying(36) NOT NULL,
    user_id character varying(64) NOT NULL,
    username character varying(128) NOT NULL,
    role character varying(64) NOT NULL,
    designation character varying(128) NOT NULL,
    machine_name character varying(128) NOT NULL,
    ip_address character varying(45) NOT NULL,
    login_at timestamp with time zone DEFAULT now() NOT NULL,
    logout_at timestamp with time zone,
    duration_seconds integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    name text NOT NULL,
    email text NOT NULL,
    role text NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    revoked_at timestamp without time zone,
    hashed_password text,
    status public.user_status DEFAULT 'PENDING'::public.user_status,
    login_id text,
    must_change_password boolean DEFAULT true,
    twofa_secret text,
    twofa_enabled boolean DEFAULT false,
    expires_at timestamp without time zone,
    operator_id character varying(50),
    identity_id integer,
    CONSTRAINT users_role_canonical_chk CHECK ((role = ANY (ARRAY['The Chief'::text, 'The Keeper'::text, 'The Seeker'::text]))),
    CONSTRAINT users_role_expiry_chk CHECK ((((role = 'The Seeker'::text) AND (expires_at IS NOT NULL)) OR ((role = ANY (ARRAY['The Chief'::text, 'The Keeper'::text])) AND (expires_at IS NULL))))
);


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: v_status_audit; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_status_audit AS
 SELECT changed_at,
    item_id,
    old_status,
    new_status,
    reason,
    changed_by AS user_id
   FROM public.status_history sh;


--
-- Name: work_authorities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.work_authorities (
    work_authority_id integer NOT NULL,
    work_id integer NOT NULL,
    authority_id integer NOT NULL,
    relationship_type text NOT NULL,
    sequence_no integer DEFAULT 1 NOT NULL,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by integer,
    CONSTRAINT work_authorities_relationship_check CHECK ((relationship_type = ANY (ARRAY['AUTHOR'::text, 'EDITOR'::text, 'TRANSLATOR'::text, 'COMPILER'::text, 'ILLUSTRATOR'::text, 'ADAPTER'::text, 'INTRODUCER'::text, 'ANNOTATOR'::text, 'PHOTOGRAPHER'::text, 'OTHER'::text]))),
    CONSTRAINT work_authorities_sequence_check CHECK ((sequence_no > 0))
);


--
-- Name: work_authorities_work_authority_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.work_authorities ALTER COLUMN work_authority_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.work_authorities_work_authority_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: work_id_never_reuse_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.work_id_never_reuse_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: work_series_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.work_series_groups (
    series_id integer NOT NULL,
    series_name text NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_by integer
);


--
-- Name: work_series_groups_series_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.work_series_groups ALTER COLUMN series_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.work_series_groups_series_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: work_series_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.work_series_members (
    series_id integer NOT NULL,
    work_id integer NOT NULL,
    volume_number integer,
    volume_label text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    series_number text,
    related_work_id integer,
    CONSTRAINT work_series_members_volume_check CHECK (((volume_number IS NULL) OR (volume_number > 0)))
);


--
-- Name: works; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.works (
    work_id integer DEFAULT public.next_work_id() NOT NULL,
    title text NOT NULL,
    language text NOT NULL,
    category text,
    genre text,
    author text DEFAULT 'Author'::text,
    publisher text DEFAULT 'PBUNK'::text,
    original_language text,
    ddc text,
    notes text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    search_vector tsvector,
    translation_compilation text,
    year integer,
    call_no text,
    isbn text,
    total_copies integer DEFAULT 0,
    status character varying(20) DEFAULT 'PENDING'::character varying,
    proposed_by integer,
    proposal_reason text,
    approved_by integer,
    approval_reason text,
    approved_at timestamp without time zone,
    original_author text,
    edition_statement text,
    series_title text,
    series_volume text,
    content_form text,
    translator text,
    compiler_editor text,
    work_nature text,
    lccn text,
    oclc_no text,
    subject_headings text,
    target_audience_era text,
    copyright_status text,
    original_title text,
    CONSTRAINT check_work_nature CHECK ((work_nature = ANY (ARRAY['Original'::text, 'Translation'::text, 'Compilation / Anthology'::text, NULL::text]))),
    CONSTRAINT works_category_check CHECK ((category = ANY (ARRAY['Fiction'::text, 'Non-Fiction'::text, 'Reference'::text, 'Religious'::text, 'Poetry'::text]))),
    CONSTRAINT works_status_check CHECK (((status)::text = ANY (ARRAY[('PENDING'::character varying)::text, ('APPROVED'::character varying)::text, ('REJECTED'::character varying)::text, ('NEEDS_CORRECTION'::character varying)::text])))
);


--
-- Name: works_work_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.works_work_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: works_work_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.works_work_id_seq OWNED BY public.works.work_id;


--
-- Name: access_requests request_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_requests ALTER COLUMN request_id SET DEFAULT nextval('public.access_requests_request_id_seq'::regclass);


--
-- Name: activity_log log_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_log ALTER COLUMN log_id SET DEFAULT nextval('public.activity_log_log_id_seq'::regclass);


--
-- Name: archive_incidents incident_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archive_incidents ALTER COLUMN incident_id SET DEFAULT nextval('public.archive_incidents_incident_id_seq'::regclass);


--
-- Name: audit_activities sequence_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_activities ALTER COLUMN sequence_id SET DEFAULT nextval('public.audit_activities_sequence_id_seq'::regclass);


--
-- Name: audit_ledger id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_ledger ALTER COLUMN id SET DEFAULT nextval('public.audit_ledger_id_seq'::regclass);


--
-- Name: audit_logs log_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN log_id SET DEFAULT nextval('public.audit_logs_log_id_seq'::regclass);


--
-- Name: chief_notifications notification_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chief_notifications ALTER COLUMN notification_id SET DEFAULT nextval('public.chief_notifications_notification_id_seq'::regclass);


--
-- Name: correction_requests request_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_requests ALTER COLUMN request_id SET DEFAULT nextval('public.correction_requests_request_id_seq'::regclass);


--
-- Name: fines fine_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fines ALTER COLUMN fine_id SET DEFAULT nextval('public.fines_fine_id_seq'::regclass);


--
-- Name: identity_registry identity_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.identity_registry ALTER COLUMN identity_id SET DEFAULT nextval('public.identity_registry_identity_id_seq'::regclass);


--
-- Name: item_locations location_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_locations ALTER COLUMN location_id SET DEFAULT nextval('public.item_locations_location_id_seq'::regclass);


--
-- Name: items item_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items ALTER COLUMN item_id SET DEFAULT nextval('public.items_id_seq'::regclass);


--
-- Name: loans loan_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.loans ALTER COLUMN loan_id SET DEFAULT nextval('public.loans_loan_id_seq'::regclass);


--
-- Name: login_audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.login_audit_log ALTER COLUMN id SET DEFAULT nextval('public.login_audit_log_id_seq'::regclass);


--
-- Name: number_registry registry_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_registry ALTER COLUMN registry_id SET DEFAULT nextval('public.number_registry_registry_id_seq'::regclass);


--
-- Name: print_audit_log audit_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.print_audit_log ALTER COLUMN audit_id SET DEFAULT nextval('public.print_audit_log_audit_id_seq'::regclass);


--
-- Name: review_notes note_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_notes ALTER COLUMN note_id SET DEFAULT nextval('public.review_notes_note_id_seq'::regclass);


--
-- Name: reviews id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
-- Name: security_incidents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.security_incidents ALTER COLUMN id SET DEFAULT nextval('public.security_incidents_id_seq'::regclass);


--
-- Name: status_audit id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status_audit ALTER COLUMN id SET DEFAULT nextval('public.status_audit_id_seq'::regclass);


--
-- Name: status_history history_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status_history ALTER COLUMN history_id SET DEFAULT nextval('public.status_history_history_id_seq'::regclass);


--
-- Name: system_audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_audit_log ALTER COLUMN id SET DEFAULT nextval('public.system_audit_log_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: access_requests access_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.access_requests
    ADD CONSTRAINT access_requests_pkey PRIMARY KEY (request_id);


--
-- Name: activity_log activity_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_log
    ADD CONSTRAINT activity_log_pkey PRIMARY KEY (log_id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: application_error_log application_error_log_error_reference_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_error_log
    ADD CONSTRAINT application_error_log_error_reference_key UNIQUE (error_reference);


--
-- Name: application_error_log application_error_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_error_log
    ADD CONSTRAINT application_error_log_pkey PRIMARY KEY (error_id);


--
-- Name: archive_incidents archive_incidents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archive_incidents
    ADD CONSTRAINT archive_incidents_pkey PRIMARY KEY (incident_id);


--
-- Name: audit_activities audit_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_activities
    ADD CONSTRAINT audit_activities_pkey PRIMARY KEY (id);


--
-- Name: audit_ledger audit_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_ledger
    ADD CONSTRAINT audit_ledger_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (log_id);


--
-- Name: authority_records authority_records_authority_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authority_records
    ADD CONSTRAINT authority_records_authority_code_key UNIQUE (authority_code);


--
-- Name: authority_records authority_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authority_records
    ADD CONSTRAINT authority_records_pkey PRIMARY KEY (authority_id);


--
-- Name: authority_variants authority_variants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authority_variants
    ADD CONSTRAINT authority_variants_pkey PRIMARY KEY (variant_id);


--
-- Name: chief_notifications chief_notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chief_notifications
    ADD CONSTRAINT chief_notifications_pkey PRIMARY KEY (notification_id);


--
-- Name: correction_requests correction_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_requests
    ADD CONSTRAINT correction_requests_pkey PRIMARY KEY (request_id);


--
-- Name: fines fines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fines
    ADD CONSTRAINT fines_pkey PRIMARY KEY (fine_id);


--
-- Name: identity_registry identity_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.identity_registry
    ADD CONSTRAINT identity_registry_pkey PRIMARY KEY (identity_id);


--
-- Name: identity_registry identity_registry_primary_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.identity_registry
    ADD CONSTRAINT identity_registry_primary_email_key UNIQUE (primary_email);


--
-- Name: item_locations item_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_locations
    ADD CONSTRAINT item_locations_pkey PRIMARY KEY (location_id);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (item_id);


--
-- Name: items items_serial_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_serial_no_key UNIQUE (serial_no);


--
-- Name: language_registry language_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_registry
    ADD CONSTRAINT language_registry_pkey PRIMARY KEY (language);


--
-- Name: language_registry language_registry_prefix_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_registry
    ADD CONSTRAINT language_registry_prefix_key UNIQUE (prefix);


--
-- Name: loans loans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.loans
    ADD CONSTRAINT loans_pkey PRIMARY KEY (loan_id);


--
-- Name: login_audit_log login_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.login_audit_log
    ADD CONSTRAINT login_audit_log_pkey PRIMARY KEY (id);


--
-- Name: number_registry number_registry_number_type_value_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_registry
    ADD CONSTRAINT number_registry_number_type_value_key UNIQUE (number_type, value);


--
-- Name: number_registry number_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_registry
    ADD CONSTRAINT number_registry_pkey PRIMARY KEY (registry_id);


--
-- Name: print_audit_log print_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.print_audit_log
    ADD CONSTRAINT print_audit_log_pkey PRIMARY KEY (audit_id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (token_id);


--
-- Name: review_notes review_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_notes
    ADD CONSTRAINT review_notes_pkey PRIMARY KEY (note_id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: security_incidents security_incidents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.security_incidents
    ADD CONSTRAINT security_incidents_pkey PRIMARY KEY (id);


--
-- Name: status_audit status_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status_audit
    ADD CONSTRAINT status_audit_pkey PRIMARY KEY (id);


--
-- Name: status_history status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status_history
    ADD CONSTRAINT status_history_pkey PRIMARY KEY (history_id);


--
-- Name: system_audit_log system_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_audit_log
    ADD CONSTRAINT system_audit_log_pkey PRIMARY KEY (id);


--
-- Name: system_config system_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT system_config_pkey PRIMARY KEY (config_key);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: users users_login_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_login_id_key UNIQUE (login_id);


--
-- Name: users users_operator_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_operator_id_key UNIQUE (operator_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: work_authorities work_authorities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_authorities
    ADD CONSTRAINT work_authorities_pkey PRIMARY KEY (work_authority_id);


--
-- Name: work_authorities work_authorities_unique_relationship; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_authorities
    ADD CONSTRAINT work_authorities_unique_relationship UNIQUE (work_id, authority_id, relationship_type);


--
-- Name: work_series_groups work_series_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_series_groups
    ADD CONSTRAINT work_series_groups_pkey PRIMARY KEY (series_id);


--
-- Name: work_series_members work_series_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_series_members
    ADD CONSTRAINT work_series_members_pkey PRIMARY KEY (series_id, work_id);


--
-- Name: works works_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.works
    ADD CONSTRAINT works_pkey PRIMARY KEY (work_id);


--
-- Name: application_error_log_occurred_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX application_error_log_occurred_idx ON public.application_error_log USING btree (occurred_at DESC);


--
-- Name: application_error_log_request_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX application_error_log_request_idx ON public.application_error_log USING btree (request_id);


--
-- Name: application_error_log_status_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX application_error_log_status_idx ON public.application_error_log USING btree (status_code, occurred_at DESC);


--
-- Name: correction_requests_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX correction_requests_lookup ON public.correction_requests USING btree (entity, entity_id);


--
-- Name: correction_requests_one_open; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX correction_requests_one_open ON public.correction_requests USING btree (entity, entity_id) WHERE (status = 'OPEN'::text);


--
-- Name: idx_audit_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_action ON public.system_audit_log USING btree (action_type);


--
-- Name: idx_audit_activities_seq; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_activities_seq ON public.audit_activities USING btree (sequence_id);


--
-- Name: idx_audit_target; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_target ON public.audit_activities USING btree (target_entity, target_id, sequence_id);


--
-- Name: idx_audit_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_timestamp ON public.system_audit_log USING btree ("timestamp" DESC);


--
-- Name: idx_authority_records_preferred_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_authority_records_preferred_name ON public.authority_records USING btree (preferred_name);


--
-- Name: idx_authority_records_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_authority_records_status ON public.authority_records USING btree (status);


--
-- Name: idx_authority_records_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_authority_records_type ON public.authority_records USING btree (authority_type);


--
-- Name: idx_authority_variants_authority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_authority_variants_authority ON public.authority_variants USING btree (authority_id);


--
-- Name: idx_authority_variants_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_authority_variants_name ON public.authority_variants USING btree (variant_name);


--
-- Name: idx_items_accession; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_accession ON public.items USING btree (accession_no);


--
-- Name: idx_items_serial; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_serial ON public.items USING btree (serial_no);


--
-- Name: idx_items_shelf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_shelf ON public.items USING btree (shelf);


--
-- Name: idx_print_audit_checksum; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_print_audit_checksum ON public.print_audit_log USING btree (checksum);


--
-- Name: idx_print_audit_serial; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_print_audit_serial ON public.print_audit_log USING btree (serial_no);


--
-- Name: idx_work_authorities_authority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_work_authorities_authority ON public.work_authorities USING btree (authority_id);


--
-- Name: idx_work_authorities_relationship; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_work_authorities_relationship ON public.work_authorities USING btree (relationship_type);


--
-- Name: idx_work_authorities_work; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_work_authorities_work ON public.work_authorities USING btree (work_id);


--
-- Name: idx_works_author_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_author_trgm ON public.works USING gin (author public.gin_trgm_ops);


--
-- Name: idx_works_category_norm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_category_norm ON public.works USING btree (replace(replace(lower(category), '-'::text, ''::text), ' '::text, ''::text));


--
-- Name: idx_works_category_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_category_trgm ON public.works USING gin (category public.gin_trgm_ops);


--
-- Name: idx_works_ddc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_ddc ON public.works USING btree (ddc);


--
-- Name: idx_works_lccn; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_lccn ON public.works USING btree (lccn);


--
-- Name: idx_works_oclc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_oclc ON public.works USING btree (oclc_no);


--
-- Name: idx_works_original_author; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_original_author ON public.works USING btree (original_author);


--
-- Name: idx_works_publisher_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_publisher_trgm ON public.works USING gin (publisher public.gin_trgm_ops);


--
-- Name: idx_works_publisher_trgm_fuzzy; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_publisher_trgm_fuzzy ON public.works USING gist (publisher public.gist_trgm_ops);


--
-- Name: idx_works_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_search ON public.works USING gin (search_vector);


--
-- Name: idx_works_title; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_title ON public.works USING btree (title);


--
-- Name: idx_works_title_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_works_title_trgm ON public.works USING gin (title public.gin_trgm_ops);


--
-- Name: review_notes_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX review_notes_lookup ON public.review_notes USING btree (entity, entity_id, note_id);


--
-- Name: uniq_works_nodup; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uniq_works_nodup ON public.works USING btree (title, language, COALESCE(author, ''::text));


--
-- Name: users_one_approved_chief_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX users_one_approved_chief_idx ON public.users USING btree (role) WHERE ((role = 'The Chief'::text) AND (status = 'APPROVED'::public.user_status));


--
-- Name: work_series_members_related_work_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX work_series_members_related_work_idx ON public.work_series_members USING btree (related_work_id);


--
-- Name: work_series_members_series_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX work_series_members_series_idx ON public.work_series_members USING btree (series_id);


--
-- Name: work_series_members_volume_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX work_series_members_volume_unique ON public.work_series_members USING btree (series_id, volume_number) WHERE (volume_number IS NOT NULL);


--
-- Name: work_series_members_work_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX work_series_members_work_idx ON public.work_series_members USING btree (work_id);


--
-- Name: work_series_members_work_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX work_series_members_work_unique ON public.work_series_members USING btree (work_id);


--
-- Name: audit_activities audit_activities_no_truncate; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_activities_no_truncate BEFORE TRUNCATE ON public.audit_activities FOR EACH STATEMENT EXECUTE FUNCTION public.audit_activities_block_change();


--
-- Name: audit_activities audit_activities_no_update_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_activities_no_update_delete BEFORE DELETE OR UPDATE ON public.audit_activities FOR EACH ROW EXECUTE FUNCTION public.audit_activities_block_change();


--
-- Name: authority_records audit_authority_records_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_authority_records_trigger AFTER INSERT OR DELETE OR UPDATE ON public.authority_records FOR EACH ROW EXECUTE FUNCTION public.process_automatic_audit();


--
-- Name: authority_variants audit_authority_variants_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_authority_variants_trigger AFTER INSERT OR DELETE OR UPDATE ON public.authority_variants FOR EACH ROW EXECUTE FUNCTION public.process_automatic_audit();


--
-- Name: items audit_items_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_items_trigger AFTER INSERT OR DELETE OR UPDATE ON public.items FOR EACH ROW EXECUTE FUNCTION public.process_automatic_audit();

ALTER TABLE public.items DISABLE TRIGGER audit_items_trigger;


--
-- Name: work_authorities audit_work_authorities_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_work_authorities_trigger AFTER INSERT OR DELETE OR UPDATE ON public.work_authorities FOR EACH ROW EXECUTE FUNCTION public.process_automatic_audit();


--
-- Name: works audit_works_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_works_trigger AFTER INSERT OR DELETE OR UPDATE ON public.works FOR EACH ROW EXECUTE FUNCTION public.process_automatic_audit();

ALTER TABLE public.works DISABLE TRIGGER audit_works_trigger;


--
-- Name: correction_requests correction_requests_guard_trg; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER correction_requests_guard_trg BEFORE DELETE OR UPDATE ON public.correction_requests FOR EACH ROW EXECUTE FUNCTION public.correction_requests_guard();


--
-- Name: audit_activities lock_audit_activities_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lock_audit_activities_trigger BEFORE DELETE OR UPDATE ON public.audit_activities FOR EACH ROW EXECUTE FUNCTION public.block_audit_tampering();


--
-- Name: audit_ledger lock_audit_ledger_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lock_audit_ledger_trigger BEFORE DELETE OR UPDATE ON public.audit_ledger FOR EACH ROW EXECUTE FUNCTION public.block_audit_tampering();


--
-- Name: review_notes review_notes_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER review_notes_append_only BEFORE DELETE OR UPDATE ON public.review_notes FOR EACH ROW EXECUTE FUNCTION public.review_notes_block_change();


--
-- Name: system_audit_log trg_fix_log_actor; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_fix_log_actor BEFORE INSERT ON public.system_audit_log FOR EACH ROW EXECUTE FUNCTION public.fix_system_audit_log_actor();


--
-- Name: works trg_update_works; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_update_works BEFORE UPDATE ON public.works FOR EACH ROW EXECUTE FUNCTION public.update_works_timestamp();


--
-- Name: items trigger_automatic_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_automatic_audit AFTER INSERT OR DELETE OR UPDATE ON public.items FOR EACH ROW EXECUTE FUNCTION public.process_automatic_audit();


--
-- Name: works trigger_automatic_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_automatic_audit AFTER INSERT OR DELETE OR UPDATE ON public.works FOR EACH ROW EXECUTE FUNCTION public.process_automatic_audit();


--
-- Name: activity_log activity_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_log
    ADD CONSTRAINT activity_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: archive_incidents archive_incidents_assigned_to_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archive_incidents
    ADD CONSTRAINT archive_incidents_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES public.users(user_id);


--
-- Name: archive_incidents archive_incidents_reported_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archive_incidents
    ADD CONSTRAINT archive_incidents_reported_by_fkey FOREIGN KEY (reported_by) REFERENCES public.users(user_id);


--
-- Name: archive_incidents archive_incidents_serial_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archive_incidents
    ADD CONSTRAINT archive_incidents_serial_no_fkey FOREIGN KEY (serial_no) REFERENCES public.items(serial_no);


--
-- Name: audit_activities audit_activities_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_activities
    ADD CONSTRAINT audit_activities_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.user_sessions(id) ON DELETE SET NULL;


--
-- Name: authority_records authority_records_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authority_records
    ADD CONSTRAINT authority_records_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: authority_records authority_records_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authority_records
    ADD CONSTRAINT authority_records_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(user_id);


--
-- Name: authority_records authority_records_verified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authority_records
    ADD CONSTRAINT authority_records_verified_by_fkey FOREIGN KEY (verified_by) REFERENCES public.users(user_id);


--
-- Name: authority_variants authority_variants_authority_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authority_variants
    ADD CONSTRAINT authority_variants_authority_fkey FOREIGN KEY (authority_id) REFERENCES public.authority_records(authority_id) ON DELETE CASCADE;


--
-- Name: authority_variants authority_variants_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authority_variants
    ADD CONSTRAINT authority_variants_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: chief_notifications chief_notifications_identity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chief_notifications
    ADD CONSTRAINT chief_notifications_identity_id_fkey FOREIGN KEY (identity_id) REFERENCES public.identity_registry(identity_id);


--
-- Name: fines fines_loan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fines
    ADD CONSTRAINT fines_loan_id_fkey FOREIGN KEY (loan_id) REFERENCES public.loans(loan_id);


--
-- Name: fines fines_processed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fines
    ADD CONSTRAINT fines_processed_by_fkey FOREIGN KEY (processed_by) REFERENCES public.users(user_id);


--
-- Name: fines fines_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fines
    ADD CONSTRAINT fines_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: system_audit_log fk_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_audit_log
    ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: audit_logs fk_user_audit; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT fk_user_audit FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: item_locations item_locations_moved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_locations
    ADD CONSTRAINT item_locations_moved_by_fkey FOREIGN KEY (moved_by) REFERENCES public.users(user_id);


--
-- Name: item_locations item_locations_serial_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_locations
    ADD CONSTRAINT item_locations_serial_no_fkey FOREIGN KEY (serial_no) REFERENCES public.items(serial_no);


--
-- Name: items items_proposed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_proposed_by_fkey FOREIGN KEY (proposed_by) REFERENCES public.users(user_id);


--
-- Name: loans loans_issued_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.loans
    ADD CONSTRAINT loans_issued_by_fkey FOREIGN KEY (issued_by) REFERENCES public.users(user_id);


--
-- Name: loans loans_serial_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.loans
    ADD CONSTRAINT loans_serial_no_fkey FOREIGN KEY (serial_no) REFERENCES public.items(serial_no);


--
-- Name: loans loans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.loans
    ADD CONSTRAINT loans_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: print_audit_log print_audit_log_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.print_audit_log
    ADD CONSTRAINT print_audit_log_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(item_id) ON DELETE SET NULL;


--
-- Name: review_notes review_notes_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_notes
    ADD CONSTRAINT review_notes_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.correction_requests(request_id);


--
-- Name: status_history status_history_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status_history
    ADD CONSTRAINT status_history_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(user_id);


--
-- Name: system_config system_config_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT system_config_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(user_id);


--
-- Name: users users_identity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_identity_id_fkey FOREIGN KEY (identity_id) REFERENCES public.identity_registry(identity_id);


--
-- Name: work_authorities work_authorities_authority_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_authorities
    ADD CONSTRAINT work_authorities_authority_fkey FOREIGN KEY (authority_id) REFERENCES public.authority_records(authority_id) ON DELETE RESTRICT;


--
-- Name: work_authorities work_authorities_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_authorities
    ADD CONSTRAINT work_authorities_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: work_authorities work_authorities_work_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_authorities
    ADD CONSTRAINT work_authorities_work_fkey FOREIGN KEY (work_id) REFERENCES public.works(work_id) ON DELETE CASCADE;


--
-- Name: work_series_groups work_series_groups_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_series_groups
    ADD CONSTRAINT work_series_groups_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: work_series_members work_series_members_related_work_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_series_members
    ADD CONSTRAINT work_series_members_related_work_fkey FOREIGN KEY (related_work_id) REFERENCES public.works(work_id) ON DELETE RESTRICT;


--
-- Name: work_series_members work_series_members_series_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_series_members
    ADD CONSTRAINT work_series_members_series_fkey FOREIGN KEY (series_id) REFERENCES public.work_series_groups(series_id) ON DELETE CASCADE;


--
-- Name: work_series_members work_series_members_work_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_series_members
    ADD CONSTRAINT work_series_members_work_fkey FOREIGN KEY (work_id) REFERENCES public.works(work_id) ON DELETE RESTRICT;


--
-- Name: works works_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.works
    ADD CONSTRAINT works_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(user_id);


--
-- Name: works works_proposed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.works
    ADD CONSTRAINT works_proposed_by_fkey FOREIGN KEY (proposed_by) REFERENCES public.users(user_id);


--
-- PostgreSQL database dump complete
--



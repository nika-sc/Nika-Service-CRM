--
-- PostgreSQL database dump
--

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: action_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_logs (
    id bigint NOT NULL,
    user_id bigint,
    username text,
    action_type text NOT NULL,
    entity_type text NOT NULL,
    entity_id bigint,
    old_values text,
    new_values text,
    details text,
    ip_address text,
    user_agent text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: action_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.action_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: action_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.action_logs_id_seq OWNED BY public.action_logs.id;


--
-- Name: appearance_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.appearance_tags (
    id bigint NOT NULL,
    name text NOT NULL,
    sort_order bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: appearance_tags_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.appearance_tags_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: appearance_tags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.appearance_tags_id_seq OWNED BY public.appearance_tags.id;


--
-- Name: cash_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cash_transactions (
    id bigint NOT NULL,
    category_id bigint NOT NULL,
    amount double precision NOT NULL,
    transaction_type text NOT NULL,
    payment_method text DEFAULT 'cash'::text,
    description text,
    order_id bigint,
    payment_id bigint,
    shop_sale_id bigint,
    transaction_date timestamp without time zone DEFAULT '2026-03-30'::date NOT NULL,
    created_by_id bigint,
    created_by_username text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_cancelled bigint DEFAULT 0,
    cancelled_at text,
    cancelled_reason text,
    cancelled_by_id bigint,
    cancelled_by_username text,
    storno_of_id bigint
);


--
-- Name: cash_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cash_transactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cash_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cash_transactions_id_seq OWNED BY public.cash_transactions.id;


--
-- Name: comment_attachments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.comment_attachments (
    id bigint NOT NULL,
    comment_id bigint NOT NULL,
    filename text NOT NULL,
    file_path text NOT NULL,
    file_size bigint,
    mime_type text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: comment_attachments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.comment_attachments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: comment_attachments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.comment_attachments_id_seq OWNED BY public.comment_attachments.id;


--
-- Name: customer_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_tokens (
    id bigint NOT NULL,
    customer_id bigint NOT NULL,
    token text NOT NULL,
    expires_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_used_at timestamp without time zone
);


--
-- Name: customer_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.customer_tokens_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: customer_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.customer_tokens_id_seq OWNED BY public.customer_tokens.id;


--
-- Name: customer_wallet_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_wallet_transactions (
    id bigint NOT NULL,
    customer_id bigint NOT NULL,
    amount_cents bigint NOT NULL,
    tx_type text NOT NULL,
    source text DEFAULT 'manual'::text NOT NULL,
    order_id bigint,
    payment_id bigint,
    comment text,
    created_by_id bigint,
    created_by_username text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: customer_wallet_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.customer_wallet_transactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: customer_wallet_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.customer_wallet_transactions_id_seq OWNED BY public.customer_wallet_transactions.id;


--
-- Name: customers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customers (
    id bigint NOT NULL,
    name text NOT NULL,
    phone text NOT NULL,
    email text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    wallet_cents bigint DEFAULT 0 NOT NULL,
    portal_password_changed bigint DEFAULT 0,
    portal_enabled bigint DEFAULT 0,
    portal_password_hash text
);


--
-- Name: customers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.customers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: customers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.customers_id_seq OWNED BY public.customers.id;


--
-- Name: device_brands; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.device_brands (
    id bigint NOT NULL,
    name text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    sort_order bigint DEFAULT 0
);


--
-- Name: device_brands_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.device_brands_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: device_brands_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.device_brands_id_seq OWNED BY public.device_brands.id;


--
-- Name: device_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.device_types (
    id bigint NOT NULL,
    name text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    sort_order bigint DEFAULT 0
);


--
-- Name: device_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.device_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: device_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.device_types_id_seq OWNED BY public.device_types.id;


--
-- Name: devices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.devices (
    id bigint NOT NULL,
    customer_id bigint NOT NULL,
    device_type_id bigint NOT NULL,
    device_brand_id bigint NOT NULL,
    serial_number text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    password text,
    symptom_tags text,
    appearance_tags text,
    comment text
);


--
-- Name: devices_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.devices_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: devices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.devices_id_seq OWNED BY public.devices.id;


--
-- Name: general_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.general_settings (
    id bigint NOT NULL,
    org_name text,
    phone text,
    address text,
    inn text,
    ogrn text,
    logo_url text,
    currency text DEFAULT 'RUB'::text,
    country text DEFAULT 'Россия'::text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    default_warranty_days bigint DEFAULT 30,
    timezone_offset bigint DEFAULT 3,
    mail_server text,
    mail_port bigint DEFAULT 587,
    mail_use_tls bigint DEFAULT 1,
    mail_use_ssl bigint DEFAULT 0,
    mail_username text,
    mail_password text,
    mail_default_sender text,
    mail_timeout bigint DEFAULT 3,
    close_print_mode text DEFAULT 'choice'::text,
    auto_email_order_accepted bigint DEFAULT 1,
    auto_email_status_update bigint DEFAULT 1,
    auto_email_order_ready bigint DEFAULT 1,
    auto_email_order_closed bigint DEFAULT 1,
    sms_enabled bigint DEFAULT 0,
    telegram_enabled bigint DEFAULT 0,
    signature_name text,
    signature_position text,
    director_email text,
    auto_email_director_order_accepted bigint DEFAULT 1,
    auto_email_director_order_closed bigint DEFAULT 1
);


--
-- Name: general_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.general_settings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: general_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.general_settings_id_seq OWNED BY public.general_settings.id;


--
-- Name: inventory; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory (
    id bigint NOT NULL,
    name text NOT NULL,
    inventory_date timestamp without time zone DEFAULT '2026-03-30'::date NOT NULL,
    status text DEFAULT 'draft'::text NOT NULL,
    notes text,
    created_by bigint,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone
);


--
-- Name: inventory_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inventory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inventory_id_seq OWNED BY public.inventory.id;


--
-- Name: inventory_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_items (
    id bigint NOT NULL,
    inventory_id bigint NOT NULL,
    part_id bigint NOT NULL,
    stock_quantity bigint DEFAULT 0 NOT NULL,
    actual_quantity bigint DEFAULT 0 NOT NULL,
    difference bigint DEFAULT 0 NOT NULL,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: inventory_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inventory_items_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inventory_items_id_seq OWNED BY public.inventory_items.id;


--
-- Name: managers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.managers (
    id bigint NOT NULL,
    name text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    salary_rule_type text,
    salary_rule_value double precision,
    active bigint DEFAULT 1,
    comment text,
    updated_at timestamp without time zone,
    user_id bigint,
    salary_percent_services double precision,
    salary_percent_parts double precision,
    salary_percent_shop_parts double precision
);


--
-- Name: managers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.managers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: managers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.managers_id_seq OWNED BY public.managers.id;


--
-- Name: masters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.masters (
    id bigint NOT NULL,
    name text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    salary_rule_type text,
    salary_rule_value double precision,
    active bigint DEFAULT 1,
    comment text,
    updated_at timestamp without time zone,
    user_id bigint,
    salary_percent_services double precision,
    salary_percent_parts double precision,
    salary_percent_shop_parts double precision
);


--
-- Name: masters_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.masters_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: masters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.masters_id_seq OWNED BY public.masters.id;


--
-- Name: notification_preferences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_preferences (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    notification_type text NOT NULL,
    enabled bigint DEFAULT 1,
    email_enabled bigint DEFAULT 1,
    push_enabled bigint DEFAULT 1,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: notification_preferences_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notification_preferences_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notification_preferences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notification_preferences_id_seq OWNED BY public.notification_preferences.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    type text NOT NULL,
    title text NOT NULL,
    message text NOT NULL,
    entity_type text,
    entity_id bigint,
    read_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notifications_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: order_appearance_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_appearance_tags (
    id bigint NOT NULL,
    order_id bigint NOT NULL,
    appearance_tag_id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: order_appearance_tags_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_appearance_tags_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_appearance_tags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_appearance_tags_id_seq OWNED BY public.order_appearance_tags.id;


--
-- Name: order_comments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_comments (
    id bigint NOT NULL,
    order_id bigint NOT NULL,
    author_type text DEFAULT 'manager'::text NOT NULL,
    author_id bigint,
    author_name text,
    comment_text text NOT NULL,
    is_internal bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_id bigint,
    mentions text
);


--
-- Name: order_comments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_comments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_comments_id_seq OWNED BY public.order_comments.id;


--
-- Name: order_models; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_models (
    id bigint NOT NULL,
    name text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: order_models_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_models_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_models_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_models_id_seq OWNED BY public.order_models.id;


--
-- Name: order_parts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_parts (
    id bigint NOT NULL,
    order_id bigint NOT NULL,
    part_id bigint,
    name text,
    quantity bigint DEFAULT 1 NOT NULL,
    price numeric DEFAULT 0.00 NOT NULL,
    purchase_price numeric,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    base_price numeric,
    discount_type text,
    discount_value double precision,
    warranty_days bigint,
    executor_id bigint
);


--
-- Name: order_parts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_parts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_parts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_parts_id_seq OWNED BY public.order_parts.id;


--
-- Name: order_services; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_services (
    id bigint NOT NULL,
    order_id bigint NOT NULL,
    service_id bigint,
    name text,
    quantity bigint DEFAULT 1,
    price numeric NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    base_price numeric,
    cost_price numeric,
    discount_type text,
    discount_value double precision,
    warranty_days bigint,
    executor_id bigint
);


--
-- Name: order_services_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_services_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_services_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_services_id_seq OWNED BY public.order_services.id;


--
-- Name: order_status_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_status_history (
    id bigint NOT NULL,
    order_id bigint NOT NULL,
    old_status_id bigint,
    new_status_id bigint NOT NULL,
    changed_by bigint,
    changed_by_username text,
    comment text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: order_status_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_status_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_status_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_status_history_id_seq OWNED BY public.order_status_history.id;


--
-- Name: order_statuses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_statuses (
    id bigint NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    color text DEFAULT '#007bff'::text NOT NULL,
    is_default bigint DEFAULT 0,
    sort_order bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    group_name text,
    triggers_payment_modal bigint DEFAULT 0,
    accrues_salary bigint DEFAULT 0,
    is_archived bigint DEFAULT 0,
    is_final bigint DEFAULT 0,
    blocks_edit bigint DEFAULT 0,
    requires_warranty bigint DEFAULT 0,
    requires_comment bigint DEFAULT 0,
    client_name text,
    client_description text,
    salary_rule_type text,
    salary_rule_value double precision
);


--
-- Name: order_statuses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_statuses_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_statuses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_statuses_id_seq OWNED BY public.order_statuses.id;


--
-- Name: order_symptoms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_symptoms (
    id bigint NOT NULL,
    order_id bigint NOT NULL,
    symptom_id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: order_symptoms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_symptoms_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_symptoms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_symptoms_id_seq OWNED BY public.order_symptoms.id;


--
-- Name: order_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_templates (
    id bigint NOT NULL,
    name text NOT NULL,
    description text,
    template_data text NOT NULL,
    created_by bigint NOT NULL,
    is_public bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: order_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_templates_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_templates_id_seq OWNED BY public.order_templates.id;


--
-- Name: order_visibility_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_visibility_history (
    id bigint NOT NULL,
    order_id bigint NOT NULL,
    hidden bigint NOT NULL,
    changed_by text,
    changed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    reason text
);


--
-- Name: order_visibility_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_visibility_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_visibility_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_visibility_history_id_seq OWNED BY public.order_visibility_history.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orders (
    id bigint NOT NULL,
    order_id text NOT NULL,
    device_id bigint NOT NULL,
    customer_id bigint NOT NULL,
    manager_id bigint NOT NULL,
    master_id bigint,
    status text DEFAULT 'new'::text,
    prepayment text DEFAULT '0'::text NOT NULL,
    password text,
    appearance text,
    comment text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    symptom_tags text,
    intake_checklist text,
    status_id bigint,
    hidden bigint DEFAULT 1,
    model text,
    model_id bigint,
    prepayment_cents bigint DEFAULT 0 NOT NULL,
    is_deleted bigint DEFAULT 0 NOT NULL,
    deleted_at timestamp without time zone,
    deleted_by_id bigint,
    deleted_reason text
);


--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.orders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: part_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.part_categories (
    id bigint NOT NULL,
    name text NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    parent_id bigint
);


--
-- Name: part_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.part_categories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: part_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.part_categories_id_seq OWNED BY public.part_categories.id;


--
-- Name: parts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parts (
    id bigint NOT NULL,
    name text NOT NULL,
    part_number text,
    description text,
    price numeric DEFAULT 0.00 NOT NULL,
    stock_quantity bigint DEFAULT 0 NOT NULL,
    min_quantity bigint DEFAULT 0 NOT NULL,
    category text,
    supplier text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    purchase_price numeric DEFAULT 0.00,
    unit text DEFAULT 'шт'::text,
    warranty_days bigint,
    is_deleted bigint DEFAULT 0,
    comment text,
    category_id bigint,
    salary_rule_type text,
    salary_rule_value double precision
);


--
-- Name: parts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.parts_id_seq OWNED BY public.parts.id;


--
-- Name: payment_receipts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_receipts (
    id bigint NOT NULL,
    payment_id bigint NOT NULL,
    receipt_type text NOT NULL,
    status text DEFAULT 'manual'::text NOT NULL,
    provider text,
    provider_receipt_id text,
    payload text,
    response text,
    error text,
    created_by_id bigint,
    created_by_username text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    printed_at timestamp without time zone
);


--
-- Name: payment_receipts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payment_receipts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payment_receipts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payment_receipts_id_seq OWNED BY public.payment_receipts.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    id bigint NOT NULL,
    order_id bigint NOT NULL,
    amount numeric NOT NULL,
    payment_type text NOT NULL,
    payment_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_by bigint,
    created_by_username text,
    comment text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_cancelled bigint DEFAULT 0,
    cancelled_at text,
    cancelled_reason text,
    cancelled_by_id bigint,
    cancelled_by_username text,
    kind text DEFAULT 'payment'::text NOT NULL,
    status text DEFAULT 'captured'::text NOT NULL,
    idempotency_key text,
    external_provider text,
    external_payment_id text,
    captured_at text,
    refunded_of_id bigint
);


--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permissions (
    id bigint NOT NULL,
    name text NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;


--
-- Name: print_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.print_templates (
    id bigint NOT NULL,
    name text NOT NULL,
    template_type text DEFAULT 'customer'::text NOT NULL,
    html_content text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: print_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.print_templates_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: print_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.print_templates_id_seq OWNED BY public.print_templates.id;


--
-- Name: purchase_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.purchase_items (
    id bigint NOT NULL,
    purchase_id bigint NOT NULL,
    part_id bigint NOT NULL,
    quantity bigint DEFAULT 1 NOT NULL,
    purchase_price numeric NOT NULL,
    total_price numeric NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: purchase_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.purchase_items_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: purchase_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.purchase_items_id_seq OWNED BY public.purchase_items.id;


--
-- Name: purchases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.purchases (
    id bigint NOT NULL,
    supplier_id bigint,
    supplier_name text,
    purchase_date timestamp without time zone NOT NULL,
    total_amount numeric DEFAULT 0.00,
    status text DEFAULT 'draft'::text NOT NULL,
    notes text,
    created_by bigint,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: purchases_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.purchases_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: purchases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.purchases_id_seq OWNED BY public.purchases.id;


--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_permissions (
    role text NOT NULL,
    permission_id bigint NOT NULL
);


--
-- Name: salary_accruals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.salary_accruals (
    id bigint NOT NULL,
    order_id bigint,
    shop_sale_id bigint,
    user_id bigint NOT NULL,
    role text NOT NULL,
    amount_cents bigint NOT NULL,
    base_amount_cents bigint NOT NULL,
    profit_cents bigint NOT NULL,
    rule_type text NOT NULL,
    rule_value double precision NOT NULL,
    calculated_from text NOT NULL,
    calculated_from_id bigint,
    service_id bigint,
    part_id bigint,
    vat_included bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: salary_accruals_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.salary_accruals_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: salary_accruals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.salary_accruals_id_seq OWNED BY public.salary_accruals.id;


--
-- Name: salary_bonuses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.salary_bonuses (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    role text NOT NULL,
    amount_cents bigint NOT NULL,
    reason text,
    order_id bigint,
    bonus_date timestamp without time zone NOT NULL,
    created_by_id bigint,
    created_by_username text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: salary_bonuses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.salary_bonuses_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: salary_bonuses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.salary_bonuses_id_seq OWNED BY public.salary_bonuses.id;


--
-- Name: salary_fines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.salary_fines (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    role text NOT NULL,
    amount_cents bigint NOT NULL,
    reason text NOT NULL,
    order_id bigint,
    fine_date timestamp without time zone NOT NULL,
    created_by_id bigint,
    created_by_username text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: salary_fines_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.salary_fines_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: salary_fines_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.salary_fines_id_seq OWNED BY public.salary_fines.id;


--
-- Name: salary_payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.salary_payments (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    role text NOT NULL,
    amount_cents bigint NOT NULL,
    payment_date timestamp without time zone NOT NULL,
    period_start timestamp without time zone,
    period_end timestamp without time zone,
    payment_type text DEFAULT 'salary'::text,
    comment text,
    created_by_id bigint,
    created_by_username text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    cash_transaction_id bigint
);


--
-- Name: salary_payments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.salary_payments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: salary_payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.salary_payments_id_seq OWNED BY public.salary_payments.id;


--
-- Name: schema_migrations_pg; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations_pg (
    version text NOT NULL,
    name text NOT NULL,
    applied_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: services; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.services (
    id bigint NOT NULL,
    name text NOT NULL,
    price numeric DEFAULT 0.00 NOT NULL,
    is_default bigint DEFAULT 0,
    sort_order bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    salary_rule_type text,
    salary_rule_value double precision
);


--
-- Name: services_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.services_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: services_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.services_id_seq OWNED BY public.services.id;


--
-- Name: shop_sale_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shop_sale_items (
    id bigint NOT NULL,
    shop_sale_id bigint NOT NULL,
    item_type text NOT NULL,
    service_id bigint,
    service_name text,
    part_id bigint,
    part_name text,
    part_sku text,
    quantity bigint DEFAULT 1 NOT NULL,
    price double precision NOT NULL,
    purchase_price double precision DEFAULT 0,
    total double precision NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: shop_sale_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shop_sale_items_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shop_sale_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shop_sale_items_id_seq OWNED BY public.shop_sale_items.id;


--
-- Name: shop_sales; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shop_sales (
    id bigint NOT NULL,
    customer_id bigint,
    customer_name text,
    customer_phone text,
    manager_id bigint,
    master_id bigint,
    total_amount double precision DEFAULT 0 NOT NULL,
    discount double precision DEFAULT 0,
    final_amount double precision DEFAULT 0 NOT NULL,
    paid_amount double precision DEFAULT 0,
    payment_method text DEFAULT 'cash'::text,
    comment text,
    sale_date timestamp without time zone DEFAULT '2026-03-30'::date NOT NULL,
    created_by_id bigint,
    created_by_username text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    order_id bigint
);


--
-- Name: shop_sales_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shop_sales_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shop_sales_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shop_sales_id_seq OWNED BY public.shop_sales.id;


--
-- Name: staff_chat_attachments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staff_chat_attachments (
    id bigint NOT NULL,
    message_id bigint NOT NULL,
    original_name text NOT NULL,
    stored_name text NOT NULL,
    mime_type text,
    size_bytes bigint NOT NULL,
    file_path text NOT NULL,
    is_image smallint DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT staff_chat_attachments_size_bytes_check CHECK ((size_bytes >= 0))
);


--
-- Name: staff_chat_attachments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.staff_chat_attachments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: staff_chat_attachments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.staff_chat_attachments_id_seq OWNED BY public.staff_chat_attachments.id;


--
-- Name: staff_chat_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staff_chat_messages (
    id bigint NOT NULL,
    room_key text DEFAULT 'global'::text NOT NULL,
    user_id bigint,
    username text NOT NULL,
    actor_display_name text,
    client_instance_id text,
    message_text text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    edited_at timestamp without time zone,
    deleted_at timestamp without time zone
);


--
-- Name: staff_chat_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.staff_chat_messages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: staff_chat_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.staff_chat_messages_id_seq OWNED BY public.staff_chat_messages.id;


--
-- Name: staff_chat_reactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staff_chat_reactions (
    id bigint NOT NULL,
    message_id bigint NOT NULL,
    user_id bigint,
    username text NOT NULL,
    actor_display_name text DEFAULT ''::text NOT NULL,
    client_instance_id text DEFAULT ''::text NOT NULL,
    emoji text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: staff_chat_reactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.staff_chat_reactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: staff_chat_reactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.staff_chat_reactions_id_seq OWNED BY public.staff_chat_reactions.id;


--
-- Name: staff_chat_read_cursors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staff_chat_read_cursors (
    id bigint NOT NULL,
    room_key text DEFAULT 'global'::text NOT NULL,
    user_id bigint NOT NULL,
    username text DEFAULT ''::text NOT NULL,
    actor_display_name text DEFAULT ''::text NOT NULL,
    client_instance_id text DEFAULT ''::text NOT NULL,
    last_read_message_id bigint DEFAULT 0 NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: staff_chat_read_cursors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.staff_chat_read_cursors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: staff_chat_read_cursors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.staff_chat_read_cursors_id_seq OWNED BY public.staff_chat_read_cursors.id;


--
-- Name: stock_movements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stock_movements (
    id bigint NOT NULL,
    part_id bigint NOT NULL,
    movement_type text NOT NULL,
    quantity bigint NOT NULL,
    reference_id bigint,
    reference_type text,
    created_by bigint,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: stock_movements_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.stock_movements_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stock_movements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.stock_movements_id_seq OWNED BY public.stock_movements.id;


--
-- Name: suppliers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.suppliers (
    id bigint NOT NULL,
    name text NOT NULL,
    contact_person text,
    phone text,
    email text,
    address text,
    inn text,
    comment text,
    is_active bigint DEFAULT 1,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: suppliers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.suppliers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: suppliers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.suppliers_id_seq OWNED BY public.suppliers.id;


--
-- Name: symptoms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.symptoms (
    id bigint NOT NULL,
    name text NOT NULL,
    sort_order bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: symptoms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.symptoms_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: symptoms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.symptoms_id_seq OWNED BY public.symptoms.id;


--
-- Name: system_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_settings (
    id bigint NOT NULL,
    key text NOT NULL,
    value text,
    description text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: system_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.system_settings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: system_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.system_settings_id_seq OWNED BY public.system_settings.id;


--
-- Name: task_checklists; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_checklists (
    id bigint NOT NULL,
    task_id bigint NOT NULL,
    item_text text NOT NULL,
    is_completed bigint DEFAULT 0,
    item_order bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: task_checklists_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.task_checklists_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: task_checklists_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.task_checklists_id_seq OWNED BY public.task_checklists.id;


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tasks (
    id bigint NOT NULL,
    order_id bigint,
    title text NOT NULL,
    description text,
    assigned_to bigint,
    created_by bigint NOT NULL,
    deadline timestamp without time zone,
    priority text DEFAULT 'medium'::text,
    status text DEFAULT 'todo'::text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone
);


--
-- Name: tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tasks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tasks_id_seq OWNED BY public.tasks.id;


--
-- Name: transaction_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transaction_categories (
    id bigint NOT NULL,
    name text NOT NULL,
    type text NOT NULL,
    description text,
    color text DEFAULT '#6c757d'::text,
    is_system bigint DEFAULT 0,
    is_active bigint DEFAULT 1,
    sort_order bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: transaction_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.transaction_categories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: transaction_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.transaction_categories_id_seq OWNED BY public.transaction_categories.id;


--
-- Name: user_role_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_role_history (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    changed_by bigint,
    changed_by_username text,
    old_role text,
    new_role text,
    old_permission_ids text,
    new_permission_ids text,
    change_type text NOT NULL,
    comment text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: user_role_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_role_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_role_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_role_history_id_seq OWNED BY public.user_role_history.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id bigint NOT NULL,
    username text NOT NULL,
    password_hash text NOT NULL,
    role text DEFAULT 'viewer'::text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_login timestamp without time zone,
    is_active bigint DEFAULT 1,
    display_name text
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: warehouse_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.warehouse_logs (
    id bigint NOT NULL,
    operation_type text NOT NULL,
    part_id bigint,
    part_name text,
    part_number text,
    user_id bigint,
    username text,
    quantity bigint,
    old_value text,
    new_value text,
    notes text,
    ip_address text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    category_id bigint
);


--
-- Name: warehouse_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.warehouse_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: warehouse_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.warehouse_logs_id_seq OWNED BY public.warehouse_logs.id;


--
-- Name: action_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_logs ALTER COLUMN id SET DEFAULT nextval('public.action_logs_id_seq'::regclass);


--
-- Name: appearance_tags id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.appearance_tags ALTER COLUMN id SET DEFAULT nextval('public.appearance_tags_id_seq'::regclass);


--
-- Name: cash_transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cash_transactions ALTER COLUMN id SET DEFAULT nextval('public.cash_transactions_id_seq'::regclass);


--
-- Name: comment_attachments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comment_attachments ALTER COLUMN id SET DEFAULT nextval('public.comment_attachments_id_seq'::regclass);


--
-- Name: customer_tokens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_tokens ALTER COLUMN id SET DEFAULT nextval('public.customer_tokens_id_seq'::regclass);


--
-- Name: customer_wallet_transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_wallet_transactions ALTER COLUMN id SET DEFAULT nextval('public.customer_wallet_transactions_id_seq'::regclass);


--
-- Name: customers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customers ALTER COLUMN id SET DEFAULT nextval('public.customers_id_seq'::regclass);


--
-- Name: device_brands id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_brands ALTER COLUMN id SET DEFAULT nextval('public.device_brands_id_seq'::regclass);


--
-- Name: device_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_types ALTER COLUMN id SET DEFAULT nextval('public.device_types_id_seq'::regclass);


--
-- Name: devices id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devices ALTER COLUMN id SET DEFAULT nextval('public.devices_id_seq'::regclass);


--
-- Name: general_settings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.general_settings ALTER COLUMN id SET DEFAULT nextval('public.general_settings_id_seq'::regclass);


--
-- Name: inventory id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory ALTER COLUMN id SET DEFAULT nextval('public.inventory_id_seq'::regclass);


--
-- Name: inventory_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_items ALTER COLUMN id SET DEFAULT nextval('public.inventory_items_id_seq'::regclass);


--
-- Name: managers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.managers ALTER COLUMN id SET DEFAULT nextval('public.managers_id_seq'::regclass);


--
-- Name: masters id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.masters ALTER COLUMN id SET DEFAULT nextval('public.masters_id_seq'::regclass);


--
-- Name: notification_preferences id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_preferences ALTER COLUMN id SET DEFAULT nextval('public.notification_preferences_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: order_appearance_tags id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_appearance_tags ALTER COLUMN id SET DEFAULT nextval('public.order_appearance_tags_id_seq'::regclass);


--
-- Name: order_comments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_comments ALTER COLUMN id SET DEFAULT nextval('public.order_comments_id_seq'::regclass);


--
-- Name: order_models id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_models ALTER COLUMN id SET DEFAULT nextval('public.order_models_id_seq'::regclass);


--
-- Name: order_parts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_parts ALTER COLUMN id SET DEFAULT nextval('public.order_parts_id_seq'::regclass);


--
-- Name: order_services id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_services ALTER COLUMN id SET DEFAULT nextval('public.order_services_id_seq'::regclass);


--
-- Name: order_status_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_status_history ALTER COLUMN id SET DEFAULT nextval('public.order_status_history_id_seq'::regclass);


--
-- Name: order_statuses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_statuses ALTER COLUMN id SET DEFAULT nextval('public.order_statuses_id_seq'::regclass);


--
-- Name: order_symptoms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_symptoms ALTER COLUMN id SET DEFAULT nextval('public.order_symptoms_id_seq'::regclass);


--
-- Name: order_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_templates ALTER COLUMN id SET DEFAULT nextval('public.order_templates_id_seq'::regclass);


--
-- Name: order_visibility_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_visibility_history ALTER COLUMN id SET DEFAULT nextval('public.order_visibility_history_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Name: part_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.part_categories ALTER COLUMN id SET DEFAULT nextval('public.part_categories_id_seq'::regclass);


--
-- Name: parts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parts ALTER COLUMN id SET DEFAULT nextval('public.parts_id_seq'::regclass);


--
-- Name: payment_receipts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_receipts ALTER COLUMN id SET DEFAULT nextval('public.payment_receipts_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);


--
-- Name: print_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.print_templates ALTER COLUMN id SET DEFAULT nextval('public.print_templates_id_seq'::regclass);


--
-- Name: purchase_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_items ALTER COLUMN id SET DEFAULT nextval('public.purchase_items_id_seq'::regclass);


--
-- Name: purchases id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchases ALTER COLUMN id SET DEFAULT nextval('public.purchases_id_seq'::regclass);


--
-- Name: salary_accruals id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salary_accruals ALTER COLUMN id SET DEFAULT nextval('public.salary_accruals_id_seq'::regclass);


--
-- Name: salary_bonuses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salary_bonuses ALTER COLUMN id SET DEFAULT nextval('public.salary_bonuses_id_seq'::regclass);


--
-- Name: salary_fines id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salary_fines ALTER COLUMN id SET DEFAULT nextval('public.salary_fines_id_seq'::regclass);


--
-- Name: salary_payments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salary_payments ALTER COLUMN id SET DEFAULT nextval('public.salary_payments_id_seq'::regclass);


--
-- Name: services id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.services ALTER COLUMN id SET DEFAULT nextval('public.services_id_seq'::regclass);


--
-- Name: shop_sale_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shop_sale_items ALTER COLUMN id SET DEFAULT nextval('public.shop_sale_items_id_seq'::regclass);


--
-- Name: shop_sales id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shop_sales ALTER COLUMN id SET DEFAULT nextval('public.shop_sales_id_seq'::regclass);


--
-- Name: staff_chat_attachments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_attachments ALTER COLUMN id SET DEFAULT nextval('public.staff_chat_attachments_id_seq'::regclass);


--
-- Name: staff_chat_messages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_messages ALTER COLUMN id SET DEFAULT nextval('public.staff_chat_messages_id_seq'::regclass);


--
-- Name: staff_chat_reactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_reactions ALTER COLUMN id SET DEFAULT nextval('public.staff_chat_reactions_id_seq'::regclass);


--
-- Name: staff_chat_read_cursors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_read_cursors ALTER COLUMN id SET DEFAULT nextval('public.staff_chat_read_cursors_id_seq'::regclass);


--
-- Name: stock_movements id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_movements ALTER COLUMN id SET DEFAULT nextval('public.stock_movements_id_seq'::regclass);


--
-- Name: suppliers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suppliers ALTER COLUMN id SET DEFAULT nextval('public.suppliers_id_seq'::regclass);


--
-- Name: symptoms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.symptoms ALTER COLUMN id SET DEFAULT nextval('public.symptoms_id_seq'::regclass);


--
-- Name: system_settings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings ALTER COLUMN id SET DEFAULT nextval('public.system_settings_id_seq'::regclass);


--
-- Name: task_checklists id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_checklists ALTER COLUMN id SET DEFAULT nextval('public.task_checklists_id_seq'::regclass);


--
-- Name: tasks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks ALTER COLUMN id SET DEFAULT nextval('public.tasks_id_seq'::regclass);


--
-- Name: transaction_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transaction_categories ALTER COLUMN id SET DEFAULT nextval('public.transaction_categories_id_seq'::regclass);


--
-- Name: user_role_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role_history ALTER COLUMN id SET DEFAULT nextval('public.user_role_history_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: warehouse_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_logs ALTER COLUMN id SET DEFAULT nextval('public.warehouse_logs_id_seq'::regclass);


--
-- Data for Name: action_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.action_logs (id, user_id, username, action_type, entity_type, entity_id, old_values, new_values, details, ip_address, user_agent, created_at) FROM stdin;
\.


--
-- Data for Name: appearance_tags; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.appearance_tags (id, name, sort_order, created_at) FROM stdin;
1	Зарядка	1	2026-03-03 17:47:45
2	Провод зарядки + мышь	2	2026-03-03 17:47:45
3	БУ	3	2026-03-03 17:47:45
4	Блок питания в коробке	4	2026-03-03 17:47:45
5	Насадка + провод	5	2026-03-03 17:47:45
6	Зарядное	6	2026-03-03 17:47:45
7	2 шт	7	2026-03-03 17:47:46
8	Зарядное + винты в коробке	8	2026-03-03 17:47:46
9	Блок питания	9	2026-03-03 17:47:46
10	4шт	10	2026-03-03 17:47:46
11	Сумка + кабель питания	11	2026-03-03 17:47:46
12	Зарядное + сумка	12	2026-03-03 17:47:46
13	Без зарядки	13	2026-03-03 17:47:47
14	Джойстик + диск Assasins Creed	14	2026-03-03 17:47:47
15	Коробка	15	2026-03-03 17:47:47
16	Сумка + зарядное	16	2026-03-03 17:47:47
17	Зарядное устройство	17	2026-03-03 17:47:47
18	Зарядное у ст	18	2026-03-03 17:47:47
19	+ корпус и новая видеокарта	19	2026-03-03 17:47:47
20	-	20	2026-03-03 17:47:47
21	+ картридж	21	2026-03-03 17:47:47
22	+ зарядное	22	2026-03-03 17:47:47
23	Задняя крышка не закреплена	23	2026-03-03 17:47:48
24	Не хватает болтов	24	2026-03-03 17:47:48
25	Зарядное + рюкзак	25	2026-03-03 17:47:48
26	Пакет + зарядное	26	2026-03-03 17:47:48
27	3 шт	27	2026-03-03 17:47:48
28	+ 2 картриджа	28	2026-03-03 17:47:48
29	285/283 - 5 шт	29	2026-03-03 17:47:48
30	Xerox 2030 - 1 шт	30	2026-03-03 17:47:48
31	CF-226X - 1шт.	31	2026-03-03 17:47:48
32	TK-1150 - 1 шт	32	2026-03-03 17:47:48
33	TK-5240Y - 1 шт	33	2026-03-03 17:47:48
34	Потертости	34	2026-03-03 17:47:48
35	Нет одного винта на задней крышке	35	2026-03-03 17:47:48
36	Сумка	36	2026-03-03 17:47:48
37	2	37	2026-03-03 17:47:48
38	2 шт. (один разобран)	38	2026-03-03 17:47:49
39	2 шт + провод + коробка	39	2026-03-03 17:47:49
40	Без боковой крышки	40	2026-03-03 17:47:49
41	Блоки питания	41	2026-03-03 17:47:49
42	Усилитель в разобранном состоянии	42	2026-03-03 17:47:49
43	2 манипулы + шланг	43	2026-03-03 17:47:49
44	Педаль	44	2026-03-03 17:47:49
45	Разбита матрица	45	2026-03-03 17:47:49
46	Коробка + пульт	46	2026-03-03 17:47:49
47	Фиолетовый	47	2026-03-03 17:47:50
48	Во время диагностики выявлена неисправность элементов питания	48	2026-03-03 17:47:50
49	Короткое замыкание сетевой платы	49	2026-03-03 17:47:50
50	Два usb-кабеля	50	2026-03-03 17:47:50
51	2 принтера	51	2026-03-03 17:47:50
52	Ключи	52	2026-03-03 17:47:50
53	+ драм картридж	53	2026-03-03 17:47:51
54	+ провод питания	54	2026-03-03 17:47:51
55	Сколы	55	2026-03-03 17:47:52
56	Без зарядного	56	2026-03-03 17:47:52
57	Без зарядкного	57	2026-03-03 17:47:52
58	Белый	58	2026-03-03 17:47:52
59	С зеленым пятном	59	2026-03-03 17:47:53
60	Розовая сумка + зарядное	60	2026-03-03 17:47:53
61	Новый	61	2026-03-03 17:47:53
62	С проводами	62	2026-03-03 17:47:53
63	Принтер в разобранном состоянии	63	2026-03-03 17:47:54
64	3 провода	64	2026-03-03 17:47:55
65	Ноутбук + зардное	65	2026-03-03 17:47:55
66	+ клавиатура и зарядное	66	2026-03-03 17:47:55
67	Наклейки	67	2026-03-03 17:47:56
68	Джойстик + стик	68	2026-03-03 17:47:56
69	Зарядное Buro	69	2026-03-03 17:47:56
70	БЕЗ ЗАРЯДКИ	70	2026-03-03 17:47:57
71	Манипула 1 шт	71	2026-03-03 17:47:57
72	+ доп. картридж	72	2026-03-03 17:47:57
73	Пробег 76347	73	2026-03-03 17:47:57
74	Пробег 18445	74	2026-03-03 17:47:58
75	Cумка	75	2026-03-03 17:47:58
76	Джойстик	76	2026-03-03 17:47:58
77	Кабель	77	2026-03-03 17:47:59
78	БЕЗ ЗАРЯДКИ и АКБ	78	2026-03-03 17:47:59
79	Флешка	79	2026-03-03 17:47:59
80	С сумкой	80	2026-03-03 17:47:59
81	В коробке	81	2026-03-03 17:48:00
82	Кабель питания	82	2026-03-03 17:48:01
83	Два джойстика	83	2026-03-03 17:48:01
84	Два провода	84	2026-03-03 17:48:01
85	Мышка	85	2026-03-03 17:48:01
86	C проводами	86	2026-03-03 17:48:01
87	Манипулы 2 шт.	87	2026-03-03 17:48:02
88	Джойстик + диск	88	2026-03-03 17:48:02
89	Печать	89	2026-03-03 17:48:02
90	Зарядное +сумка	90	2026-03-03 17:48:03
91	2 картриджа	91	2026-03-03 17:48:03
92	+ два джойстика	92	2026-03-03 17:48:03
93	Вытекает жидкость из БП	93	2026-03-03 17:48:03
94	БУ нет подсветки на матрицу	94	2026-03-03 17:48:03
95	Системный блок	95	2026-03-03 17:48:03
96	+ Материнская плата в коробке	96	2026-03-03 17:48:03
97	Джойстик + провода	97	2026-03-03 17:48:03
98	Зарядное 1 шт	98	2026-03-03 17:48:04
99	Блок питания 2 шт.	99	2026-03-03 17:48:04
100	Повреждена решетка радиатора	100	2026-03-03 17:48:05
101	БУ экран	101	2026-03-03 17:48:05
102	БУ царапины всрывалс	102	2026-03-03 17:48:05
103	Гейипад	103	2026-03-03 17:48:05
104	Без картриджа	104	2026-03-03 17:48:05
105	Мышь	105	2026-03-03 17:48:05
106	2 джойстика	106	2026-03-03 17:48:05
107	Без ножки	107	2026-03-03 17:48:05
108	3 диска	108	2026-03-03 17:48:06
109	Бу пролито ВИНО в центре клавиатуры	109	2026-03-03 17:48:06
110	Без боковых крышек	110	2026-03-03 17:48:06
111	БУ с зарядкой	111	2026-03-03 17:48:06
112	Красная сумка	112	2026-03-03 17:48:06
113	+3 модуля ОЗУ	113	2026-03-03 17:48:06
114	БУ с открытой крышкой	114	2026-03-03 17:48:06
115	В коробке с блоком питания	115	2026-03-03 17:48:07
116	+3 картриджа	116	2026-03-03 17:48:07
117	4 шт + тонер + чипы	117	2026-03-03 17:48:07
118	Диск Fifa19	118	2026-03-03 17:48:07
119	Зардное	119	2026-03-03 17:48:07
120	21 шт (Pantum 12 шт	120	2026-03-03 17:48:07
121	HP 4 шт. Kyocera 5 шт.)	121	2026-03-03 17:48:07
122	Без боковых крышек с джойстиком	122	2026-03-03 17:48:07
123	+новый АКБ	123	2026-03-03 17:48:07
124	+ джойстик	124	2026-03-03 17:48:08
125	+картридж	125	2026-03-03 17:48:08
126	Зарядное 2 шт	126	2026-03-03 17:48:08
127	Провода VGA + 220V	127	2026-03-03 17:48:08
128	Трещина на нижней крышке	128	2026-03-03 17:48:08
129	4 доп. картриджа + 4 чипа	129	2026-03-03 17:48:08
130	С проводом питания	130	2026-03-03 17:48:08
131	Без поддона	131	2026-03-03 17:48:09
132	В ящике	132	2026-03-03 17:48:09
133	Блок зарядки	133	2026-03-03 17:48:10
134	С проводом	134	2026-03-03 17:48:10
135	Акб	135	2026-03-03 17:48:10
136	+ зарядое	136	2026-03-03 17:48:11
137	Чёрный ssd	137	2026-03-03 17:48:11
138	С зарядкой	138	2026-03-03 17:48:11
139	6 шт.	139	2026-03-03 17:48:12
140	Чёрный	140	2026-03-03 17:48:12
141	Зарядное + АКБ	141	2026-03-03 17:48:13
142	Коробка с матрицей + зарядное	142	2026-03-03 17:48:13
143	2- геймпада	143	2026-03-03 17:48:13
144	Сумка+ коробка с запчастями	144	2026-03-03 17:48:13
145	2 шт.	145	2026-03-03 17:48:14
146	С кабелем питания	146	2026-03-03 17:48:14
147	Два провода USB	147	2026-03-03 17:48:14
148	Провод питания	148	2026-03-03 17:48:14
149	Материнская плата	149	2026-03-03 17:48:14
150	Кулер	150	2026-03-03 17:48:14
151	Оперативная память	151	2026-03-03 17:48:14
152	4 шт.	152	2026-03-03 17:48:14
153	Без боковой крышки + кабель HDMI	153	2026-03-03 17:48:14
154	Ручка в черном кейсе	154	2026-03-03 17:48:15
155	Матрица	155	2026-03-03 17:48:15
156	Б/у	156	2026-03-03 17:48:15
157	Клавиатура	157	2026-03-03 17:48:16
158	19 шт	158	2026-03-03 17:48:16
159	Джоqстик	159	2026-03-03 17:48:16
160	Диск Cyberpunk	160	2026-03-03 17:48:16
161	Белый корпус	161	2026-03-03 17:48:16
162	Зарядное + привод	162	2026-03-03 17:48:17
163	8 шт.	163	2026-03-03 17:48:18
164	2 геймпада	164	2026-03-03 17:48:19
165	2 видеокарты	165	2026-03-03 17:48:19
166	Мат.плата	166	2026-03-03 17:48:19
167	Процессор	167	2026-03-03 17:48:19
168	Оперативная память 1 шт.	168	2026-03-03 17:48:19
169	Клише	169	2026-03-03 17:48:20
170	Внешний HDD на 500 Gb	170	2026-03-03 17:48:20
171	Провод	171	2026-03-03 17:48:20
172	Без АКБ	172	2026-03-03 17:48:20
173	Не работает клавиатура	173	2026-03-03 17:48:20
174	МП Строительство	174	2026-03-03 17:48:20
175	58*22	175	2026-03-03 17:48:20
176	С чипом	176	2026-03-03 17:48:21
177	6 штук	177	2026-03-03 17:48:21
178	+ 3 картриджа	178	2026-03-03 17:48:21
179	Ноут у клиента	179	2026-03-03 17:48:21
180	3 шт.	180	2026-03-03 17:48:21
181	2 штуки	181	2026-03-03 17:48:21
182	1	182	2026-03-03 17:48:21
183	БП	183	2026-03-03 17:48:21
184	2 клише	184	2026-03-03 17:48:22
185	Шнур	185	2026-03-03 17:48:22
186	5 штук	186	2026-03-03 17:48:22
187	3	187	2026-03-03 17:48:22
188	Шнур питания	188	2026-03-03 17:48:22
189	+ Принтер Pantum	189	2026-03-03 17:48:23
190	4 шт	190	2026-03-03 17:48:23
191	Сколько стоит новый?	191	2026-03-03 17:48:23
192	Заберёт сегодня  вечером в 18:30	192	2026-03-03 17:48:23
193	Сломан	193	2026-03-03 17:48:23
194	ПРОВОД ПОГРЫЗАН собакой	194	2026-03-03 17:48:23
195	1. сыпется	195	2026-03-03 17:48:24
196	10 шт	196	2026-03-03 17:48:24
197	Чехол	197	2026-03-03 17:48:24
198	3 картриджа	198	2026-03-03 17:48:24
199	( 2 на заправку	199	2026-03-03 17:48:24
200	1 новый в принтере)	200	2026-03-03 17:48:24
201	1 шт	201	2026-03-03 17:48:24
202	2шт.	202	2026-03-03 17:48:24
203	Телефон (пример, без ПДн)	203	2026-03-03 17:48:24
204	2 шнура	204	2026-03-03 17:48:24
205	Чемодан	205	2026-03-03 17:48:24
206	8 шт	206	2026-03-03 17:48:24
207	ПК+принтер	207	2026-03-03 17:48:25
208	6шт	208	2026-03-03 17:48:25
209	59 А -5 шт	209	2026-03-03 17:48:26
210	ТК 1170-8 шт. 285 А -4 шт	210	2026-03-03 17:48:26
211	4 шт.+1шт(hp)	211	2026-03-03 17:48:26
212	Нет внешней крышки	212	2026-03-03 17:48:26
213	Лопатка	213	2026-03-03 17:48:27
214	Бывает включается и бывает нет	214	2026-03-03 17:48:27
215	Акб 2шт	215	2026-03-03 17:48:27
216	Сзу.	216	2026-03-03 17:48:27
217	+донор M5526cdw	217	2026-03-03 17:48:27
218	Полный комплект+камера	218	2026-03-03 17:48:28
219	Ризинки	219	2026-03-03 17:48:28
220	Лапа	220	2026-03-03 17:48:28
221	Лопасти	221	2026-03-03 17:48:28
222	СЗУ	222	2026-03-03 17:48:28
223	В разборе с зарядкой	223	2026-03-03 17:48:28
224	Опт.кабель	224	2026-03-03 17:48:28
225	Кабель RCA.	225	2026-03-03 17:48:28
226	Hdmi	226	2026-03-03 17:48:29
227	Диск.	227	2026-03-03 17:48:29
228	10+5+1	228	2026-03-03 17:48:29
229	Плеер	229	2026-03-03 17:48:29
230	Сзу	230	2026-03-03 17:48:29
231	Наушника	231	2026-03-03 17:48:29
232	Чехол.	232	2026-03-03 17:48:29
233	Трещина на рамке матрицы	233	2026-03-03 17:48:29
234	Отсутствует болт	234	2026-03-03 17:48:29
235	Был в другом сервисе.	235	2026-03-03 17:48:29
236	Без крышки АКБ	236	2026-03-03 17:48:30
237	Без крышки	237	2026-03-03 17:48:30
238	Сдвинута матрица.	238	2026-03-03 17:48:30
239	Б.П.	239	2026-03-03 17:48:31
240	3шт	240	2026-03-03 17:48:31
241	Пульт 3шт	241	2026-03-03 17:48:31
242	Инструкция.	242	2026-03-03 17:48:31
243	Пульт	243	2026-03-03 17:48:31
244	Бп	244	2026-03-03 17:48:31
245	Разобран	245	2026-03-03 17:48:32
246	Болты	246	2026-03-03 17:48:32
247	Зу.	247	2026-03-03 17:48:32
248	Следы влаги	248	2026-03-03 17:48:32
249	Топ-кейс	249	2026-03-03 17:48:32
250	Крышка матрицы	250	2026-03-03 17:48:32
251	Разъем	251	2026-03-03 17:48:32
252	Пробег 90647 стр.	252	2026-03-03 17:48:32
253	+ ноутбук MicroXperts	253	2026-03-03 17:48:32
254	---	254	2026-03-03 17:48:32
255	Болт внутри	255	2026-03-03 17:48:32
256	DDR3 4Gb	256	2026-03-03 17:48:32
257	Внешний SSD накопитель	257	2026-03-03 17:48:32
258	Чистка и установка ПО	258	2026-03-03 17:48:32
259	ЗУ	259	2026-03-03 17:48:33
260	Колонка	260	2026-03-03 17:48:33
261	Принтер	261	2026-03-03 17:48:33
262	Картридж.	262	2026-03-03 17:48:33
263	22 шт	263	2026-03-03 17:48:33
264	Сумка.	264	2026-03-03 17:48:33
265	Ноутбук	265	2026-03-03 17:48:33
266	Планшет	266	2026-03-03 17:48:33
267	Платы 2 шт.	267	2026-03-03 17:48:33
268	БП + плата	268	2026-03-03 17:48:33
269	+ картридж 2335	269	2026-03-03 17:48:33
270	SSD M2	270	2026-03-03 17:48:33
271	ОЗУ 2шт.	271	2026-03-03 17:48:33
272	Накопитель kingston 480Gb	272	2026-03-03 17:48:34
273	2шт. провод usb	273	2026-03-03 17:48:34
274	Коптер	274	2026-03-03 17:48:35
275	Пульт (без крышки).	275	2026-03-03 17:48:35
276	Ноутбук и жесткий диск	276	2026-03-03 17:48:35
277	Наушники	277	2026-03-03 17:48:35
278	Тример с зарядным устройством	278	2026-03-03 17:48:35
279	Ноут	279	2026-03-03 17:48:35
280	Комплект	280	2026-03-03 17:48:36
281	N10D11-N12513	281	2026-03-03 17:48:36
282	Коробка + шнур	282	2026-03-03 17:48:36
283	Системный блок - 2шт.	283	2026-03-03 17:48:36
284	2 дж	284	2026-03-03 17:48:36
285	Приставка	285	2026-03-03 17:48:36
286	Провод USB	286	2026-03-03 17:48:36
287	Пылесос	287	2026-03-03 17:48:36
288	ЗУ + ЗУ от другого пылесоса с АКБ.	288	2026-03-03 17:48:36
289	ОЗУ	289	2026-03-03 17:48:36
290	+ зарядное устройство	290	2026-03-03 17:48:36
291	Переходник hdmi	291	2026-03-03 17:48:37
292	Новые	292	2026-03-03 17:48:37
293	Сильно БУ	293	2026-03-03 17:48:37
294	PS4-3шт. PS5-3шт.	294	2026-03-03 17:48:37
295	Полный комплект.	295	2026-03-03 17:48:37
296	Ноут (разобран)	296	2026-03-03 17:48:38
297	Мат. плата	297	2026-03-03 17:48:38
298	Крышка задняя	298	2026-03-03 17:48:38
299	Ssd m2	299	2026-03-03 17:48:38
300	БЕЗ ЗАРЯДКИ НЕ РАБОТАЕТ	300	2026-03-03 17:48:38
301	В разборе	301	2026-03-03 17:48:38
302	Геймпад 1шт.	302	2026-03-03 17:48:38
303	Контакт (пример, без ПДн)	303	2026-03-03 17:48:39
304	Фотоаппарат	304	2026-03-03 17:48:39
305	Объектив.	305	2026-03-03 17:48:39
306	Диск с игрой The Crew 2	306	2026-03-03 17:48:39
307	ТВ	307	2026-03-03 17:48:39
308	Пульт.	308	2026-03-03 17:48:39
309	Машинка	309	2026-03-03 17:48:39
310	ЗУ.	310	2026-03-03 17:48:39
311	Без ЗУ	311	2026-03-03 17:48:39
312	Ноутбук.	312	2026-03-03 17:48:40
313	Геймпад с проводом	313	2026-03-03 17:48:40
314	СЗУ.	314	2026-03-03 17:48:40
315	Смартфон	315	2026-03-03 17:48:40
316	Коробка.	316	2026-03-03 17:48:40
317	Аппарат	317	2026-03-03 17:48:40
318	Объектив DX 18-55	318	2026-03-03 17:48:40
319	Ремешок.	319	2026-03-03 17:48:40
320	Телефон внешнего вида (пример 2)	320	2026-03-03 17:48:41
321	2 мфу + картридж 718	321	2026-03-03 17:48:41
322	Геймпад	322	2026-03-03 17:48:41
323	Кабель HDMI	323	2026-03-03 17:48:41
324	Кабель сетевой	324	2026-03-03 17:48:41
325	Апарат	325	2026-03-03 17:48:42
326	Сломана петля	326	2026-03-03 17:48:42
327	Драмкартридж	327	2026-03-03 17:48:42
328	Чипы 3 шт.	328	2026-03-03 17:48:42
329	Новая клавиатура	329	2026-03-03 17:48:42
330	Старый АКБ	330	2026-03-03 17:48:42
331	С чехлом	331	2026-03-03 17:48:42
332	Объектив EFS18-135	332	2026-03-03 17:48:42
333	Зарядное устройство Asus	333	2026-03-03 17:48:42
334	После удара	334	2026-03-03 17:48:42
335	Не хватает клавиш на клавиатуре	335	2026-03-03 17:48:42
336	Зарядное + принтер с usb кабелем	336	2026-03-03 17:48:42
337	Без зарядного устройства	337	2026-03-03 17:48:43
338	БП.	338	2026-03-03 17:48:43
339	С зарядным	339	2026-03-03 17:48:43
340	+ доп картридж	340	2026-03-03 17:48:43
341	Коробка + средство от накипи	341	2026-03-03 17:48:43
342	Плата в коробке	342	2026-03-03 17:48:44
343	Джойстик.	343	2026-03-03 17:48:44
344	Клавиатура(новая).	344	2026-03-03 17:48:44
345	Серая	345	2026-03-03 17:48:44
346	Ноутбук у клиента	346	2026-03-03 17:48:44
347	+картридж 725	347	2026-03-03 17:48:45
348	Квадрокоптер	348	2026-03-03 17:48:45
349	АКБ	349	2026-03-03 17:48:45
350	Ноутбук + зарядное	350	2026-03-03 17:48:45
351	Ждойстик	351	2026-03-03 17:48:45
352	SSD120	352	2026-03-03 17:48:45
353	DIMM*2.	353	2026-03-03 17:48:45
354	Внешний бокс	354	2026-03-03 17:48:45
355	Беспроводная мышь	355	2026-03-03 17:48:45
356	С 05.04 по 16.04	356	2026-03-03 17:48:46
357	Телефон	357	2026-03-03 17:48:46
358	ОПЛАЧЕНО 1200 руб.	358	2026-03-03 17:48:47
359	Картридж	359	2026-03-03 17:48:47
360	HDMI кабель	360	2026-03-03 17:48:47
361	Сетевой кабель	361	2026-03-03 17:48:47
362	2 пульта	362	2026-03-03 17:48:47
363	2 БП	363	2026-03-03 17:48:47
364	HDMI провод	364	2026-03-03 17:48:47
365	Трещина на крышке	365	2026-03-03 17:48:47
366	Черная	366	2026-03-03 17:48:47
367	Тв	367	2026-03-03 17:48:48
368	БУ залитый	368	2026-03-03 17:48:48
369	Пуль и коробка	369	2026-03-03 17:48:48
370	PS 4	370	2026-03-03 17:48:48
371	- 2 шт. PS 5 - 2 шт.	371	2026-03-03 17:48:48
372	Черный	372	2026-03-03 17:48:49
373	С	373	2026-03-03 17:48:49
374	Внешний HDD 1Tb	374	2026-03-03 17:48:49
375	Приствка + джойстик	375	2026-03-03 17:48:49
376	Зарядное устройство + клавиатура	376	2026-03-03 17:48:49
377	HP 83A - 6 шт	377	2026-03-03 17:48:49
378	HP505X-1шт	378	2026-03-03 17:48:49
379	Brother - 6 шт	379	2026-03-03 17:48:49
380	TK- 9 шт	380	2026-03-03 17:48:49
381	Материнская плата + процессор + кулер	381	2026-03-03 17:48:49
382	2 шт. ТК-1120 заправка + 3шт. PC-211 диагностика	382	2026-03-03 17:48:49
383	Manual	383	2026-03-03 17:48:49
384	Б.У	384	2026-03-03 17:48:49
385	Зарядное + коробка	385	2026-03-03 17:48:49
386	ОПЛАЧЕНО 1500	386	2026-03-03 17:48:49
387	ОПЛАЧЕНО	387	2026-03-03 17:48:49
388	С зарядкой + SSD Colorful 512 GB	388	2026-03-03 17:48:50
389	ОПЛАЧЕНО 1500 руб.	389	2026-03-03 17:48:50
390	Без лотка для бумаги	390	2026-03-03 17:48:50
391	Zalman 600W и FSP 550W	391	2026-03-03 17:48:50
392	Зарядное + джойстик	392	2026-03-03 17:48:50
393	Счёт (пример, без персональных данных)	393	2026-03-03 17:48:50
394	Без HDD	394	2026-03-03 17:48:50
395	CE410X - 3 шт	395	2026-03-03 17:48:50
396	CF462X - 1 шт. (желтый) / CE413	396	2026-03-03 17:48:50
397	CE411	397	2026-03-03 17:48:50
398	CE412	398	2026-03-03 17:48:50
399	CF411X	399	2026-03-03 17:48:50
400	CF410A	400	2026-03-03 17:48:50
401	CF410X	401	2026-03-03 17:48:50
402	CF412X	402	2026-03-03 17:48:50
403	CF413X	403	2026-03-03 17:48:50
404	Без лицевой панели	404	2026-03-03 17:48:50
405	Царапины	405	2026-03-03 17:48:51
406	Разбито стекло матрицы	406	2026-03-03 17:48:51
407	Сабвуфер + колонка	407	2026-03-03 18:55:29
408	Док-станция + блок питания	408	2026-03-03 18:55:29
409	Джойстик + запчасти от привода	409	2026-03-03 18:55:30
410	2 блока питания	410	2026-03-03 18:55:31
411	Мышь + клавиатура	411	2026-03-12 08:05:11
412	В наклейках	412	2026-03-13 12:44:41
413	Зарядное + рюкзак + сетевой модуль	413	2026-04-01 08:14:12.287211
\.


--
-- Data for Name: cash_transactions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.cash_transactions (id, category_id, amount, transaction_type, payment_method, description, order_id, payment_id, shop_sale_id, transaction_date, created_by_id, created_by_username, created_at, is_cancelled, cancelled_at, cancelled_reason, cancelled_by_id, cancelled_by_username, storno_of_id) FROM stdin;
\.


--
-- Data for Name: comment_attachments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.comment_attachments (id, comment_id, filename, file_path, file_size, mime_type, created_at) FROM stdin;
\.


--
-- Data for Name: customer_tokens; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.customer_tokens (id, customer_id, token, expires_at, created_at, last_used_at) FROM stdin;
\.


--
-- Data for Name: customer_wallet_transactions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.customer_wallet_transactions (id, customer_id, amount_cents, tx_type, source, order_id, payment_id, comment, created_by_id, created_by_username, created_at) FROM stdin;
\.


--
-- Data for Name: customers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.customers (id, name, phone, email, created_at, updated_at, wallet_cents, portal_password_changed, portal_enabled, portal_password_hash) FROM stdin;
\.


--
-- Data for Name: device_brands; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.device_brands (id, name, created_at, sort_order) FROM stdin;
1	Не указан	2026-03-03 17:47:45	0
2	-	2026-03-03 17:47:45	0
3	Intel	2026-03-03 17:47:45	0
4	Apple	2026-03-03 17:47:45	0
5	Sony	2026-03-03 17:47:45	0
6	Kyocera	2026-03-03 17:47:45	0
7	Xbox	2026-03-03 17:47:45	0
8	Indiba	2026-03-03 17:47:45	0
9	Bosh	2026-03-03 17:47:45	0
10	Vitek	2026-03-03 17:47:45	0
11	Asus	2026-03-03 17:47:45	0
12	BBQ	2026-03-03 17:47:45	0
13	Msi	2026-03-03 17:47:45	0
14	Thunderrobot	2026-03-03 17:47:45	0
15	HUAWEI	2026-03-03 17:47:45	0
16	Canon	2026-03-03 17:47:45	0
17	HP	2026-03-03 17:47:45	0
18	Appe	2026-03-03 17:47:45	0
19	Pantum	2026-03-03 17:47:45	0
20	Lenovo	2026-03-03 17:47:46	0
21	pantum	2026-03-03 17:47:46	0
22	Gigabite	2026-03-03 17:47:46	0
23	Katana 17	2026-03-03 17:47:46	0
24	Fellowes/Cactus	2026-03-03 17:47:46	0
25	Toshiba	2026-03-03 17:47:46	0
26	Honor	2026-03-03 17:47:46	0
27	Hp	2026-03-03 17:47:46	0
28	Xerox	2026-03-03 17:47:46	0
29	бн	2026-03-03 17:47:46	0
30	Polaris	2026-03-03 17:47:46	0
31	EXPE	2026-03-03 17:47:46	0
32	МФУ Brother	2026-03-03 17:47:46	0
33	LG	2026-03-03 17:47:47	0
34	Huawei	2026-03-03 17:47:47	0
35	RED Solution	2026-03-03 17:47:47	0
36	HP 117A	2026-03-03 17:47:47	0
37	ASUS TUF	2026-03-03 17:47:47	0
38	MSI	2026-03-03 17:47:47	0
39	Krups	2026-03-03 17:47:47	0
40	Samsung	2026-03-03 17:47:47	0
41	Delonghi	2026-03-03 17:47:48	0
42	Acer	2026-03-03 17:47:48	0
43	assida	2026-03-03 17:47:48	0
44	Bankosa, Dors	2026-03-03 17:47:49	0
45	Brother	2026-03-03 17:47:49	0
46	Dyson	2026-03-03 17:47:49	0
47	EItronik	2026-03-03 17:47:49	0
48	Cosmotools	2026-03-03 17:47:49	0
49	Thunderobot	2026-03-03 17:47:49	0
50	Hartens	2026-03-03 17:47:49	0
51	Ricoh	2026-03-03 17:47:49	0
52	Machcreltor	2026-03-03 17:47:50	0
53	XBOX	2026-03-03 17:47:50	0
54	ARDON	2026-03-03 17:47:50	0
55	Samsung/Hp	2026-03-03 17:47:50	0
56	Infinix	2026-03-03 17:47:50	0
57	Saeco	2026-03-03 17:47:50	0
58	HP и Pantum	2026-03-03 17:47:50	0
59	Samsung и Brother	2026-03-03 17:47:50	0
60	ASUS	2026-03-03 17:47:51	0
61	Delongi	2026-03-03 17:47:51	0
62	Xerox, Brother	2026-03-03 17:47:51	0
63	slim	2026-03-03 17:47:52	0
64	Maibenben	2026-03-03 17:47:52	0
65	Gygabyte	2026-03-03 17:47:52	0
66	lenovo	2026-03-03 17:47:52	0
67	HUAWAY	2026-03-03 17:47:52	0
68	Jura	2026-03-03 17:47:52	0
69	canon, samsung	2026-03-03 17:47:52	0
70	acer	2026-03-03 17:47:52	0
71	Brothrt	2026-03-03 17:47:53	0
72	DIGMA	2026-03-03 17:47:54	0
73	POSCenter	2026-03-03 17:47:54	0
74	Xerox и HP	2026-03-03 17:47:54	0
75	THOSIBA	2026-03-03 17:47:55	0
76	Trodat	2026-03-03 17:47:55	0
77	Steam Deck	2026-03-03 17:47:55	0
78	бх	2026-03-03 17:47:55	0
79	Р	2026-03-03 17:47:55	0
80	DORS	2026-03-03 17:47:57	0
81	Siemens	2026-03-03 17:47:57	0
82	Pioner	2026-03-03 17:47:57	0
83	Dell	2026-03-03 17:47:58	0
84	harman/kardon	2026-03-03 17:47:58	0
85	Cafitaly	2026-03-03 17:47:58	0
86	Samcung SCX-3400	2026-03-03 17:47:58	0
87	Son	2026-03-03 17:47:59	0
88	emachines	2026-03-03 17:47:59	0
89	JBL	2026-03-03 17:47:59	0
90	Krups и капсульная	2026-03-03 17:47:59	0
91	Neobihier	2026-03-03 17:47:59	0
92	ThinkPad	2026-03-03 17:47:59	0
93	Dr. Coffe	2026-03-03 17:47:59	0
94	jula	2026-03-03 17:48:00	0
95	Dr Coffee	2026-03-03 17:48:00	0
96	HP и Xpriner	2026-03-03 17:48:01	0
97	PlayStation	2026-03-03 17:48:01	0
98	Packerd Bell	2026-03-03 17:48:01	0
99	Inhouse	2026-03-03 17:48:01	0
100	Белый	2026-03-03 17:48:01	0
101	Рикта	2026-03-03 17:48:02	0
102	Moibenben	2026-03-03 17:48:02	0
103	Dere	2026-03-03 17:48:02	0
104	Ultrasonic	2026-03-03 17:48:02	0
105	DEXP	2026-03-03 17:48:03	0
106	Зарядное	2026-03-03 17:48:03	0
107	--	2026-03-03 17:48:03	0
108	Samsung и Acer	2026-03-03 17:48:04	0
109	Panasonic	2026-03-03 17:48:05	0
110	brother	2026-03-03 17:48:05	0
111	Haier	2026-03-03 17:48:06	0
112	Epson	2026-03-03 17:48:06	0
113	Philips	2026-03-03 17:48:06	0
114	3	2026-03-03 17:48:06	0
115	samsung	2026-03-03 17:48:07	0
116	GK mini	2026-03-03 17:48:07	0
117	печать	2026-03-03 17:48:07	0
118	PC-211	2026-03-03 17:48:07	0
119	KREZ	2026-03-03 17:48:08	0
120	Автомат	2026-03-03 17:48:08	0
121	Dexp	2026-03-03 17:48:08	0
122	Acer Predator	2026-03-03 17:48:09	0
123	Gigabyte	2026-03-03 17:48:09	0
124	sony	2026-03-03 17:48:09	0
125	Echips	2026-03-03 17:48:09	0
126	Katana	2026-03-03 17:48:10	0
127	TufGaming	2026-03-03 17:48:10	0
128	IdeaLpADl340	2026-03-03 17:48:10	0
129	spark	2026-03-03 17:48:11	0
130	PANTUM	2026-03-03 17:48:12	0
131	trodat	2026-03-03 17:48:12	0
132	SMART	2026-03-03 17:48:13	0
133	Sam4S	2026-03-03 17:48:13	0
134	Mechrev	2026-03-03 17:48:13	0
135	ThinBook	2026-03-03 17:48:13	0
136	Acer Aspire 3	2026-03-03 17:48:14	0
137	Tanshi	2026-03-03 17:48:14	0
138	автомат	2026-03-03 17:48:14	0
139	asus	2026-03-03 17:48:14	0
140	Soprano Titanium	2026-03-03 17:48:15	0
141	SAM4S	2026-03-03 17:48:15	0
142	Getac	2026-03-03 17:48:15	0
143	ручная	2026-03-03 17:48:15	0
144	HP, Kyocera	2026-03-03 17:48:15	0
145	kyocera	2026-03-03 17:48:15	0
146	MECHREV	2026-03-03 17:48:15	0
147	INNO3D	2026-03-03 17:48:15	0
148	EPSON	2026-03-03 17:48:15	0
149	geektech	2026-03-03 17:48:15	0
150	Tooshiba	2026-03-03 17:48:15	0
151	Лягушка	2026-03-03 17:48:16	0
152	Realme	2026-03-03 17:48:16	0
153	Thermaltake	2026-03-03 17:48:17	0
154	CHUWI	2026-03-03 17:48:17	0
155	Aorus	2026-03-03 17:48:18	0
156	Brother, HP	2026-03-03 17:48:18	0
157	De'Longhi	2026-03-03 17:48:19	0
158	EMachines	2026-03-03 17:48:19	0
159	Brother и HP	2026-03-03 17:48:19	0
160	Seco	2026-03-03 17:48:19	0
161	Transcend	2026-03-03 17:48:20	0
162	Seagate	2026-03-03 17:48:20	0
163	Prestigio	2026-03-03 17:48:21	0
164	OURUS	2026-03-03 17:48:21	0
165	Ps4	2026-03-03 17:48:22	0
166	НО	2026-03-03 17:48:22	0
167	283	2026-03-03 17:48:22	0
168	Deep Cool	2026-03-03 17:48:23	0
169	Gala	2026-03-03 17:48:23	0
170	eazy print	2026-03-03 17:48:23	0
171	MCI	2026-03-03 17:48:23	0
172	Think	2026-03-03 17:48:23	0
173	285	2026-03-03 17:48:23	0
174	Пантум	2026-03-03 17:48:23	0
175	Aguarius	2026-03-03 17:48:24	0
176	MI	2026-03-03 17:48:24	0
177	136А	2026-03-03 17:48:24	0
178	Nespreso	2026-03-03 17:48:24	0
179	Redmond	2026-03-03 17:48:25	0
180	Дерево	2026-03-03 17:48:25	0
181	Redmi	2026-03-03 17:48:25	0
182	KARCHER	2026-03-03 17:48:25	0
183	Medion	2026-03-03 17:48:25	0
184	Zanussi	2026-03-03 17:48:25	0
185	Perfomance	2026-03-03 17:48:25	0
186	Ресанта	2026-03-03 17:48:25	0
187	Xiaomi	2026-03-03 17:48:26	0
188	Goldstar	2026-03-03 17:48:26	0
189	Яндекс	2026-03-03 17:48:26	0
190	ГП-10 МО	2026-03-03 17:48:26	0
191	Pioneer	2026-03-03 17:48:26	0
192	клише	2026-03-03 17:48:26	0
193	ACER	2026-03-03 17:48:26	0
194	POCO	2026-03-03 17:48:27	0
195	CEM	2026-03-03 17:48:27	0
196	Ladies	2026-03-03 17:48:27	0
197	Fujifilm	2026-03-03 17:48:27	0
198	Microsoft	2026-03-03 17:48:27	0
199	INFINIX	2026-03-03 17:48:28	0
200	dji	2026-03-03 17:48:28	0
201	IEK	2026-03-03 17:48:28	0
202	Dr.Coffee	2026-03-03 17:48:28	0
203	Dreame	2026-03-03 17:48:28	0
204	ZET	2026-03-03 17:48:28	0
205	Audison	2026-03-03 17:48:28	0
206	NEVONA	2026-03-03 17:48:28	0
207	TEPLOCOM	2026-03-03 17:48:28	0
208	Zalman	2026-03-03 17:48:28	0
209	HP, Kyocera, Brother	2026-03-03 17:48:29	0
210	PAPAGO	2026-03-03 17:48:29	0
211	Ariston	2026-03-03 17:48:29	0
212	TEYES	2026-03-03 17:48:29	0
213	Trodar	2026-03-03 17:48:29	0
214	Rowenta	2026-03-03 17:48:30	0
215	Bosch	2026-03-03 17:48:30	0
216	HI	2026-03-03 17:48:30	0
217	Melitta	2026-03-03 17:48:30	0
218	KUPERSBERG	2026-03-03 17:48:30	0
219	BBK	2026-03-03 17:48:30	0
220	Teclast	2026-03-03 17:48:31	0
221	Pantum и Kyocera	2026-03-03 17:48:31	0
222	KENWOOD	2026-03-03 17:48:31	0
223	WodMax	2026-03-03 17:48:31	0
224	Player	2026-03-03 17:48:31	0
225	АТОЛ	2026-03-03 17:48:31	0
226	DIGIVOLT	2026-03-03 17:48:31	0
227	Harman	2026-03-03 17:48:31	0
228	Onviz	2026-03-03 17:48:31	0
229	Tufvassons	2026-03-03 17:48:31	0
230	Toyota	2026-03-03 17:48:31	0
231	ZYMA	2026-03-03 17:48:31	0
232	StarLine	2026-03-03 17:48:31	0
233	Mi	2026-03-03 17:48:31	0
234	BarTon	2026-03-03 17:48:31	0
235	KYOCERA	2026-03-03 17:48:31	0
236	Атол	2026-03-03 17:48:32	0
237	ARDOR	2026-03-03 17:48:32	0
238	KIMISO	2026-03-03 17:48:32	0
239	DeLonghi	2026-03-03 17:48:32	0
240	SVEN	2026-03-03 17:48:32	0
241	Sony PS4	2026-03-03 17:48:32	0
242	Packard Bell	2026-03-03 17:48:32	0
243	Harmann	2026-03-03 17:48:32	0
244	Honeywell	2026-03-03 17:48:32	0
245	General Satelite	2026-03-03 17:48:32	0
246	Karaoke	2026-03-03 17:48:32	0
247	D104	2026-03-03 17:48:32	0
248	LabelManager	2026-03-03 17:48:32	0
249	Renault	2026-03-03 17:48:32	0
250	Кофемашин	2026-03-03 17:48:32	0
251	King Audio	2026-03-03 17:48:32	0
252	Power	2026-03-03 17:48:32	0
253	PreSonus	2026-03-03 17:48:32	0
254	Imou	2026-03-03 17:48:33	0
255	Babylis	2026-03-03 17:48:33	0
256	Hasee	2026-03-03 17:48:33	0
257	Falcon Eye	2026-03-03 17:48:33	0
258	Aser	2026-03-03 17:48:33	0
259	Fusion	2026-03-03 17:48:33	0
260	ABK	2026-03-03 17:48:33	0
261	Tribit	2026-03-03 17:48:33	0
262	Ardor	2026-03-03 17:48:33	0
263	Roal Bakery	2026-03-03 17:48:33	0
264	Pauling	2026-03-03 17:48:33	0
265	GemiBook	2026-03-03 17:48:33	0
266	Vollrus	2026-03-03 17:48:33	0
267	NVidia	2026-03-03 17:48:33	0
268	Детская	2026-03-03 17:48:33	0
269	ETS,	2026-03-03 17:48:33	0
270	Bravo	2026-03-03 17:48:33	0
271	Beko	2026-03-03 17:48:33	0
272	Kitfort	2026-03-03 17:48:33	0
273	Kyosera	2026-03-03 17:48:33	0
274	Skyline	2026-03-03 17:48:33	0
275	Massage Stone	2026-03-03 17:48:33	0
276	Real	2026-03-03 17:48:33	0
277	KIWI	2026-03-03 17:48:34	0
278	X541U	2026-03-03 17:48:34	0
279	Mystery	2026-03-03 17:48:34	0
280	-Ginzzu	2026-03-03 17:48:34	0
281	Vacuum	2026-03-03 17:48:34	0
282	Yag Laser	2026-03-03 17:48:34	0
283	Panasonik	2026-03-03 17:48:34	0
284	Magner	2026-03-03 17:48:34	0
285	Накопитель	2026-03-03 17:48:34	0
286	Phillips	2026-03-03 17:48:34	0
287	Drone	2026-03-03 17:48:35	0
288	Lenova	2026-03-03 17:48:35	0
289	DEEBOT	2026-03-03 17:48:35	0
290	Hotpoint	2026-03-03 17:48:35	0
291	MarkLevinson	2026-03-03 17:48:35	0
292	CyberPower	2026-03-03 17:48:35	0
293	Tefal	2026-03-03 17:48:35	0
294	Энергия	2026-03-03 17:48:35	0
295	Электро-гитара	2026-03-03 17:48:35	0
296	DoCash	2026-03-03 17:48:35	0
297	Nissan	2026-03-03 17:48:35	0
298	SmartBeam	2026-03-03 17:48:35	0
299	nVidia	2026-03-03 17:48:35	0
300	HiBREW	2026-03-03 17:48:35	0
301	Бойлер	2026-03-03 17:48:35	0
302	Nesons	2026-03-03 17:48:35	0
303	MR	2026-03-03 17:48:35	0
304	Базар	2026-03-03 17:48:35	0
305	Kisan	2026-03-03 17:48:36	0
306	GeForce	2026-03-03 17:48:36	0
307	ZyXEL	2026-03-03 17:48:36	0
308	Pantum, HP	2026-03-03 17:48:36	0
309	DNS, SONY	2026-03-03 17:48:36	0
310	Xiami	2026-03-03 17:48:36	0
311	Hyawei	2026-03-03 17:48:36	0
312	Yanaha	2026-03-03 17:48:36	0
313	Deleghi	2026-03-03 17:48:36	0
314	Гироскутер	2026-03-03 17:48:37	0
315	Окатные ворота	2026-03-03 17:48:37	0
316	CoreBook X	2026-03-03 17:48:37	0
317	Элтех	2026-03-03 17:48:37	0
318	БУ	2026-03-03 17:48:37	0
319	Supra	2026-03-03 17:48:37	0
320	TOPAZ	2026-03-03 17:48:37	0
321	Erisson	2026-03-03 17:48:37	0
322	Электрокамин	2026-03-03 17:48:37	0
323	BORK	2026-03-03 17:48:37	0
324	Redmi Note 10S/Honor 10	2026-03-03 17:48:37	0
325	Shivaki	2026-03-03 17:48:37	0
326	AVR	2026-03-03 17:48:37	0
327	FIMI	2026-03-03 17:48:37	0
328	Ресанта 5000	2026-03-03 17:48:38	0
329	Comffi	2026-03-03 17:48:38	0
330	SCT-SHS	2026-03-03 17:48:38	0
331	Прессотерапии	2026-03-03 17:48:38	0
332	Yandex	2026-03-03 17:48:38	0
333	Катюша	2026-03-03 17:48:38	0
334	ECON	2026-03-03 17:48:38	0
335	От ТВ	2026-03-03 17:48:38	0
336	PS4	2026-03-03 17:48:38	0
337	ELtronic	2026-03-03 17:48:38	0
338	Ресонта	2026-03-03 17:48:38	0
339	Nikon	2026-03-03 17:48:39	0
340	ПК	2026-03-03 17:48:39	0
341	Robot Coupe	2026-03-03 17:48:39	0
342	BXG	2026-03-03 17:48:39	0
343	Пульт	2026-03-03 17:48:39	0
344	Wella	2026-03-03 17:48:39	0
345	HONOR	2026-03-03 17:48:39	0
346	Chuwi	2026-03-03 17:48:39	0
347	ViewSonic	2026-03-03 17:48:39	0
348	Sansung	2026-03-03 17:48:40	0
349	Nvidia	2026-03-03 17:48:40	0
350	Сис. блок	2026-03-03 17:48:40	0
351	CHUX	2026-03-03 17:48:40	0
352	Nokia	2026-03-03 17:48:40	0
353	SBM	2026-03-03 17:48:40	0
354	TCL	2026-03-03 17:48:40	0
355	Maunfeld	2026-03-03 17:48:40	0
356	KRUPS	2026-03-03 17:48:40	0
357	Midea	2026-03-03 17:48:40	0
358	Rolsen	2026-03-03 17:48:40	0
359	Fiero	2026-03-03 17:48:40	0
360	Стабилизатор	2026-03-03 17:48:40	0
361	BQ	2026-03-03 17:48:41	0
362	Nelefunken	2026-03-03 17:48:41	0
363	Olympus	2026-03-03 17:48:41	0
364	52v	2026-03-03 17:48:41	0
365	Kyocera, Pantum	2026-03-03 17:48:41	0
366	LG-2шт.	2026-03-03 17:48:41	0
367	NESONS	2026-03-03 17:48:41	0
368	canon	2026-03-03 17:48:41	0
369	Wolberg	2026-03-03 17:48:41	0
370	Nespresso	2026-03-03 17:48:42	0
371	Uniel	2026-03-03 17:48:42	0
372	NIVONA	2026-03-03 17:48:42	0
373	APC	2026-03-03 17:48:42	0
374	Orion	2026-03-03 17:48:42	0
375	SONY	2026-03-03 17:48:42	0
376	NANOASIA	2026-03-03 17:48:42	0
377	NEWTon	2026-03-03 17:48:42	0
378	OKI	2026-03-03 17:48:42	0
379	Thomson	2026-03-03 17:48:42	0
380	Nhunderobot	2026-03-03 17:48:43	0
381	Magnum	2026-03-03 17:48:43	0
382	CrossWave	2026-03-03 17:48:43	0
383	Tefal и Polaris	2026-03-03 17:48:43	0
384	IPOD	2026-03-03 17:48:43	0
385	HP + Canon	2026-03-03 17:48:43	0
386	MIE	2026-03-03 17:48:43	0
387	jura	2026-03-03 17:48:43	0
388	Пылесос	2026-03-03 17:48:44	0
389	Sony PS5	2026-03-03 17:48:44	0
390	DNS	2026-03-03 17:48:44	0
391	Сис. Блок	2026-03-03 17:48:44	0
392	SoundKing	2026-03-03 17:48:44	0
393	Huawey	2026-03-03 17:48:45	0
394	Воsch	2026-03-03 17:48:45	0
395	ЛОС	2026-03-03 17:48:45	0
396	Hubsan	2026-03-03 17:48:45	0
397	Zebra	2026-03-03 17:48:45	0
398	Dji	2026-03-03 17:48:45	0
399	BOSH	2026-03-03 17:48:45	0
400	JVC	2026-03-03 17:48:45	0
401	WD	2026-03-03 17:48:45	0
402	BENQ	2026-03-03 17:48:46	0
403	ECO	2026-03-03 17:48:46	0
404	Щетка	2026-03-03 17:48:46	0
405	Electrolux	2026-03-03 17:48:46	0
406	X-BOX	2026-03-03 17:48:46	0
407	Envision	2026-03-03 17:48:46	0
408	CF244A	2026-03-03 17:48:46	0
409	Kyocera и PaNTUM	2026-03-03 17:48:46	0
410	Scarlett	2026-03-03 17:48:46	0
411	Kiniso	2026-03-03 17:48:46	0
412	VX-1800	2026-03-03 17:48:46	0
413	DJI	2026-03-03 17:48:46	0
414	Dr.pen	2026-03-03 17:48:46	0
415	Nanasia	2026-03-03 17:48:46	0
416	Плата	2026-03-03 17:48:46	0
417	Hi	2026-03-03 17:48:46	0
418	Urovo	2026-03-03 17:48:47	0
419	Smartbuy	2026-03-03 17:48:47	0
420	Mavic	2026-03-03 17:48:47	0
421	Xenyx	2026-03-03 17:48:47	0
422	Vitesse	2026-03-03 17:48:47	0
423	MobiStamps	2026-03-03 17:48:47	0
424	Jaguar	2026-03-03 17:48:47	0
425	Eufy	2026-03-03 17:48:47	0
426	Slinex	2026-03-03 17:48:47	0
427	Триколор	2026-03-03 17:48:47	0
428	Centek Air	2026-03-03 17:48:47	0
429	Ruself	2026-03-03 17:48:47	0
430	Skycoocer	2026-03-03 17:48:48	0
431	PAPAGO!	2026-03-03 17:48:48	0
432	CENTEK	2026-03-03 17:48:48	0
433	РЕСАНТА	2026-03-03 17:48:48	0
434	Mirandi	2026-03-03 17:48:48	0
435	Brayer	2026-03-03 17:48:48	0
436	Braun	2026-03-03 17:48:48	0
437	PS	2026-03-03 17:48:48	0
438	Akai	2026-03-03 17:48:48	0
439	---	2026-03-03 17:48:48	0
440	Chiftec	2026-03-03 17:48:48	0
441	Alive	2026-03-03 17:48:48	0
442	Aсer	2026-03-03 17:48:48	0
443	MS	2026-03-03 17:48:48	0
444	Pantu 211	2026-03-03 17:48:48	0
445	Radeon	2026-03-03 17:48:48	0
446	Harper	2026-03-03 17:48:49	0
447	BOSCH	2026-03-03 17:48:49	0
448	SP	2026-03-03 17:48:49	0
449	Системный блок	2026-03-03 17:48:49	0
450	Noname	2026-03-03 17:48:49	0
451	LG 42PW450	2026-03-03 17:48:49	0
452	Crups	2026-03-03 17:48:49	0
453	Play Syayion	2026-03-03 17:48:49	0
454	Rexel	2026-03-03 17:48:50	0
455	Ноутбук Asus	2026-03-03 17:48:50	0
456	Voltron	2026-03-03 17:48:50	0
457	Deli	2026-03-03 18:55:29	0
458	Marinex	2026-03-03 18:55:29	0
459	Tuvio	2026-03-03 18:55:29	0
460	Dayson	2026-03-03 18:55:29	0
461	Kodak	2026-03-03 18:55:30	0
462	Bork	2026-03-03 18:55:31	0
463	Samsug	2026-04-06 12:59:19.573755	1
\.


--
-- Data for Name: device_types; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.device_types (id, name, created_at, sort_order) FROM stdin;
1	Не указан	2026-03-03 17:47:45	0
2	-	2026-03-03 17:47:45	0
3	Кофемашина	2026-03-03 17:47:45	0
4	Печать	2026-03-03 17:47:45	0
5	ноутбук смартбук	2026-03-03 17:47:45	0
6	Макбук	2026-03-03 17:47:45	0
7	Джойстики	2026-03-03 17:47:45	0
8	МФУ	2026-03-03 17:47:45	0
9	Игровая консоль	2026-03-03 17:47:45	0
10	Ps4	2026-03-03 17:47:45	0
11	Печати	2026-03-03 17:47:45	0
12	Парогенератор	2026-03-03 17:47:45	0
13	Микроволновка	2026-03-03 17:47:45	0
14	Принтер	2026-03-03 17:47:45	0
15	Сервер	2026-03-03 17:47:45	0
16	Системный блок	2026-03-03 17:47:45	0
17	Косметологический аппарат	2026-03-03 17:47:45	0
18	Утюг	2026-03-03 17:47:45	0
19	Робот-пылесос	2026-03-03 17:47:45	0
20	Ноутбук	2026-03-03 17:47:45	0
21	POS-принтер	2026-03-03 17:47:45	0
22	Телевизор	2026-03-03 17:47:45	0
23	СГУ	2026-03-03 17:47:45	0
24	Картриджи	2026-03-03 17:47:45	0
25	Картридж	2026-03-03 17:47:45	0
26	Принтеры	2026-03-03 17:47:45	0
27	Клише	2026-03-03 17:47:46	0
28	Видиокарта	2026-03-03 17:47:46	0
29	Шредеры	2026-03-03 17:47:46	0
30	Моноблок	2026-03-03 17:47:46	0
31	Обогреватель	2026-03-03 17:47:46	0
32	Плата	2026-03-03 17:47:46	0
33	кулинарные приборы 3 шт.	2026-03-03 17:47:46	0
34	Системный блок 3 шт	2026-03-03 17:47:46	0
35	Геймпад ps 5	2026-03-03 17:47:46	0
36	Пылесос	2026-03-03 17:47:47	0
37	HP 117A	2026-03-03 17:47:47	0
38	ноутбук	2026-03-03 17:47:47	0
39	печать	2026-03-03 17:47:47	0
40	Штамп	2026-03-03 17:47:47	0
41	Жесткий диск	2026-03-03 17:47:48	0
42	картриджи	2026-03-03 17:47:48	0
43	POS-терминал	2026-03-03 17:47:48	0
44	принтер	2026-03-03 17:47:48	0
45	Счётчик купюр	2026-03-03 17:47:48	0
46	Рентген аппарат	2026-03-03 17:47:49	0
47	Счетчик Банкнот 2 шт.	2026-03-03 17:47:49	0
48	Фен, плойка,пылесос\\пылесос	2026-03-03 17:47:49	0
49	Плата от домашнего кинотеатра	2026-03-03 17:47:49	0
50	Диодный лазер	2026-03-03 17:47:49	0
51	печати	2026-03-03 17:47:49	0
52	POS-принтер \\ Кипер	2026-03-03 17:47:49	0
53	Геймпад	2026-03-03 17:47:50	0
54	Джойстике	2026-03-03 17:47:50	0
55	Ps5	2026-03-03 17:47:50	0
56	SSD	2026-03-03 17:47:50	0
57	Часы	2026-03-03 17:47:50	0
58	Принтеры 2 шт.	2026-03-03 17:47:50	0
59	Принтеры 2 шт	2026-03-03 17:47:50	0
60	Штампы	2026-03-03 17:47:51	0
61	Печати 2 шт	2026-03-03 17:47:51	0
62	Принтер Pantum	2026-03-03 17:47:51	0
63	картридж	2026-03-03 17:47:51	0
64	Принетр	2026-03-03 17:47:51	0
65	Принтеры 3 шт.	2026-03-03 17:47:51	0
66	Игрова	2026-03-03 17:47:51	0
67	Видеокарта	2026-03-03 17:47:52	0
68	Клише + печать	2026-03-03 17:47:52	0
69	Системный блок + монитор	2026-03-03 17:47:53	0
70	Системный блок в разобранном состоянии	2026-03-03 17:47:54	0
71	Кассовый модуль	2026-03-03 17:47:54	0
72	Флэшка	2026-03-03 17:47:54	0
73	Драм DR-2335	2026-03-03 17:47:56	0
74	Джойстик	2026-03-03 17:47:56	0
75	клише	2026-03-03 17:47:56	0
76	Принтер и ноутбук	2026-03-03 17:47:56	0
77	Mcbook	2026-03-03 17:47:56	0
78	M1212nf	2026-03-03 17:47:56	0
79	Драм картридж	2026-03-03 17:47:56	0
80	Копировальный аппарат	2026-03-03 17:47:57	0
81	Счетчик банкнот	2026-03-03 17:47:57	0
82	Инвертор от кондиционера	2026-03-03 17:47:57	0
83	Диодный Лазер	2026-03-03 17:47:57	0
84	Нотбук	2026-03-03 17:47:58	0
85	Колонка	2026-03-03 17:47:58	0
86	Икромёт	2026-03-03 17:47:58	0
87	системный блок	2026-03-03 17:47:58	0
88	Dualsens	2026-03-03 17:47:59	0
89	Кофемашины	2026-03-03 17:47:59	0
90	Плата авто	2026-03-03 17:47:59	0
91	pantum 420	2026-03-03 17:48:00	0
92	Игровая приставка	2026-03-03 17:48:01	0
93	Кофемашина капсульная	2026-03-03 17:48:01	0
94	штамп	2026-03-03 17:48:02	0
95	аппарат	2026-03-03 17:48:02	0
96	iMac	2026-03-03 17:48:02	0
97	Аппарат фоноворез	2026-03-03 17:48:02	0
98	штампы	2026-03-03 17:48:03	0
99	Игровая приставка ПС5	2026-03-03 17:48:03	0
100	Ноутбуки	2026-03-03 17:48:04	0
101	Увлажнитель воздуха	2026-03-03 17:48:04	0
102	Ps 5	2026-03-03 17:48:05	0
103	Жесткие диски	2026-03-03 17:48:06	0
104	системны блок	2026-03-03 17:48:06	0
105	Проектор	2026-03-03 17:48:06	0
106	Системный блок МИНИ	2026-03-03 17:48:06	0
107	deLongi	2026-03-03 17:48:07	0
108	Мини ПК	2026-03-03 17:48:07	0
109	мини ПК	2026-03-03 17:48:07	0
110	кофемашина	2026-03-03 17:48:07	0
111	Pantum	2026-03-03 17:48:07	0
112	ps4	2026-03-03 17:48:08	0
113	Сист. блок	2026-03-03 17:48:08	0
114	Принтер, ноутбук	2026-03-03 17:48:09	0
115	джойстик	2026-03-03 17:48:09	0
116	Лазерный аппарат	2026-03-03 17:48:09	0
117	PlayStation	2026-03-03 17:48:10	0
118	POS принтер	2026-03-03 17:48:10	0
119	Манипула	2026-03-03 17:48:10	0
120	PS4	2026-03-03 17:48:10	0
121	Lenovo	2026-03-03 17:48:10	0
122	--	2026-03-03 17:48:11	0
123	Kyocera	2026-03-03 17:48:11	0
124	Ssd	2026-03-03 17:48:11	0
125	факсисмиле	2026-03-03 17:48:12	0
126	факсимиле	2026-03-03 17:48:12	0
127	POS-принтеры	2026-03-03 17:48:13	0
128	Печать, картриджи	2026-03-03 17:48:13	0
129	Системны блок мини	2026-03-03 17:48:13	0
130	Сист блок мини	2026-03-03 17:48:14	0
131	DualSense	2026-03-03 17:48:14	0
132	Материнская плата	2026-03-03 17:48:14	0
133	видеокарта	2026-03-03 17:48:15	0
134	Факсимиле	2026-03-03 17:48:16	0
135	смартфон	2026-03-03 17:48:16	0
136	Картриджи, драмы	2026-03-03 17:48:17	0
137	автомат	2026-03-03 17:48:18	0
138	Xerox	2026-03-03 17:48:19	0
139	Два принтера + картридж	2026-03-03 17:48:19	0
140	Комплектующие ПК	2026-03-03 17:48:19	0
141	Внешний HDD	2026-03-03 17:48:20	0
142	HDD	2026-03-03 17:48:20	0
143	электронный	2026-03-03 17:48:21	0
144	Игровая приставка ПС4	2026-03-03 17:48:22	0
145	Пчеть	2026-03-03 17:48:22	0
146	Картридж-	2026-03-03 17:48:22	0
147	принитер	2026-03-03 17:48:23	0
148	Светодиодная лента	2026-03-03 17:48:23	0
149	аккумулятор на ноут	2026-03-03 17:48:24	0
150	Нотубук	2026-03-03 17:48:24	0
151	плата	2026-03-03 17:48:24	0
152	Зарядное устройство	2026-03-03 17:48:24	0
153	Ручной-пылесос	2026-03-03 17:48:25	0
154	Аудиоколонка	2026-03-03 17:48:25	0
155	Смартфон	2026-03-03 17:48:25	0
156	ПК+принтер LP58	2026-03-03 17:48:25	0
157	Блок питания	2026-03-03 17:48:25	0
158	Аккустическая система	2026-03-03 17:48:25	0
159	Плата кондиционера	2026-03-03 17:48:25	0
160	Фен	2026-03-03 17:48:25	0
161	Стабилизатор	2026-03-03 17:48:25	0
162	печ	2026-03-03 17:48:26	0
163	Платы	2026-03-03 17:48:26	0
164	Стерилизатор воздушный	2026-03-03 17:48:26	0
165	Фотоаппарат	2026-03-03 17:48:26	0
166	Мультиметр	2026-03-03 17:48:27	0
167	Ультразвуковой аппарат	2026-03-03 17:48:27	0
168	Квадрокоптер	2026-03-03 17:48:28	0
169	Аудио-преобразователь	2026-03-03 17:48:28	0
170	ПК	2026-03-03 17:48:29	0
171	Видеорегистратор	2026-03-03 17:48:29	0
172	Плата управления	2026-03-03 17:48:29	0
173	Автомагнитола	2026-03-03 17:48:29	0
174	Аудио-плеер	2026-03-03 17:48:29	0
175	Штамп рекламный	2026-03-03 17:48:29	0
176	З.У. ноутбука	2026-03-03 17:48:29	0
177	Фен для волос	2026-03-03 17:48:30	0
178	Джостик XBOX	2026-03-03 17:48:30	0
179	Объектив	2026-03-03 17:48:30	0
180	Мультиварка	2026-03-03 17:48:30	0
181	Индукционая-плита	2026-03-03 17:48:30	0
182	Монитор	2026-03-03 17:48:31	0
183	Сканер штрихкодов	2026-03-03 17:48:31	0
184	Электропривод штор.	2026-03-03 17:48:31	0
185	БП	2026-03-03 17:48:31	0
186	Плата от магнитола	2026-03-03 17:48:31	0
187	Брелок автосигнализации	2026-03-03 17:48:31	0
188	ТВ-приставка	2026-03-03 17:48:31	0
189	Саббуфер	2026-03-03 17:48:32	0
190	Усилитель	2026-03-03 17:48:32	0
191	ТВ	2026-03-03 17:48:32	0
192	Планшет	2026-03-03 17:48:32	0
193	Усилитель авто	2026-03-03 17:48:32	0
194	МФУ струйный	2026-03-03 17:48:32	0
195	Пульт управления	2026-03-03 17:48:32	0
196	Камера	2026-03-03 17:48:33	0
197	Утюжок	2026-03-03 17:48:33	0
198	Монитор домофона	2026-03-03 17:48:33	0
199	HP Color 150a	2026-03-03 17:48:33	0
200	Джостик	2026-03-03 17:48:33	0
201	Портативная мини-система	2026-03-03 17:48:33	0
202	Миксер планетарный	2026-03-03 17:48:33	0
203	Автомобильное ЗУ	2026-03-03 17:48:33	0
204	Видекарта	2026-03-03 17:48:33	0
205	Машинка	2026-03-03 17:48:33	0
206	Платы управления	2026-03-03 17:48:33	0
207	Sony	2026-03-03 17:48:33	0
208	Печь	2026-03-03 17:48:33	0
209	монитор	2026-03-03 17:48:33	0
210	Плата от компьютера	2026-03-03 17:48:33	0
211	ролик захвата SCX4200	2026-03-03 17:48:33	0
212	Планщет	2026-03-03 17:48:34	0
213	Samsun	2026-03-03 17:48:34	0
214	ПРИНТЕР	2026-03-03 17:48:34	0
215	Автомобильный пылесос	2026-03-03 17:48:34	0
216	Аппарат	2026-03-03 17:48:34	0
217	Теле	2026-03-03 17:48:34	0
218	Накопитель	2026-03-03 17:48:34	0
219	Ноутбук, наушники	2026-03-03 17:48:35	0
220	Asus	2026-03-03 17:48:35	0
221	Джостик PS5	2026-03-03 17:48:35	0
222	Джостик PS4	2026-03-03 17:48:35	0
223	Iphone	2026-03-03 17:48:35	0
224	Тример	2026-03-03 17:48:35	0
225	Электро-гитара	2026-03-03 17:48:35	0
226	Джойсик	2026-03-03 17:48:35	0
227	ШГУ	2026-03-03 17:48:35	0
228	Проэктор	2026-03-03 17:48:35	0
229	Весы	2026-03-03 17:48:35	0
230	Нетбук	2026-03-03 17:48:36	0
231	Терминал	2026-03-03 17:48:36	0
232	МФУ 2 шт.	2026-03-03 17:48:36	0
233	Приставка	2026-03-03 17:48:36	0
234	Домашний кинотеатр	2026-03-03 17:48:36	0
235	Ноутбук-планшет	2026-03-03 17:48:37	0
236	Гироскутер	2026-03-03 17:48:37	0
237	Ресанта	2026-03-03 17:48:37	0
238	Отбеливатель	2026-03-03 17:48:37	0
239	Индукционная плита	2026-03-03 17:48:37	0
240	Камин	2026-03-03 17:48:37	0
241	Бесперебойник	2026-03-03 17:48:37	0
242	плита	2026-03-03 17:48:38	0
243	Электронный замок	2026-03-03 17:48:38	0
244	Кофе-машина	2026-03-03 17:48:38	0
245	консоль	2026-03-03 17:48:38	0
246	Узел термозакрепления	2026-03-03 17:48:38	0
247	Контроллер солнечных батарей	2026-03-03 17:48:39	0
248	Блендер	2026-03-03 17:48:39	0
249	Сушилка для рук 2шт.	2026-03-03 17:48:39	0
250	Холодильник	2026-03-03 17:48:39	0
251	Пульт	2026-03-03 17:48:39	0
252	Дрон	2026-03-03 17:48:39	0
253	Машинка-игрушка	2026-03-03 17:48:39	0
254	Машинка для стрижки	2026-03-03 17:48:39	0
255	Системный блок.	2026-03-03 17:48:40	0
256	Счётчик банкнот	2026-03-03 17:48:40	0
257	Индукционная-плита	2026-03-03 17:48:40	0
258	Плата упраления	2026-03-03 17:48:41	0
259	DVD-плеер	2026-03-03 17:48:41	0
260	Радио-пульт	2026-03-03 17:48:41	0
261	725	2026-03-03 17:48:41	0
262	Системный блок + видеокарта	2026-03-03 17:48:42	0
263	Магнитола	2026-03-03 17:48:42	0
264	Кофемашинка	2026-03-03 17:48:42	0
265	Сист блок	2026-03-03 17:48:42	0
266	DVD плеер	2026-03-03 17:48:42	0
267	Компрессор	2026-03-03 17:48:42	0
268	Принтер цветной	2026-03-03 17:48:42	0
269	струйный МФУ	2026-03-03 17:48:42	0
270	Микроволновки 2 шт. серебристые	2026-03-03 17:48:42	0
271	Ноутбук + мфу	2026-03-03 17:48:42	0
272	Чайник(Deerma), колонка (Алиса)	2026-03-03 17:48:43	0
273	Активный авто-саббуфер	2026-03-03 17:48:43	0
274	Парогенераторы	2026-03-03 17:48:43	0
275	Плеер	2026-03-03 17:48:43	0
276	Brother	2026-03-03 17:48:43	0
277	Фен и плойка для волос	2026-03-03 17:48:43	0
278	Принтер + МФУ	2026-03-03 17:48:43	0
279	Отпариватель	2026-03-03 17:48:43	0
280	Saeco	2026-03-03 17:48:43	0
281	Принтер струйный	2026-03-03 17:48:44	0
282	Сис. Блок	2026-03-03 17:48:44	0
283	Акустическая система	2026-03-03 17:48:44	0
284	Колонка Алиса	2026-03-03 17:48:44	0
285	Macbook	2026-03-03 17:48:44	0
286	Чернила	2026-03-03 17:48:45	0
287	Крмбайн	2026-03-03 17:48:45	0
288	Кофемолка	2026-03-03 17:48:45	0
289	Сканер штрих-кодов	2026-03-03 17:48:45	0
290	Стабиллизатор	2026-03-03 17:48:45	0
291	Системный блок (мини)	2026-03-03 17:48:45	0
292	Муз. центр	2026-03-03 17:48:45	0
293	Плата от эл. духовки	2026-03-03 17:48:45	0
294	Геймпад PS4	2026-03-03 17:48:46	0
295	CF244A	2026-03-03 17:48:46	0
296	Провод	2026-03-03 17:48:46	0
297	Телефон	2026-03-03 17:48:46	0
298	Контактная сварка	2026-03-03 17:48:46	0
299	Kyocera и PaNTUM	2026-03-03 17:48:46	0
300	DVD	2026-03-03 17:48:46	0
301	Термопод	2026-03-03 17:48:46	0
302	колонка	2026-03-03 17:48:46	0
303	Плитка индукционная	2026-03-03 17:48:46	0
304	Компьютер	2026-03-03 17:48:46	0
305	HP	2026-03-03 17:48:46	0
306	ТВ приставка	2026-03-03 17:48:46	0
307	Бойлер	2026-03-03 17:48:46	0
308	ТСД	2026-03-03 17:48:47	0
309	Принет	2026-03-03 17:48:47	0
310	Микшер	2026-03-03 17:48:47	0
311	Скороварка	2026-03-03 17:48:47	0
312	Домофон	2026-03-03 17:48:47	0
313	Пианино	2026-03-03 17:48:47	0
314	Приставка триколор 2шт	2026-03-03 17:48:47	0
315	Пртинтер	2026-03-03 17:48:47	0
316	Блок питания от водяного фильтра	2026-03-03 17:48:47	0
317	Заказ картриджа HP44A	2026-03-03 17:48:48	0
318	геймпад	2026-03-03 17:48:48	0
319	Соковыжималка	2026-03-03 17:48:48	0
320	Термопот	2026-03-03 17:48:48	0
321	Парогенератор Braun	2026-03-03 17:48:48	0
322	МФУ цветной + нужна печать SHADI	2026-03-03 17:48:48	0
323	Ноутук	2026-03-03 17:48:48	0
324	Хлебопечка	2026-03-03 17:48:48	0
325	Плата от синтезатора	2026-03-03 17:48:48	0
326	Пульт от ТВ	2026-03-03 17:48:48	0
327	Плита	2026-03-03 17:48:48	0
328	Проиграватель патефон	2026-03-03 17:48:48	0
329	Сист. блок mimi	2026-03-03 17:48:48	0
330	HDCVI регистратор	2026-03-03 17:48:48	0
331	Яндекс станция	2026-03-03 17:48:48	0
332	Индукционные плитки	2026-03-03 17:48:48	0
333	Струйный принтер	2026-03-03 17:48:48	0
334	Флэш накопитель	2026-03-03 17:48:49	0
335	Электронный дверной замок	2026-03-03 17:48:49	0
336	Лазер	2026-03-03 17:48:49	0
337	геймпад PS4	2026-03-03 17:48:49	0
338	Приставка PS4	2026-03-03 17:48:49	0
339	Мфу	2026-03-03 17:48:49	0
340	Sony PS4	2026-03-03 17:48:49	0
341	Игровая консоль PS4	2026-03-03 17:48:49	0
342	Системный блок Elton	2026-03-03 17:48:50	0
343	МФУ HP M28W, ноутбук Acer Nitro 5	2026-03-03 17:48:50	0
344	Уничтожитель бумаги	2026-03-03 17:48:50	0
345	Консоль PS4 Slim	2026-03-03 17:48:50	0
346	Оплачено	2026-03-03 17:48:50	0
347	Шредер	2026-03-03 18:55:29	0
348	Колонки	2026-03-03 18:55:29	0
349	Мясорубка	2026-03-03 18:55:29	0
350	Пластина массажа	2026-03-03 18:55:29	0
351	Ручной пылесос	2026-03-03 18:55:29	0
352	Стабилизаторы	2026-03-03 18:55:29	0
353	Стоматологоческий рентген	2026-03-03 18:55:30	0
354	Xbox one	2026-03-03 18:55:30	0
355	Видеорегистратор "Зеркало"	2026-03-03 18:55:30	0
356	Вафельница	2026-03-03 18:55:31	0
357	Заказ печати	2026-03-04 12:37:57	1
358	Заказ клише	2026-03-10 14:04:30	2
359	Заказ печатей	2026-03-11 14:56:57	3
360	Гриль	2026-03-13 14:48:17	4
361	Заправка картриджей	2026-03-13 15:53:59	5
362	Заказ факсимиле	2026-03-19 14:33:17	6
363	Заказ штампов	2026-03-24 14:54:15	7
364	Синхрофазатрон	2026-03-31 07:46:14.199813	8
\.


--
-- Data for Name: devices; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.devices (id, customer_id, device_type_id, device_brand_id, serial_number, created_at, password, symptom_tags, appearance_tags, comment) FROM stdin;
\.


--
-- Data for Name: general_settings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.general_settings (id, org_name, phone, address, inn, ogrn, logo_url, currency, country, updated_at, default_warranty_days, timezone_offset, mail_server, mail_port, mail_use_tls, mail_use_ssl, mail_username, mail_password, mail_default_sender, mail_timeout, close_print_mode, auto_email_order_accepted, auto_email_status_update, auto_email_order_ready, auto_email_order_closed, sms_enabled, telegram_enabled, signature_name, signature_position, director_email, auto_email_director_order_accepted, auto_email_director_order_closed) FROM stdin;
1	Nika Service CRM Demo	+7 (900) 000-00-00	Demo address				RUB	Россия	2025-11-27 15:44:30	30	3		587	1	0			Nika CRM Demo <noreply@example.com>	3	choice	1	1	1	1	0	0	Demo Director	Director	director@example.com	1	1
\.


--
-- Data for Name: inventory; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inventory (id, name, inventory_date, status, notes, created_by, created_at, completed_at) FROM stdin;
\.


--
-- Data for Name: inventory_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inventory_items (id, inventory_id, part_id, stock_quantity, actual_quantity, difference, notes, created_at) FROM stdin;
\.


--
-- Data for Name: managers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.managers (id, name, created_at, salary_rule_type, salary_rule_value, active, comment, updated_at, user_id, salary_percent_services, salary_percent_parts, salary_percent_shop_parts) FROM stdin;
7	Demo Manager	2026-04-07 20:10:55.118104	percent	10	1	\N	\N	9	\N	\N	\N
\.


--
-- Data for Name: masters; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.masters (id, name, created_at, salary_rule_type, salary_rule_value, active, comment, updated_at, user_id, salary_percent_services, salary_percent_parts, salary_percent_shop_parts) FROM stdin;
5	Demo Master	2026-04-07 20:10:55.121069	percent	20	1	\N	\N	10	\N	\N	\N
\.


--
-- Data for Name: notification_preferences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notification_preferences (id, user_id, notification_type, enabled, email_enabled, push_enabled, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notifications (id, user_id, type, title, message, entity_type, entity_id, read_at, created_at) FROM stdin;
\.


--
-- Data for Name: order_appearance_tags; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_appearance_tags (id, order_id, appearance_tag_id, created_at) FROM stdin;
\.


--
-- Data for Name: order_comments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_comments (id, order_id, author_type, author_id, author_name, comment_text, is_internal, created_at, user_id, mentions) FROM stdin;
\.


--
-- Data for Name: order_models; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_models (id, name, created_at) FROM stdin;
1	-	2026-03-03 17:47:45
2	133S	2026-03-03 17:47:45
3	A2681	2026-03-03 17:47:45
4	PS5	2026-03-03 17:47:45
5	M2540DN	2026-03-03 17:47:45
6	Serias X	2026-03-03 17:47:45
7	Ps4 PRO	2026-03-03 17:47:45
8	M2635	2026-03-03 17:47:45
9	Rog	2026-03-03 17:47:45
10	911MR Max	2026-03-03 17:47:45
11	LBP6030B	2026-03-03 17:47:45
12	12A	2026-03-03 17:47:45
13	MF4018	2026-03-03 17:47:45
14	M428fdn	2026-03-03 17:47:45
15	Macbook Air M1 A2337	2026-03-03 17:47:45
16	6500W/6500	2026-03-03 17:47:45
17	IdeaPad 5 Pro	2026-03-03 17:47:46
18	GU605M	2026-03-03 17:47:46
19	3070	2026-03-03 17:47:46
20	B12VFK	2026-03-03 17:47:46
21	P2506W	2026-03-03 17:47:46
22	1102w	2026-03-03 17:47:46
23	1800	2026-03-03 17:47:46
24	211	2026-03-03 17:47:46
25	PS4	2026-03-03 17:47:46
26	U400	2026-03-03 17:47:46
27	3025	2026-03-03 17:47:46
28	Белый	2026-03-03 17:47:46
29	Sous-vide SV-40, SV-30, Блендер Probar	2026-03-03 17:47:46
30	Бн	2026-03-03 17:47:46
31	0605	2026-03-03 17:47:46
32	Bravo	2026-03-03 17:47:46
33	32	2026-03-03 17:47:47
34	MDF-X	2026-03-03 17:47:47
35	V3080	2026-03-03 17:47:47
36	HP 117A	2026-03-03 17:47:47
37	Katana17	2026-03-03 17:47:47
38	Ideal Pad L340	2026-03-03 17:47:47
39	IdeaPad 3 15ITL6	2026-03-03 17:47:47
40	P1102	2026-03-03 17:47:47
41	M5521cdw	2026-03-03 17:47:47
42	IdeaPad3	2026-03-03 17:47:47
43	Цветной	2026-03-03 17:47:47
44	SCX-3407	2026-03-03 17:47:47
45	M125r	2026-03-03 17:47:47
46	Ps4	2026-03-03 17:47:47
47	QCWB335	2026-03-03 17:47:47
48	M132nw	2026-03-03 17:47:47
49	Scx-3205W	2026-03-03 17:47:47
50	MS-17F6	2026-03-03 17:47:48
51	Philips	2026-03-03 17:47:48
52	136a	2026-03-03 17:47:48
53	125ra	2026-03-03 17:47:48
54	B1025	2026-03-03 17:47:48
55	P300	2026-03-03 17:47:48
56	TK-6115	2026-03-03 17:47:48
57	107a	2026-03-03 17:47:48
58	M2535dn	2026-03-03 17:47:48
59	15B12M	2026-03-03 17:47:48
60	M6507W	2026-03-03 17:47:48
61	Delonghi	2026-03-03 17:47:48
62	M6550	2026-03-03 17:47:48
63	P3010DW	2026-03-03 17:47:48
64	Автомат	2026-03-03 17:47:48
65	SCX-4220	2026-03-03 17:47:48
66	M135wr	2026-03-03 17:47:48
67	428	2026-03-03 17:47:48
68	M6500	2026-03-03 17:47:49
69	G513	2026-03-03 17:47:49
70	L300	2026-03-03 17:47:49
71	6507	2026-03-03 17:47:49
72	2500	2026-03-03 17:47:49
73	P2035	2026-03-03 17:47:49
74	MF3010	2026-03-03 17:47:49
75	MF754	2026-03-03 17:47:49
76	2700	2026-03-03 17:47:49
77	Aspire 3 A315-53	2026-03-03 17:47:49
78	911S Core D	2026-03-03 17:47:49
79	AX211	2026-03-03 17:47:49
80	M2160	2026-03-03 17:47:49
81	43'	2026-03-03 17:47:49
82	150 suw	2026-03-03 17:47:49
83	NP930XED	2026-03-03 17:47:50
84	2165	2026-03-03 17:47:50
85	Katana	2026-03-03 17:47:50
86	M480	2026-03-03 17:47:50
87	Ps5	2026-03-03 17:47:50
88	X	2026-03-03 17:47:50
89	2070	2026-03-03 17:47:50
90	M111w	2026-03-03 17:47:50
91	5742G	2026-03-03 17:47:50
92	DCP-L5500	2026-03-03 17:47:50
93	Saeco phedra evo espresso	2026-03-03 17:47:50
94	1188 и 2500	2026-03-03 17:47:50
95	M5521	2026-03-03 17:47:50
96	L2500	2026-03-03 17:47:51
97	ThinkPad	2026-03-03 17:47:51
98	TPN-W130	2026-03-03 17:47:51
99	X550V	2026-03-03 17:47:51
100	M176n	2026-03-03 17:47:51
101	3200	2026-03-03 17:47:51
102	0	2026-03-03 17:47:51
103	911 MR Max	2026-03-03 17:47:51
104	Tuf	2026-03-03 17:47:51
105	Poemia	2026-03-03 17:47:51
106	5500	2026-03-03 17:47:51
107	M1214	2026-03-03 17:47:51
108	B218, DCP-7065, SCX-4100	2026-03-03 17:47:51
109	6500W	2026-03-03 17:47:52
110	Lenovo	2026-03-03 17:47:52
111	HL1202R	2026-03-03 17:47:52
112	X577	2026-03-03 17:47:52
113	3070TI	2026-03-03 17:47:52
114	1125	2026-03-03 17:47:52
115	M125r m132a	2026-03-03 17:47:52
116	Черный	2026-03-03 17:47:52
117	WFH-9	2026-03-03 17:47:52
118	X G2 IAH	2026-03-03 17:47:52
119	W2070A 117A	2026-03-03 17:47:52
120	847А	2026-03-03 17:47:52
121	F50	2026-03-03 17:47:52
122	2735	2026-03-03 17:47:52
123	Color 150a	2026-03-03 17:47:52
124	SCX-3400	2026-03-03 17:47:52
125	G50-70	2026-03-03 17:47:52
126	M6507	2026-03-03 17:47:52
127	Neo16	2026-03-03 17:47:53
128	Katana 17	2026-03-03 17:47:53
129	1018	2026-03-03 17:47:53
130	L2700DNR	2026-03-03 17:47:53
131	3010	2026-03-03 17:47:53
132	M2540	2026-03-03 17:47:53
133	C129	2026-03-03 17:47:53
134	M433i	2026-03-03 17:47:53
135	TUF Gaming	2026-03-03 17:47:53
136	M2835dw	2026-03-03 17:47:53
137	X1504V	2026-03-03 17:47:53
138	M1132 mfp	2026-03-03 17:47:53
139	NDB WAH9	2026-03-03 17:47:53
140	SCX-3200	2026-03-03 17:47:53
141	FS-1135	2026-03-03 17:47:53
142	Q262	2026-03-03 17:47:54
143	Action	2026-03-03 17:47:54
144	NP300E7Z	2026-03-03 17:47:54
145	Aspire 3	2026-03-03 17:47:54
146	POS100	2026-03-03 17:47:54
147	Yoga 2	2026-03-03 17:47:54
148	F17	2026-03-03 17:47:54
149	Tuf 17	2026-03-03 17:47:54
150	1995	2026-03-03 17:47:54
151	M132	2026-03-03 17:47:54
152	M426fdw	2026-03-03 17:47:54
153	MagnificaS	2026-03-03 17:47:54
154	15-n205sr	2026-03-03 17:47:54
155	3140 и 1522nf	2026-03-03 17:47:54
156	6700W и 6500W	2026-03-03 17:47:54
157	470G2	2026-03-03 17:47:54
158	MF4410	2026-03-03 17:47:54
159	C660	2026-03-03 17:47:55
160	N550J	2026-03-03 17:47:55
161	BMH-WFQ9NH	2026-03-03 17:47:55
162	M426	2026-03-03 17:47:55
163	TravelMate 5744series BIC50	2026-03-03 17:47:55
164	B590	2026-03-03 17:47:55
165	L2520DWR	2026-03-03 17:47:55
166	FX506I	2026-03-03 17:47:55
167	БН	2026-03-03 17:47:55
168	N21h	2026-03-03 17:47:55
169	П	2026-03-03 17:47:55
170	M402	2026-03-03 17:47:56
171	LJ 1600	2026-03-03 17:47:56
172	NP-R540H	2026-03-03 17:47:56
173	A2337	2026-03-03 17:47:56
174	CF234A	2026-03-03 17:47:56
175	X571G	2026-03-03 17:47:56
176	PS3	2026-03-03 17:47:56
177	2835	2026-03-03 17:47:56
178	E1	2026-03-03 17:47:56
179	132Mf	2026-03-03 17:47:56
180	1132	2026-03-03 17:47:56
181	M7100DW	2026-03-03 17:47:56
182	MFC-L2700DNR	2026-03-03 17:47:56
183	FS1025	2026-03-03 17:47:57
184	M2070	2026-03-03 17:47:57
185	15IMH6	2026-03-03 17:47:57
186	6500	2026-03-03 17:47:57
187	Phaser 3100	2026-03-03 17:47:57
188	MacBook Pro	2026-03-03 17:47:57
189	M6500W	2026-03-03 17:47:57
190	FC128	2026-03-03 17:47:57
191	DORS 800	2026-03-03 17:47:57
192	M2735dn	2026-03-03 17:47:57
193	M5521cdn	2026-03-03 17:47:57
194	PC-211	2026-03-03 17:47:57
195	Ideal Pad S340-15API	2026-03-03 17:47:57
196	R459F	2026-03-03 17:47:57
197	DCP-L2500DR	2026-03-03 17:47:57
198	OK-Pioner	2026-03-03 17:47:57
199	B215	2026-03-03 17:47:57
200	M2040dn	2026-03-03 17:47:57
201	N16C2	2026-03-03 17:47:58
202	P5026cdn	2026-03-03 17:47:58
203	RTL0723DE	2026-03-03 17:47:58
204	M2135dn	2026-03-03 17:47:58
205	Latitude E7470	2026-03-03 17:47:58
206	MS-V341	2026-03-03 17:47:58
207	MS-17C1	2026-03-03 17:47:58
208	Thinkpad	2026-03-03 17:47:58
209	Капсульная	2026-03-03 17:47:58
210	1536	2026-03-03 17:47:58
211	IdealPad 330-17IKB	2026-03-03 17:47:58
212	Magnifica S	2026-03-03 17:47:58
213	E410MA	2026-03-03 17:47:58
214	RT3290	2026-03-03 17:47:59
215	E732 Series	2026-03-03 17:47:59
216	CHARGE 3	2026-03-03 17:47:59
217	Q5WPH	2026-03-03 17:47:59
218	3260	2026-03-03 17:47:59
219	GP75 Leopard	2026-03-03 17:47:59
220	Vivo	2026-03-03 17:47:59
221	Cafe Venezia	2026-03-03 17:47:59
222	1510R	2026-03-03 17:47:59
223	M1132	2026-03-03 17:48:00
224	MacBook Air	2026-03-03 17:48:00
225	Лягушка	2026-03-03 17:48:00
226	M15	2026-03-03 17:48:00
227	Satellite C850-E3K	2026-03-03 17:48:00
228	PCG-71812V	2026-03-03 17:48:00
229	MFC-L2700DW	2026-03-03 17:48:00
230	M6035cidn	2026-03-03 17:48:00
231	Корпус Corsair	2026-03-03 17:48:00
232	M16	2026-03-03 17:48:01
233	1536dnf	2026-03-03 17:48:01
234	HP и Xpriner	2026-03-03 17:48:01
235	M6500Q	2026-03-03 17:48:01
236	PS4Pro	2026-03-03 17:48:01
237	M125ra	2026-03-03 17:48:01
238	N20C1	2026-03-03 17:48:01
239	M1603Q	2026-03-03 17:48:01
240	Pro	2026-03-03 17:48:01
241	P3150	2026-03-03 17:48:01
242	15s-eq1118ng	2026-03-03 17:48:01
243	MS2384	2026-03-03 17:48:01
244	PCG-41219V	2026-03-03 17:48:01
245	X541N	2026-03-03 17:48:01
246	L2500DR	2026-03-03 17:48:01
247	M2070W	2026-03-03 17:48:01
248	M176N	2026-03-03 17:48:01
249	8265NGW	2026-03-03 17:48:02
250	Fat	2026-03-03 17:48:02
251	VeroCup 100	2026-03-03 17:48:02
252	FX707Z	2026-03-03 17:48:02
253	Bom-WDQ9	2026-03-03 17:48:02
254	M177fw	2026-03-03 17:48:02
255	YM-628	2026-03-03 17:48:02
256	4KL9Q72	2026-03-03 17:48:02
257	MP2014AD	2026-03-03 17:48:02
258	15s-eq1275ur	2026-03-03 17:48:02
259	Aspire E5 575	2026-03-03 17:48:03
260	IdealPad 5	2026-03-03 17:48:03
261	M1132MFP	2026-03-03 17:48:03
262	ATK3060	2026-03-03 17:48:03
263	GP-W2070A	2026-03-03 17:48:03
264	16 G8	2026-03-03 17:48:03
265	1214nfh	2026-03-03 17:48:03
266	6700	2026-03-03 17:48:03
267	HYLR-WFQ9	2026-03-03 17:48:03
268	K50IJ	2026-03-03 17:48:03
269	IdeaPad5	2026-03-03 17:48:03
270	CLP-315	2026-03-03 17:48:03
271	Modern 14 CM12M230RU	2026-03-03 17:48:03
272	WAP9HNRP	2026-03-03 17:48:04
273	Серебристый	2026-03-03 17:48:04
274	MagicBook 10	2026-03-03 17:48:04
275	NP350V5C	2026-03-03 17:48:04
276	V3571G и ТЗ-К528	2026-03-03 17:48:04
277	K53tk	2026-03-03 17:48:04
278	HNZW9G2	2026-03-03 17:48:04
279	C660-28k	2026-03-03 17:48:04
280	2021ap	2026-03-03 17:48:04
281	2000	2026-03-03 17:48:05
282	DCP-7057R	2026-03-03 17:48:05
283	K53S	2026-03-03 17:48:05
284	1602	2026-03-03 17:48:05
285	7057	2026-03-03 17:48:05
286	ENVY 17-cg1002ur	2026-03-03 17:48:05
287	17-ck2095Ci	2026-03-03 17:48:05
288	M130fw	2026-03-03 17:48:05
289	P2040DN	2026-03-03 17:48:05
290	Автромат	2026-03-03 17:48:05
291	107	2026-03-03 17:48:05
292	M1217	2026-03-03 17:48:05
293	X1505ZA	2026-03-03 17:48:05
294	911SE-E5TaR	2026-03-03 17:48:05
295	Tank 1005	2026-03-03 17:48:05
296	IdealPad Gaming 3	2026-03-03 17:48:05
297	3165NGW	2026-03-03 17:48:05
298	UX301	2026-03-03 17:48:05
299	2040	2026-03-03 17:48:05
300	4410	2026-03-03 17:48:05
301	1020	2026-03-03 17:48:05
302	8070	2026-03-03 17:48:06
303	Satellite C50	2026-03-03 17:48:06
304	N19c2	2026-03-03 17:48:06
305	Legion 5	2026-03-03 17:48:06
306	6550	2026-03-03 17:48:06
307	EB-X72	2026-03-03 17:48:06
308	MagnificaS серебристая	2026-03-03 17:48:06
309	Mfp135w	2026-03-03 17:48:06
310	Magnifica	2026-03-03 17:48:06
311	Aspire 5	2026-03-03 17:48:06
312	911 Plus Gr Pro7	2026-03-03 17:48:06
313	3	2026-03-03 17:48:06
314	RTL 8723DE	2026-03-03 17:48:07
315	3010MF	2026-03-03 17:48:07
316	BoDE-WDH9	2026-03-03 17:48:07
317	CLX-2160	2026-03-03 17:48:07
318	GK mini	2026-03-03 17:48:07
319	M3145idn	2026-03-03 17:48:07
320	FS-1320	2026-03-03 17:48:07
321	VivoBook	2026-03-03 17:48:07
322	B3402FE	2026-03-03 17:48:07
323	Playstation 3	2026-03-03 17:48:07
324	1520P	2026-03-03 17:48:07
325	5735 Series	2026-03-03 17:48:07
326	Автоматическая	2026-03-03 17:48:07
327	MF3228	2026-03-03 17:48:07
328	V5-571G	2026-03-03 17:48:07
329	Ideal Pad 330-15 ARR	2026-03-03 17:48:07
330	I5-cx002Tur	2026-03-03 17:48:07
331	M65002	2026-03-03 17:48:07
332	NP530U4B	2026-03-03 17:48:07
333	FS-1125	2026-03-03 17:48:08
334	M1522n	2026-03-03 17:48:08
335	СTES32X	2026-03-03 17:48:08
336	Idealpad 310	2026-03-03 17:48:08
337	X75A	2026-03-03 17:48:08
338	NINJA	2026-03-03 17:48:08
339	L2300DR	2026-03-03 17:48:08
340	QSV1107	2026-03-03 17:48:08
341	15-j012sr	2026-03-03 17:48:08
342	L340	2026-03-03 17:48:08
343	P3145dn	2026-03-03 17:48:08
344	CM1100ADWW	2026-03-03 17:48:08
345	7060DR	2026-03-03 17:48:08
346	S550cb	2026-03-03 17:48:08
347	5521cdn	2026-03-03 17:48:08
348	RTX3060	2026-03-03 17:48:08
349	4300	2026-03-03 17:48:09
350	6550NW	2026-03-03 17:48:09
351	Helios 30 serios	2026-03-03 17:48:09
352	GV-R68X1GAMING	2026-03-03 17:48:09
353	Intuita	2026-03-03 17:48:09
354	M180n	2026-03-03 17:48:09
355	MS-175A	2026-03-03 17:48:09
356	CLX-3305FW	2026-03-03 17:48:09
357	BRN-F58	2026-03-03 17:48:09
358	N580V	2026-03-03 17:48:09
359	JF Diode 810	2026-03-03 17:48:09
360	3207	2026-03-03 17:48:09
361	Acer	2026-03-03 17:48:10
362	M2635dn	2026-03-03 17:48:10
363	5521	2026-03-03 17:48:10
364	2207	2026-03-03 17:48:10
365	4018	2026-03-03 17:48:10
366	NL-9206NL	2026-03-03 17:48:10
367	Viao	2026-03-03 17:48:10
368	-M125	2026-03-03 17:48:10
369	7065	2026-03-03 17:48:11
370	Zenbook UX3402V	2026-03-03 17:48:11
371	7065DNR	2026-03-03 17:48:11
372	NP305V5A	2026-03-03 17:48:11
373	Карманная	2026-03-03 17:48:11
374	Ручная	2026-03-03 17:48:11
375	HP 134a	2026-03-03 17:48:11
376	A315	2026-03-03 17:48:11
377	428fdn	2026-03-03 17:48:12
378	2900	2026-03-03 17:48:12
379	EQ 6 plus	2026-03-03 17:48:12
380	ProtectSmart	2026-03-03 17:48:12
381	--	2026-03-03 17:48:12
382	8520dn	2026-03-03 17:48:12
383	125r	2026-03-03 17:48:12
384	M50	2026-03-03 17:48:12
385	EX215	2026-03-03 17:48:12
386	1010	2026-03-03 17:48:13
387	4830 Series	2026-03-03 17:48:13
388	SM6100E	2026-03-03 17:48:13
389	15S-Eqir56ur	2026-03-03 17:48:13
390	ELLIX40E, ELLIX30	2026-03-03 17:48:13
391	Pavilion	2026-03-03 17:48:13
392	M8124cidn	2026-03-03 17:48:13
393	Legion5 Pro	2026-03-03 17:48:13
394	15 G2	2026-03-03 17:48:13
395	6507W	2026-03-03 17:48:14
396	K56CM	2026-03-03 17:48:14
397	S145-15ST	2026-03-03 17:48:14
398	M1217nfw	2026-03-03 17:48:14
399	N20C5	2026-03-03 17:48:14
400	X669	2026-03-03 17:48:14
401	106	2026-03-03 17:48:14
402	Автом	2026-03-03 17:48:14
403	P2500W	2026-03-03 17:48:14
404	15-ba052ur	2026-03-03 17:48:14
405	Клише	2026-03-03 17:48:15
406	3055	2026-03-03 17:48:15
407	K16	2026-03-03 17:48:15
408	Автомат и лягушка	2026-03-03 17:48:15
409	59A	2026-03-03 17:48:15
410	SAM4S	2026-03-03 17:48:15
411	RLEF-X	2026-03-03 17:48:15
412	1120	2026-03-03 17:48:15
413	RTX3060TI	2026-03-03 17:48:15
414	HFBOOK2	2026-03-03 17:48:15
415	L850	2026-03-03 17:48:15
416	EP-27	2026-03-03 17:48:16
417	Ideapad	2026-03-03 17:48:16
418	M2040	2026-03-03 17:48:16
419	2540	2026-03-03 17:48:16
420	7265NGW	2026-03-03 17:48:16
421	Лягушки	2026-03-03 17:48:16
422	SCX-4824FN	2026-03-03 17:48:16
423	Vaio	2026-03-03 17:48:16
424	E402W	2026-03-03 17:48:16
425	285A	2026-03-03 17:48:16
426	-Автомат	2026-03-03 17:48:16
427	M1120 MFP	2026-03-03 17:48:16
428	9206AD	2026-03-03 17:48:16
429	J 5945	2026-03-03 17:48:16
430	Ручные	2026-03-03 17:48:16
431	MF645Cx	2026-03-03 17:48:16
432	P89F	2026-03-03 17:48:17
433	ML	2026-03-03 17:48:17
434	Pro 400 MFP M425dn	2026-03-03 17:48:17
435	VA73	2026-03-03 17:48:17
436	HP728A - 6 шт, TK-1170/1200 - 6 шт, TN-2375 - 12 шт, TN-14 - 1 шт, HP505X - 2 шт, DK-1150 -3 шт, DR-2335 - 1 шт	2026-03-03 17:48:17
437	Trodat	2026-03-03 17:48:17
438	FX705D	2026-03-03 17:48:17
439	15-dk0064ur	2026-03-03 17:48:17
440	PS4 Slim	2026-03-03 17:48:17
441	ProBook 470 G4	2026-03-03 17:48:17
442	P2040dn	2026-03-03 17:48:17
443	CF31	2026-03-03 17:48:17
444	M2035dn	2026-03-03 17:48:17
445	JGemiBCW1H220301233	2026-03-03 17:48:17
446	YOGA 530-14IKB 81EK	2026-03-03 17:48:17
447	STP-S260	2026-03-03 17:48:17
448	Lirika	2026-03-03 17:48:17
449	IdeaPad L340-17IRH	2026-03-03 17:48:18
450	Dualsense 5	2026-03-03 17:48:18
451	M1132 MFP	2026-03-03 17:48:18
452	285A - 2шт. 259A - 2шт. TK1150/1200 - 7шт	2026-03-03 17:48:18
453	M283fdn	2026-03-03 17:48:18
454	M1120MFP	2026-03-03 17:48:18
455	5	2026-03-03 17:48:18
456	1602R	2026-03-03 17:48:18
457	Kyocera	2026-03-03 17:48:18
458	EC850.M	2026-03-03 17:48:18
459	FS-1040	2026-03-03 17:48:18
460	15s-eq1322ur	2026-03-03 17:48:18
461	Врач	2026-03-03 17:48:18
462	FX753V	2026-03-03 17:48:19
463	UM433D	2026-03-03 17:48:19
464	ML1665	2026-03-03 17:48:19
465	E5-573	2026-03-03 17:48:19
466	E732G	2026-03-03 17:48:19
467	DCP-1510R, M1132mfp	2026-03-03 17:48:19
468	A315-21	2026-03-03 17:48:19
469	N19H1	2026-03-03 17:48:19
470	HP	2026-03-03 17:48:19
471	M28a	2026-03-03 17:48:19
472	A515-44	2026-03-03 17:48:19
473	CP1525n	2026-03-03 17:48:19
474	X553M	2026-03-03 17:48:19
475	42	2026-03-03 17:48:20
476	CQ58-251SR	2026-03-03 17:48:20
477	X53U	2026-03-03 17:48:20
478	14-ec0002ur	2026-03-03 17:48:20
479	SCX-3205	2026-03-03 17:48:20
480	CP1025	2026-03-03 17:48:20
481	NP350E	2026-03-03 17:48:20
482	M2540dn	2026-03-03 17:48:20
483	TS1TSJ25H3P	2026-03-03 17:48:20
484	500Gb	2026-03-03 17:48:20
485	17-j017sr	2026-03-03 17:48:20
486	MFC-L2751DW	2026-03-03 17:48:20
487	MS-1795	2026-03-03 17:48:20
488	M3145dn	2026-03-03 17:48:20
489	DCP	2026-03-03 17:48:20
490	M127fw	2026-03-03 17:48:20
491	RTX2060 SUPER	2026-03-03 17:48:20
492	MS-17F4	2026-03-03 17:48:20
493	N17Q3	2026-03-03 17:48:20
494	30мм	2026-03-03 17:48:20
495	LBP6020B	2026-03-03 17:48:20
496	2040DN	2026-03-03 17:48:20
497	X552C	2026-03-03 17:48:21
498	58*22	2026-03-03 17:48:21
499	135W	2026-03-03 17:48:21
500	X52A	2026-03-03 17:48:21
501	FX506L	2026-03-03 17:48:21
502	116C	2026-03-03 17:48:21
503	44A	2026-03-03 17:48:21
504	CF244A	2026-03-03 17:48:21
505	435-436-285	2026-03-03 17:48:21
506	136A	2026-03-03 17:48:21
507	W1106	2026-03-03 17:48:21
508	285	2026-03-03 17:48:21
509	2275	2026-03-03 17:48:21
510	M283fdw	2026-03-03 17:48:21
511	NP300E5A	2026-03-03 17:48:21
512	K540B	2026-03-03 17:48:21
513	OURUS 17	2026-03-03 17:48:21
514	N23C3	2026-03-03 17:48:21
515	44А	2026-03-03 17:48:21
516	С7115Х	2026-03-03 17:48:21
517	R543B	2026-03-03 17:48:21
518	Laser  179 fnw	2026-03-03 17:48:21
519	GL731G	2026-03-03 17:48:22
520	НОН	2026-03-03 17:48:22
521	LBR623	2026-03-03 17:48:22
522	80WK	2026-03-03 17:48:22
523	CF244a-x	2026-03-03 17:48:22
524	Modern 15 B12M	2026-03-03 17:48:22
525	2335	2026-03-03 17:48:22
526	W106A	2026-03-03 17:48:22
527	2375	2026-03-03 17:48:22
528	Ideapad 3	2026-03-03 17:48:22
529	17-1160nr	2026-03-03 17:48:22
530	Nitro 5	2026-03-03 17:48:22
531	HP Laser Jet P2035	2026-03-03 17:48:23
532	ICONA_Tab_W500-C62G03iss	2026-03-03 17:48:23
533	W1106A без чипа	2026-03-03 17:48:23
534	278	2026-03-03 17:48:23
535	Pc-211	2026-03-03 17:48:23
536	CF218A	2026-03-03 17:48:23
537	JF65	2026-03-03 17:48:23
538	M600W	2026-03-03 17:48:23
539	N17C1	2026-03-03 17:48:23
540	ML-2160	2026-03-03 17:48:23
541	Aspire	2026-03-03 17:48:23
542	Color Laser MFP 178nw	2026-03-03 17:48:23
543	15s-eq2058ur	2026-03-03 17:48:23
544	G5 KD	2026-03-03 17:48:23
545	410	2026-03-03 17:48:23
546	D540M	2026-03-03 17:48:23
547	X540S	2026-03-03 17:48:24
548	Vostro 15	2026-03-03 17:48:24
549	S330U	2026-03-03 17:48:24
550	MFP 135w	2026-03-03 17:48:24
551	A53S	2026-03-03 17:48:24
552	XPS	2026-03-03 17:48:24
553	F0CD	2026-03-03 17:48:24
554	MFP 135a	2026-03-03 17:48:24
555	15 Pro	2026-03-03 17:48:24
556	12А	2026-03-03 17:48:24
557	ТК1110	2026-03-03 17:48:24
558	MFP M28a	2026-03-03 17:48:24
559	Dv6-6153er	2026-03-03 17:48:24
560	=	2026-03-03 17:48:24
561	Струйный	2026-03-03 17:48:24
562	80TV	2026-03-03 17:48:24
563	350E	2026-03-03 17:48:24
564	2235	2026-03-03 17:48:24
565	17an6r	2026-03-03 17:48:24
566	Для часов	2026-03-03 17:48:24
567	P2207	2026-03-03 17:48:24
568	SeOLa 180201	2026-03-03 17:48:24
569	SeOLA-1802-00	2026-03-03 17:48:24
570	P3010D	2026-03-03 17:48:24
571	Ecosys p2040dn	2026-03-03 17:48:24
572	Матричный принтер	2026-03-03 17:48:24
573	NBR-WAI9	2026-03-03 17:48:25
574	PRO58S	2026-03-03 17:48:25
575	RV-UR378	2026-03-03 17:48:25
576	PartyBox 300	2026-03-03 17:48:25
577	8 Plus	2026-03-03 17:48:25
578	J120F	2026-03-03 17:48:25
579	Лак	2026-03-03 17:48:25
580	LaserJet Pro 200 color MFP m276n	2026-03-03 17:48:25
581	MCLF-X	2026-03-03 17:48:25
582	217160-03	2026-03-03 17:48:25
583	6.445-043.0	2026-03-03 17:48:25
584	OK65	2026-03-03 17:48:25
585	S6445	2026-03-03 17:48:25
586	B50-45	2026-03-03 17:48:25
587	MAR-LX1M	2026-03-03 17:48:25
588	Zax	2026-03-03 17:48:25
589	755-808-1064nm	2026-03-03 17:48:25
590	GF76	2026-03-03 17:48:25
591	Dyson	2026-03-03 17:48:25
592	22500	2026-03-03 17:48:25
593	283	2026-03-03 17:48:25
594	Hot 12i	2026-03-03 17:48:25
595	13,5	2026-03-03 17:48:25
596	GS66 Stealth	2026-03-03 17:48:25
597	3160	2026-03-03 17:48:25
598	23021RAA2Y	2026-03-03 17:48:26
599	P65F	2026-03-03 17:48:26
600	18V500mA	2026-03-03 17:48:26
601	YNDX-00020	2026-03-03 17:48:26
602	Incanto Deluxe W HD	2026-03-03 17:48:26
603	УХЛ4.2	2026-03-03 17:48:26
604	ELLIX40E	2026-03-03 17:48:26
605	1200	2026-03-03 17:48:26
606	7000	2026-03-03 17:48:26
607	CMA009	2026-03-03 17:48:26
608	13.5	2026-03-03 17:48:26
609	9C	2026-03-03 17:48:26
610	40	2026-03-03 17:48:26
611	Z3100	2026-03-03 17:48:26
612	HP250G6	2026-03-03 17:48:26
613	BL50	2026-03-03 17:48:26
614	A570IS	2026-03-03 17:48:26
615	АСН-2000/1-Ц	2026-03-03 17:48:27
616	12 mini	2026-03-03 17:48:27
617	M2102J20SG	2026-03-03 17:48:27
618	DT-3367	2026-03-03 17:48:27
619	R543U	2026-03-03 17:48:27
620	G771J	2026-03-03 17:48:27
621	IdeaPad 3 15 ITLS	2026-03-03 17:48:27
622	17-ak049ur	2026-03-03 17:48:27
623	CE847A	2026-03-03 17:48:27
624	LE32R81B	2026-03-03 17:48:27
625	Paradise	2026-03-03 17:48:27
626	Elleta	2026-03-03 17:48:27
627	M6550NQ	2026-03-03 17:48:27
628	PSP-3008	2026-03-03 17:48:27
629	CALLISTO-102D	2026-03-03 17:48:27
630	ELLIX30IIID	2026-03-03 17:48:27
631	M5526cdn/A	2026-03-03 17:48:27
632	Instax	2026-03-03 17:48:27
633	1075	2026-03-03 17:48:27
634	1170	2026-03-03 17:48:27
635	1708	2026-03-03 17:48:27
636	MFP135	2026-03-03 17:48:27
637	LE32B8000	2026-03-03 17:48:27
638	13-ba0023ur	2026-03-03 17:48:28
639	G513R	2026-03-03 17:48:28
640	Smart 6	2026-03-03 17:48:28
641	Mavic 3 pro mini	2026-03-03 17:48:28
642	CF455A	2026-03-03 17:48:28
643	Extensive 12 кВА	2026-03-03 17:48:28
644	F176200	2026-03-03 17:48:28
645	Big-s	2026-03-03 17:48:28
646	VTE1-GR3	2026-03-03 17:48:28
647	Hyper	2026-03-03 17:48:28
648	1914	2026-03-03 17:48:28
649	M1120	2026-03-03 17:48:28
650	SFC-converter	2026-03-03 17:48:28
651	42mm	2026-03-03 17:48:28
652	NEVONA\tCofe Romantica	2026-03-03 17:48:28
653	ST-222	2026-03-03 17:48:28
654	ST-888	2026-03-03 17:48:28
655	TK-475	2026-03-03 17:48:28
656	530	2026-03-03 17:48:28
657	M141 a	2026-03-03 17:48:28
658	14IML05	2026-03-03 17:48:29
659	SCX3205	2026-03-03 17:48:29
660	SV10	2026-03-03 17:48:29
661	UE32F5020AK	2026-03-03 17:48:29
662	CECH-4208C	2026-03-03 17:48:29
663	P2PRO	2026-03-03 17:48:29
664	LS	2026-03-03 17:48:29
665	4+64G CC2	2026-03-03 17:48:29
666	A1238	2026-03-03 17:48:29
667	P35E	2026-03-03 17:48:29
668	42LS570T-ZB	2026-03-03 17:48:29
669	Ручной	2026-03-03 17:48:29
670	32LF580U	2026-03-03 17:48:29
671	MFP M125R	2026-03-03 17:48:29
672	20 pro	2026-03-03 17:48:29
673	Dualsense	2026-03-03 17:48:29
674	TK-1170	2026-03-03 17:48:29
675	TPN-DA09	2026-03-03 17:48:29
676	Карманные	2026-03-03 17:48:29
677	3168ngw	2026-03-03 17:48:29
678	15-bs161ur	2026-03-03 17:48:29
679	42AV653DR	2026-03-03 17:48:29
680	UE40EH	2026-03-03 17:48:29
681	G6-1250er	2026-03-03 17:48:29
682	CUH-70088	2026-03-03 17:48:29
683	3138	2026-03-03 17:48:29
684	K50I	2026-03-03 17:48:30
685	PH532	2026-03-03 17:48:30
686	X541U	2026-03-03 17:48:30
687	Benvenuto Classic	2026-03-03 17:48:30
688	A33	2026-03-03 17:48:30
689	ECOSYS M2040dn	2026-03-03 17:48:30
690	1797	2026-03-03 17:48:30
691	7739ZG	2026-03-03 17:48:30
692	AIC70	2026-03-03 17:48:30
693	P2055d	2026-03-03 17:48:30
694	VHIT-40F152MS	2026-03-03 17:48:30
695	SPT-S100	2026-03-03 17:48:30
696	Europa	2026-03-03 17:48:30
697	50mm	2026-03-03 17:48:30
698	V98472	2026-03-03 17:48:30
699	Tmz550	2026-03-03 17:48:30
700	UE65NU7090UXRU	2026-03-03 17:48:30
701	ESC402	2026-03-03 17:48:30
702	32LEM1029	2026-03-03 17:48:30
703	32LEM-1033	2026-03-03 17:48:31
704	ELLIX30IID	2026-03-03 17:48:31
705	FOS-R6	2026-03-03 17:48:31
706	STRIX-RX480-8G-GAMING	2026-03-03 17:48:31
707	F7 Plus	2026-03-03 17:48:31
708	81LW	2026-03-03 17:48:31
709	P2516	2026-03-03 17:48:31
710	VE276	2026-03-03 17:48:31
711	85A	2026-03-03 17:48:31
712	HW60-10636A	2026-03-03 17:48:31
713	KDC-455UW	2026-03-03 17:48:31
714	LE22S81B	2026-03-03 17:48:31
715	ST-555	2026-03-03 17:48:31
716	CE101KR	2026-03-03 17:48:31
717	S145-15IKB	2026-03-03 17:48:31
718	43UJ750V	2026-03-03 17:48:31
719	WD-683	2026-03-03 17:48:31
720	PC	2026-03-03 17:48:31
721	RP-326-USE	2026-03-03 17:48:31
722	DG-1122	2026-03-03 17:48:31
723	Goplay	2026-03-03 17:48:31
724	A30	2026-03-03 17:48:31
725	Ыфв	2026-03-03 17:48:31
726	SPT-S260	2026-03-03 17:48:31
727	Onviz	2026-03-03 17:48:31
728	TK-7310-2шт.	2026-03-03 17:48:31
729	18V 200mA	2026-03-03 17:48:31
730	5010-3133	2026-03-03 17:48:31
731	X15W	2026-03-03 17:48:31
732	CX29	2026-03-03 17:48:31
733	A62	2026-03-03 17:48:31
734	M2001J2G	2026-03-03 17:48:31
735	TH-562	2026-03-03 17:48:31
736	EN-500	2026-03-03 17:48:31
737	M2103K10PG	2026-03-03 17:48:31
738	L-2300DR	2026-03-03 17:48:32
739	15-dk1278ng	2026-03-03 17:48:32
740	27А	2026-03-03 17:48:32
741	R541U	2026-03-03 17:48:32
742	KDL-42W807A	2026-03-03 17:48:32
743	NEO	2026-03-03 17:48:32
744	42LB653V	2026-03-03 17:48:32
745	KMS-221	2026-03-03 17:48:32
746	IPhone 14	2026-03-03 17:48:32
747	Dinamica	2026-03-03 17:48:32
748	HT-480	2026-03-03 17:48:32
749	15s-fq2151ur	2026-03-03 17:48:32
750	M21	2026-03-03 17:48:32
751	S21FE 5G	2026-03-03 17:48:32
752	M28w	2026-03-03 17:48:32
753	M16DFL	2026-03-03 17:48:32
754	32LEM	2026-03-03 17:48:32
755	NELA0	2026-03-03 17:48:32
756	ProBook 445 GB	2026-03-03 17:48:32
757	2186462	2026-03-03 17:48:32
758	Aspire 7	2026-03-03 17:48:32
759	PC42t Plus	2026-03-03 17:48:32
760	42LS3400	2026-03-03 17:48:32
761	B211	2026-03-03 17:48:32
762	P1120	2026-03-03 17:48:32
763	256Gb	2026-03-03 17:48:32
764	3145	2026-03-03 17:48:32
765	7500A	2026-03-03 17:48:32
766	MR-901	2026-03-03 17:48:32
767	GTK-XB60	2026-03-03 17:48:32
768	V15G2	2026-03-03 17:48:32
769	N15C4	2026-03-03 17:48:32
770	D104	2026-03-03 17:48:32
771	160	2026-03-03 17:48:32
772	AGC-1220RF-A	2026-03-03 17:48:32
773	32LEM-1050/TS2C	2026-03-03 17:48:32
774	15s-eq1356ur	2026-03-03 17:48:32
775	13500	2026-03-03 17:48:32
776	80XF	2026-03-03 17:48:32
777	P4140	2026-03-03 17:48:32
778	TSR-240.4	2026-03-03 17:48:32
779	315	2026-03-03 17:48:32
780	P6230CDN	2026-03-03 17:48:32
781	Mini	2026-03-03 17:48:32
782	G14	2026-03-03 17:48:32
783	F40C7100C	2026-03-03 17:48:32
784	E3/5	2026-03-03 17:48:32
785	D541N	2026-03-03 17:48:33
786	MJSTG1	2026-03-03 17:48:33
787	355V	2026-03-03 17:48:33
788	U40B9000H	2026-03-03 17:48:33
789	PCG-41414V	2026-03-03 17:48:33
790	FE-40	2026-03-03 17:48:33
791	CFI-ZCT1J	2026-03-03 17:48:33
792	OK85	2026-03-03 17:48:33
793	15-dc1004ur	2026-03-03 17:48:33
794	FLTV-22T9	2026-03-03 17:48:33
795	BAH3-W59	2026-03-03 17:48:33
796	UE49N5510AU	2026-03-03 17:48:33
797	Envy	2026-03-03 17:48:33
798	Bravia KDL-55W807A	2026-03-03 17:48:33
799	М1132	2026-03-03 17:48:33
800	PA2612U	2026-03-03 17:48:33
801	BTS31	2026-03-03 17:48:33
802	Neo G15-15ND302	2026-03-03 17:48:33
803	ST500LM012	2026-03-03 17:48:33
804	N55S	2026-03-03 17:48:33
805	M2540dn? sc000778	2026-03-03 17:48:33
806	R-FLEX	2026-03-03 17:48:33
807	3040	2026-03-03 17:48:33
808	3150	2026-03-03 17:48:33
809	B&E	2026-03-03 17:48:33
810	MFP 400	2026-03-03 17:48:33
811	GA401I	2026-03-03 17:48:33
812	1528	2026-03-03 17:48:33
813	MS2233	2026-03-03 17:48:33
814	A114-32	2026-03-03 17:48:33
815	N18C3	2026-03-03 17:48:33
816	75A	2026-03-03 17:48:33
817	4090	2026-03-03 17:48:33
818	Xbox	2026-03-03 17:48:33
819	F158200	2026-03-03 17:48:33
820	EC POT S	2026-03-03 17:48:33
821	40F152	2026-03-03 17:48:33
822	PS4 Fat	2026-03-03 17:48:33
823	15	2026-03-03 17:48:33
824	S550CB	2026-03-03 17:48:33
825	KDL-40W	2026-03-03 17:48:33
826	PS4 Pro	2026-03-03 17:48:33
827	PCG-61211V	2026-03-03 17:48:33
828	FS-1060	2026-03-03 17:48:33
829	43LT590	2026-03-03 17:48:33
830	N19C1	2026-03-03 17:48:33
831	ZV-E10	2026-03-03 17:48:33
832	1035	2026-03-03 17:48:33
833	51b040	2026-03-03 17:48:33
834	18 Quart	2026-03-03 17:48:33
835	FX506H	2026-03-03 17:48:33
836	Redmi Note 10S	2026-03-03 17:48:33
837	Cofe Romantica	2026-03-03 17:48:33
838	Master Edition GT	2026-03-03 17:48:33
839	A705FN	2026-03-03 17:48:33
840	4200	2026-03-03 17:48:33
841	NP-RV511	2026-03-03 17:48:33
842	KX-MB1500	2026-03-03 17:48:33
843	F48B7000V	2026-03-03 17:48:33
844	АСН-8000	2026-03-03 17:48:33
845	14-bs000ur	2026-03-03 17:48:33
846	FS-1120	2026-03-03 17:48:34
847	M132fn	2026-03-03 17:48:34
848	Mop Essential	2026-03-03 17:48:34
849	S550C	2026-03-03 17:48:34
850	X551C	2026-03-03 17:48:34
851	Asus	2026-03-03 17:48:34
852	DCP-L2540DNR	2026-03-03 17:48:34
853	MTV-2229LT2	2026-03-03 17:48:34
854	2375/2335	2026-03-03 17:48:34
855	42PFL5604/60	2026-03-03 17:48:34
856	JZ2204	2026-03-03 17:48:34
857	BoD-WDI9	2026-03-03 17:48:34
858	LatteGo	2026-03-03 17:48:34
859	Sm-g780g/dsm	2026-03-03 17:48:34
860	U940-D4M	2026-03-03 17:48:34
861	1102	2026-03-03 17:48:34
862	15-cw0040ur	2026-03-03 17:48:34
863	N19C5	2026-03-03 17:48:34
864	LE32B530	2026-03-03 17:48:34
865	0726	2026-03-03 17:48:34
866	Killer Pro	2026-03-03 17:48:34
867	G550J	2026-03-03 17:48:34
868	MB1900	2026-03-03 17:48:34
869	A70	2026-03-03 17:48:34
870	XMA2101-BN	2026-03-03 17:48:34
871	150 Digital	2026-03-03 17:48:34
872	2500W	2026-03-03 17:48:34
873	M175	2026-03-03 17:48:34
874	IdeaPad 330s-14IKB	2026-03-03 17:48:34
875	D250-0Br	2026-03-03 17:48:34
876	15-n058sr	2026-03-03 17:48:34
877	N56V	2026-03-03 17:48:34
878	2 шт.	2026-03-03 17:48:34
879	GTX1660S	2026-03-03 17:48:34
880	CINEOS	2026-03-03 17:48:34
881	XS MAX	2026-03-03 17:48:34
882	15-cw1019ur	2026-03-03 17:48:34
883	K540L	2026-03-03 17:48:34
884	MediaPad T3	2026-03-03 17:48:35
885	1660	2026-03-03 17:48:35
886	Drone	2026-03-03 17:48:35
887	15ARH05	2026-03-03 17:48:35
888	Hot 12 Play	2026-03-03 17:48:35
889	725	2026-03-03 17:48:35
890	15-ac679ur	2026-03-03 17:48:35
891	44	2026-03-03 17:48:35
892	VG70	2026-03-03 17:48:35
893	A1586	2026-03-03 17:48:35
894	47pft6569/60	2026-03-03 17:48:35
895	1510	2026-03-03 17:48:35
896	Pro 200	2026-03-03 17:48:35
897	IdeaPad Gaming 3 15ACH6	2026-03-03 17:48:35
898	DEEBOT	2026-03-03 17:48:35
899	20	2026-03-03 17:48:35
900	UE40F8000	2026-03-03 17:48:35
901	10	2026-03-03 17:48:35
902	Ps	2026-03-03 17:48:35
903	212	2026-03-03 17:48:35
904	NL 9206	2026-03-03 17:48:35
905	KLVF-X	2026-03-03 17:48:35
906	G5	2026-03-03 17:48:35
907	CPS600E	2026-03-03 17:48:35
908	Nitro	2026-03-03 17:48:35
909	WDI9	2026-03-03 17:48:35
910	FS-1030MFP	2026-03-03 17:48:35
911	MFC-L2700DWR	2026-03-03 17:48:35
912	75	2026-03-03 17:48:35
913	20000	2026-03-03 17:48:35
914	3Z6TOES	2026-03-03 17:48:35
915	35S	2026-03-03 17:48:35
916	DC-45V	2026-03-03 17:48:35
917	FS-1035	2026-03-03 17:48:35
918	2 блока	2026-03-03 17:48:35
919	8QXL	2026-03-03 17:48:35
920	Royal	2026-03-03 17:48:35
921	Алиса	2026-03-03 17:48:35
922	X27G	2026-03-03 17:48:35
923	40R553	2026-03-03 17:48:35
924	HL-1110R	2026-03-03 17:48:35
925	T470	2026-03-03 17:48:35
926	K56C	2026-03-03 17:48:35
927	C660-2DD	2026-03-03 17:48:35
928	Vacoom-mop	2026-03-03 17:48:35
929	32LN613	2026-03-03 17:48:35
930	M3535	2026-03-03 17:48:35
931	326AFU	2026-03-03 17:48:35
932	Мидл	2026-03-03 17:48:35
933	EC-70	2026-03-03 17:48:36
934	LP80	2026-03-03 17:48:36
935	N150 Plus	2026-03-03 17:48:36
936	Ellix30	2026-03-03 17:48:36
937	Newtone-vs	2026-03-03 17:48:36
938	RTX3070	2026-03-03 17:48:36
939	22-c0006ur	2026-03-03 17:48:36
940	FX504	2026-03-03 17:48:36
941	Vita	2026-03-03 17:48:36
942	135w	2026-03-03 17:48:36
943	ThinBook 15 G2 ITL	2026-03-03 17:48:36
944	Note 10Pro	2026-03-03 17:48:36
945	NAS542	2026-03-03 17:48:36
946	10000	2026-03-03 17:48:36
947	UE32EH40000	2026-03-03 17:48:36
948	WDl9	2026-03-03 17:48:36
949	M6500, M1132	2026-03-03 17:48:36
950	42LB561V	2026-03-03 17:48:36
951	P30	2026-03-03 17:48:36
952	RedmiBook 15	2026-03-03 17:48:36
953	VSX-5267-K	2026-03-03 17:48:36
954	R-N301	2026-03-03 17:48:36
955	42LS560	2026-03-03 17:48:36
956	32LJ594	2026-03-03 17:48:36
957	H32D	2026-03-03 17:48:36
958	C660-14J	2026-03-03 17:48:36
959	SVE151C11V	2026-03-03 17:48:36
960	17-ab413ur	2026-03-03 17:48:36
961	N17W7	2026-03-03 17:48:36
962	X-BOX ONE S	2026-03-03 17:48:36
963	15-bs508ur	2026-03-03 17:48:36
964	8265NG	2026-03-03 17:48:36
965	737	2026-03-03 17:48:36
966	Sx530hs	2026-03-03 17:48:36
967	X705M	2026-03-03 17:48:37
968	Pulse 3	2026-03-03 17:48:37
969	FX504G	2026-03-03 17:48:37
970	2751	2026-03-03 17:48:37
971	X-Box one S	2026-03-03 17:48:37
972	Alutech	2026-03-03 17:48:37
973	CHUWI	2026-03-03 17:48:37
974	20H1-S00E00	2026-03-03 17:48:37
975	LT32E310	2026-03-03 17:48:37
976	8225	2026-03-03 17:48:37
977	R429M	2026-03-03 17:48:37
978	СН-20000	2026-03-03 17:48:37
979	106A	2026-03-03 17:48:37
980	PS4PRO	2026-03-03 17:48:37
981	15КВ	2026-03-03 17:48:37
982	БУ	2026-03-03 17:48:37
983	TUF	2026-03-03 17:48:37
984	X540L	2026-03-03 17:48:37
985	M12bg	2026-03-03 17:48:37
986	L3 15ITL6	2026-03-03 17:48:37
987	3000	2026-03-03 17:48:37
988	1641	2026-03-03 17:48:37
989	Syntia	2026-03-03 17:48:37
990	23LEN60	2026-03-03 17:48:37
991	Silver	2026-03-03 17:48:37
992	32FR250	2026-03-03 17:48:37
993	107w	2026-03-03 17:48:37
994	DCP-8070	2026-03-03 17:48:37
995	32PFL	2026-03-03 17:48:37
996	UE32	2026-03-03 17:48:37
997	X550C	2026-03-03 17:48:37
998	R450	2026-03-03 17:48:37
999	UM431D	2026-03-03 17:48:37
1000	24LED	2026-03-03 17:48:37
1001	Aspire 5742	2026-03-03 17:48:37
1002	42LB677	2026-03-03 17:48:37
1003	UE22	2026-03-03 17:48:37
1004	550	2026-03-03 17:48:37
1005	KDL-32S2000	2026-03-03 17:48:37
1006	3210	2026-03-03 17:48:37
1007	X8SE	2026-03-03 17:48:37
1008	EON-15	2026-03-03 17:48:37
1009	M212mf	2026-03-03 17:48:38
1010	MS-1688	2026-03-03 17:48:38
1011	5000	2026-03-03 17:48:38
1012	CTN610	2026-03-03 17:48:38
1013	Charge3	2026-03-03 17:48:38
1014	LE32	2026-03-03 17:48:38
1015	8300	2026-03-03 17:48:38
1016	5230	2026-03-03 17:48:38
1017	L355	2026-03-03 17:48:38
1018	250G8	2026-03-03 17:48:38
1019	T500	2026-03-03 17:48:38
1020	7100	2026-03-03 17:48:38
1021	YNDX-0008	2026-03-03 17:48:38
1022	X542UQ-DM282T	2026-03-03 17:48:38
1023	MHC-V77	2026-03-03 17:48:38
1024	M368	2026-03-03 17:48:38
1025	R-540	2026-03-03 17:48:38
1026	E5-771	2026-03-03 17:48:38
1027	Kdl43we755	2026-03-03 17:48:38
1028	LE40B530	2026-03-03 17:48:38
1029	S	2026-03-03 17:48:38
1030	Mf249dw	2026-03-03 17:48:38
1031	M227fdw	2026-03-03 17:48:38
1032	DV6-2019er	2026-03-03 17:48:38
1033	49LJ622V	2026-03-03 17:48:38
1034	12000	2026-03-03 17:48:39
1035	M236	2026-03-03 17:48:39
1036	D3400	2026-03-03 17:48:39
1037	5800	2026-03-03 17:48:39
1038	15-bw505ur	2026-03-03 17:48:39
1039	13-an0075	2026-03-03 17:48:39
1040	UX31A	2026-03-03 17:48:39
1041	190	2026-03-03 17:48:39
1042	F40E8000Q	2026-03-03 17:48:39
1043	От ворот	2026-03-03 17:48:39
1044	3 mini pro	2026-03-03 17:48:39
1045	TS3140	2026-03-03 17:48:39
1046	15000	2026-03-03 17:48:39
1047	Kx-mb2000	2026-03-03 17:48:39
1048	MS-70	2026-03-03 17:48:39
1049	Redmi Note 7	2026-03-03 17:48:39
1050	HS61	2026-03-03 17:48:39
1051	HONOR	2026-03-03 17:48:39
1052	HeroBook Pro	2026-03-03 17:48:39
1053	PJD5155	2026-03-03 17:48:39
1054	UE32J5120	2026-03-03 17:48:40
1055	GTX760 2GB	2026-03-03 17:48:40
1056	GTK-XB7	2026-03-03 17:48:40
1057	S-1000-15	2026-03-03 17:48:40
1058	18000	2026-03-03 17:48:40
1059	IPhone 7	2026-03-03 17:48:40
1060	Redmi Note 5	2026-03-03 17:48:40
1061	2.1	2026-03-03 17:48:40
1062	Iphone XR	2026-03-03 17:48:40
1063	7600	2026-03-03 17:48:40
1064	SB-1050	2026-03-03 17:48:40
1065	2.0	2026-03-03 17:48:40
1066	Cdz1902	2026-03-03 17:48:40
1067	15dh1003	2026-03-03 17:48:40
1068	AVH-Z5200BT	2026-03-03 17:48:40
1069	179fnw	2026-03-03 17:48:40
1070	292	2026-03-03 17:48:40
1071	PVCR-0726W	2026-03-03 17:48:40
1072	GL703GS	2026-03-03 17:48:40
1073	Note 9 Pro	2026-03-03 17:48:40
1074	M3040dn	2026-03-03 17:48:40
1075	EOS1300D	2026-03-03 17:48:40
1076	Y540	2026-03-03 17:48:40
1077	Flip 5	2026-03-03 17:48:40
1078	G505	2026-03-03 17:48:40
1079	HVY-WAP9	2026-03-03 17:48:40
1080	VCR20B	2026-03-03 17:48:40
1081	T-580	2026-03-03 17:48:40
1082	28	2026-03-03 17:48:40
1083	Flip 6	2026-03-03 17:48:40
1084	M2020	2026-03-03 17:48:40
1085	LC32	2026-03-03 17:48:40
1086	HD3067	2026-03-03 17:48:40
1087	PCG-71211V	2026-03-03 17:48:40
1088	VSS-1800	2026-03-03 17:48:40
1089	4S	2026-03-03 17:48:40
1090	50LEX	2026-03-03 17:48:40
1091	XB60	2026-03-03 17:48:40
1092	NP-RV515	2026-03-03 17:48:40
1093	D3100	2026-03-03 17:48:40
1094	MS2271	2026-03-03 17:48:40
1095	15ITL05	2026-03-03 17:48:40
1096	AUM-L41	2026-03-03 17:48:40
1097	LBP 6020	2026-03-03 17:48:40
1098	SCX-4200	2026-03-03 17:48:41
1099	UE32F6400AK	2026-03-03 17:48:41
1100	3204	2026-03-03 17:48:41
1101	MM720	2026-03-03 17:48:41
1102	Boh-WAP9R	2026-03-03 17:48:41
1103	15s-eq1041ur	2026-03-03 17:48:41
1104	LED32	2026-03-03 17:48:41
1105	33214	2026-03-03 17:48:41
1106	LR42	2026-03-03 17:48:41
1107	50	2026-03-03 17:48:41
1108	E-520	2026-03-03 17:48:41
1109	CUH-2108B	2026-03-03 17:48:41
1110	X540M	2026-03-03 17:48:41
1111	PoE	2026-03-03 17:48:41
1112	FS-8525, M6500	2026-03-03 17:48:41
1113	M6502	2026-03-03 17:48:41
1114	Svs15a11v	2026-03-03 17:48:41
1115	32NL541U	2026-03-03 17:48:41
1116	FS	2026-03-03 17:48:41
1117	UE40ES	2026-03-03 17:48:41
1118	1226	2026-03-03 17:48:41
1119	Extreme 3	2026-03-03 17:48:41
1120	DC-50F	2026-03-03 17:48:41
1121	TPN-C125	2026-03-03 17:48:41
1122	Robot-Vacuum	2026-03-03 17:48:41
1123	M4020ND	2026-03-03 17:48:41
1124	UE32H4000	2026-03-03 17:48:41
1125	MB2740	2026-03-03 17:48:41
1126	C156	2026-03-03 17:48:41
1127	XBox One X	2026-03-03 17:48:41
1128	Max Pro v3	2026-03-03 17:48:41
1129	UX535L	2026-03-03 17:48:42
1130	MVH-29BT	2026-03-03 17:48:42
1131	WFQ9	2026-03-03 17:48:42
1132	RTL8223	2026-03-03 17:48:42
1133	B50-30	2026-03-03 17:48:42
1134	2020	2026-03-03 17:48:42
1135	42LD750	2026-03-03 17:48:42
1136	8	2026-03-03 17:48:42
1137	10KW	2026-03-03 17:48:42
1138	15-cs	2026-03-03 17:48:42
1139	One S	2026-03-03 17:48:42
1140	G50	2026-03-03 17:48:42
1141	1000	2026-03-03 17:48:42
1142	411dw	2026-03-03 17:48:42
1143	BDP-S485	2026-03-03 17:48:42
1144	DZ850M	2026-03-03 17:48:42
1145	SM-T560	2026-03-03 17:48:42
1146	2410	2026-03-03 17:48:42
1147	HS-386	2026-03-03 17:48:42
1148	BhR-WAP9HNRP	2026-03-03 17:48:42
1149	Newton-fs	2026-03-03 17:48:42
1150	L340-15irh	2026-03-03 17:48:42
1151	510R	2026-03-03 17:48:42
1152	C810	2026-03-03 17:48:42
1153	81N3	2026-03-03 17:48:42
1154	X200CA	2026-03-03 17:48:42
1155	ES1-111	2026-03-03 17:48:42
1156	Extreme	2026-03-03 17:48:42
1157	СПН-13500	2026-03-03 17:48:42
1158	Kdl-32we613	2026-03-03 17:48:42
1159	UX533F	2026-03-03 17:48:42
1160	42`	2026-03-03 17:48:42
1161	MF-4018	2026-03-03 17:48:42
1162	Pixma	2026-03-03 17:48:42
1163	43Р717	2026-03-03 17:48:42
1164	50W808	2026-03-03 17:48:42
1165	N16C1	2026-03-03 17:48:42
1166	550D	2026-03-03 17:48:42
1167	2452	2026-03-03 17:48:42
1168	600D	2026-03-03 17:48:42
1169	911 Air Wave D	2026-03-03 17:48:43
1170	A315-51	2026-03-03 17:48:43
1171	Dv5-1030ee	2026-03-03 17:48:43
1172	42LB620V	2026-03-03 17:48:43
1173	АСН-1500	2026-03-03 17:48:43
1174	Cordless	2026-03-03 17:48:43
1175	43LT5900	2026-03-03 17:48:43
1176	CNBRN3S1LT	2026-03-03 17:48:43
1177	Pulse4	2026-03-03 17:48:43
1178	ECAM 22.110	2026-03-03 17:48:43
1179	7032	2026-03-03 17:48:43
1180	4070	2026-03-03 17:48:43
1181	ML-1641	2026-03-03 17:48:43
1182	M513U	2026-03-03 17:48:43
1183	TN-241BK	2026-03-03 17:48:43
1184	30G	2026-03-03 17:48:43
1185	24	2026-03-03 17:48:43
1186	42PJ353	2026-03-03 17:48:43
1187	Mi robot vacoum	2026-03-03 17:48:43
1188	Aspire V3	2026-03-03 17:48:43
1189	M10	2026-03-03 17:48:43
1190	43	2026-03-03 17:48:43
1191	13-an0087ur	2026-03-03 17:48:43
1192	426 + LBP2600	2026-03-03 17:48:43
1193	Yndx-0001	2026-03-03 17:48:43
1194	Ue40k5550bu	2026-03-03 17:48:43
1195	N15W4	2026-03-03 17:48:43
1196	EX-2519	2026-03-03 17:48:43
1197	Kdl-32r303c	2026-03-03 17:48:43
1198	DeLuxe	2026-03-03 17:48:43
1199	Nespresso	2026-03-03 17:48:43
1200	Incanto	2026-03-03 17:48:43
1201	Aroma G3	2026-03-03 17:48:43
1202	Xtreme	2026-03-03 17:48:43
1203	M2835	2026-03-03 17:48:43
1204	TX-PR50	2026-03-03 17:48:43
1205	PicoBarista DELUX	2026-03-03 17:48:44
1206	M1212nf	2026-03-03 17:48:44
1207	Y700-17ISK	2026-03-03 17:48:44
1208	1612WR	2026-03-03 17:48:44
1209	UE32EH5007K	2026-03-03 17:48:44
1210	T-555	2026-03-03 17:48:44
1211	CFI-1008A	2026-03-03 17:48:44
1212	HN-W19R	2026-03-03 17:48:44
1213	Ideapad 330S-15IKB	2026-03-03 17:48:44
1214	32LF653V	2026-03-03 17:48:44
1215	3640S	2026-03-03 17:48:44
1216	ML-1660	2026-03-03 17:48:44
1217	Laninude D830	2026-03-03 17:48:44
1218	L775	2026-03-03 17:48:44
1219	J215A	2026-03-03 17:48:44
1220	721	2026-03-03 17:48:44
1221	NP-R510H	2026-03-03 17:48:44
1222	Fs1120	2026-03-03 17:48:44
1223	15 d000sr	2026-03-03 17:48:44
1224	CLV-650-CFHD	2026-03-03 17:48:44
1225	CUH-1108A	2026-03-03 17:48:44
1226	SF314-51	2026-03-03 17:48:44
1227	АСН-3000	2026-03-03 17:48:44
1228	Aspire V5	2026-03-03 17:48:44
1229	XBOX 360S	2026-03-03 17:48:44
1230	Серая	2026-03-03 17:48:44
1231	A315-41G	2026-03-03 17:48:44
1232	UE50	2026-03-03 17:48:44
1233	1140	2026-03-03 17:48:44
1234	218	2026-03-03 17:48:44
1235	Vostro 3500	2026-03-03 17:48:44
1236	42PFL	2026-03-03 17:48:44
1237	EOS 6D	2026-03-03 17:48:44
1238	135r	2026-03-03 17:48:44
1239	X554L	2026-03-03 17:48:44
1240	P1005	2026-03-03 17:48:45
1241	KDL-40	2026-03-03 17:48:45
1242	103	2026-03-03 17:48:45
1243	WFH9	2026-03-03 17:48:45
1244	L3100	2026-03-03 17:48:45
1245	6Tb	2026-03-03 17:48:45
1246	Pro 400	2026-03-03 17:48:45
1247	KDL55W	2026-03-03 17:48:45
1248	Zino Pro+	2026-03-03 17:48:45
1249	EC145	2026-03-03 17:48:45
1250	Aspire 3 A314 Model N20Q1	2026-03-03 17:48:45
1251	Satellite A300	2026-03-03 17:48:45
1252	Aroma	2026-03-03 17:48:45
1253	D522	2026-03-03 17:48:45
1254	L1300	2026-03-03 17:48:45
1255	Air2s	2026-03-03 17:48:45
1256	NP880Z5E	2026-03-03 17:48:45
1257	Картридж NV-Print CB435A/CB436A/CE285A/725 для HP LJ P1005/ P1505/ M1120/ M1522, LJ Pro P1102, Canon LBP6000 (1600стр.) NV-CB435A/436A/285/725	2026-03-03 17:48:45
1258	Eee PC 1000H	2026-03-03 17:48:45
1259	PS4 (1108)	2026-03-03 17:48:45
1260	Q31C	2026-03-03 17:48:45
1261	---	2026-03-03 17:48:45
1262	2740	2026-03-03 17:48:45
1263	LBP6000	2026-03-03 17:48:45
1264	LT-32M540	2026-03-03 17:48:45
1265	X542U	2026-03-03 17:48:45
1266	N76VB	2026-03-03 17:48:45
1267	WX91A68	2026-03-03 17:48:45
1268	HLYL-WFQ9	2026-03-03 17:48:45
1269	AN515-42	2026-03-03 17:48:45
1270	HP 15-ac679ur	2026-03-03 17:48:45
1271	XMA2002-AJ	2026-03-03 17:48:45
1272	NP-R540	2026-03-03 17:48:45
1273	G780	2026-03-03 17:48:45
1274	2520	2026-03-03 17:48:45
1275	M2010J19CG	2026-03-03 17:48:45
1276	С460W	2026-03-03 17:48:45
1277	UX303U	2026-03-03 17:48:45
1278	MFP M132A	2026-03-03 17:48:46
1279	700	2026-03-03 17:48:46
1280	EER73	2026-03-03 17:48:46
1281	Пылесоса	2026-03-03 17:48:46
1282	40PFL	2026-03-03 17:48:46
1283	15s-eq2013ur	2026-03-03 17:48:46
1284	P2251	2026-03-03 17:48:46
1285	WP511	2026-03-03 17:48:46
1286	M426dw	2026-03-03 17:48:46
1287	HP 250 G7	2026-03-03 17:48:46
1288	K3500P	2026-03-03 17:48:46
1289	1024 ГБ	2026-03-03 17:48:46
1290	Xperia	2026-03-03 17:48:46
1291	Dv7-610er	2026-03-03 17:48:46
1292	J510	2026-03-03 17:48:46
1293	FX-750	2026-03-03 17:48:46
1294	742	2026-03-03 17:48:46
1295	SL-1509	2026-03-03 17:48:46
1296	50PK560-ZA	2026-03-03 17:48:46
1297	3145dn	2026-03-03 17:48:46
1298	15-db1146ur	2026-03-03 17:48:46
1299	Air2	2026-03-03 17:48:46
1300	15-bw664ur	2026-03-03 17:48:46
1301	5755G	2026-03-03 17:48:46
1302	UE40EH5000	2026-03-03 17:48:46
1303	HL-22	2026-03-03 17:48:46
1304	179	2026-03-03 17:48:46
1305	135	2026-03-03 17:48:46
1306	FX505DT	2026-03-03 17:48:46
1307	Ultima-M7	2026-03-03 17:48:46
1308	MI Box	2026-03-03 17:48:46
1309	Бойлера	2026-03-03 17:48:46
1310	SmartTV 40	2026-03-03 17:48:46
1311	5526	2026-03-03 17:48:47
1312	F0D6	2026-03-03 17:48:47
1313	Ideapad 330	2026-03-03 17:48:47
1314	Dell	2026-03-03 17:48:47
1315	2200	2026-03-03 17:48:47
1316	Air 2	2026-03-03 17:48:47
1317	QX1222USB	2026-03-03 17:48:47
1318	SF314-52	2026-03-03 17:48:47
1319	VS-524	2026-03-03 17:48:47
1320	HN-W29R	2026-03-03 17:48:47
1321	Синяя	2026-03-03 17:48:47
1322	15-ra058ur	2026-03-03 17:48:47
1323	HD 3900	2026-03-03 17:48:47
1324	M201n	2026-03-03 17:48:47
1325	M28W	2026-03-03 17:48:47
1326	100-15IBY	2026-03-03 17:48:47
1327	RoboVac25C	2026-03-03 17:48:47
1328	330-15IKB	2026-03-03 17:48:47
1329	SM-07M	2026-03-03 17:48:47
1330	32LJ500U	2026-03-03 17:48:47
1331	PS4 CUH-7208B	2026-03-03 17:48:47
1332	Триколор	2026-03-03 17:48:47
1333	CT-6100	2026-03-03 17:48:47
1334	PS$	2026-03-03 17:48:47
1335	135wr	2026-03-03 17:48:47
1336	3045	2026-03-03 17:48:47
1337	15IGL05	2026-03-03 17:48:47
1338	55LA970	2026-03-03 17:48:47
1339	150a	2026-03-03 17:48:47
1340	Charge 3	2026-03-03 17:48:47
1341	15-da0548ur	2026-03-03 17:48:47
1342	NP355V5C	2026-03-03 17:48:47
1343	L1752S	2026-03-03 17:48:47
1344	X550Z	2026-03-03 17:48:47
1345	C850-D1K	2026-03-03 17:48:48
1346	49"	2026-03-03 17:48:48
1347	W270EGQ	2026-03-03 17:48:48
1348	CT-6140	2026-03-03 17:48:48
1349	MF249dw	2026-03-03 17:48:48
1350	7045	2026-03-03 17:48:48
1351	LG32LF592	2026-03-03 17:48:48
1352	A315-536-34Zt	2026-03-03 17:48:48
1353	Z170	2026-03-03 17:48:48
1354	55UK	2026-03-03 17:48:48
1355	ХЗ	2026-03-03 17:48:48
1356	G100	2026-03-03 17:48:48
1357	K53T	2026-03-03 17:48:48
1358	15сы3073с1	2026-03-03 17:48:48
1359	Braun	2026-03-03 17:48:48
1360	Aura	2026-03-03 17:48:48
1361	436dn	2026-03-03 17:48:48
1362	2235dn	2026-03-03 17:48:48
1363	55UK64	2026-03-03 17:48:48
1364	39V51	2026-03-03 17:48:48
1365	LG	2026-03-03 17:48:48
1366	BPS-750C2	2026-03-03 17:48:48
1367	HI	2026-03-03 17:48:48
1368	H32F7000K	2026-03-03 17:48:48
1369	G500	2026-03-03 17:48:48
1370	M6502W	2026-03-03 17:48:48
1371	ACH-5000	2026-03-03 17:48:48
1372	PS 4, PS 5	2026-03-03 17:48:48
1373	ПТ-81ЖК	2026-03-03 17:48:48
1374	XC330S	2026-03-03 17:48:48
1375	SB1050	2026-03-03 17:48:48
1376	RX580	2026-03-03 17:48:48
1377	352	2026-03-03 17:48:49
1378	GL-30	2026-03-03 17:48:49
1379	HP 250 G3	2026-03-03 17:48:49
1380	65UK6100PLA	2026-03-03 17:48:49
1381	15-p06tsr	2026-03-03 17:48:49
1382	SP	2026-03-03 17:48:49
1383	Системный блок	2026-03-03 17:48:49
1384	554MV0	2026-03-03 17:48:49
1385	NBR-WA/9	2026-03-03 17:48:49
1386	LG 42PW450	2026-03-03 17:48:49
1387	2535	2026-03-03 17:48:49
1388	MS-179B	2026-03-03 17:48:49
1389	V3-571G	2026-03-03 17:48:49
1390	G50-45	2026-03-03 17:48:49
1391	G6-2163sr	2026-03-03 17:48:49
1392	M2030dn	2026-03-03 17:48:49
1393	S540-14IML	2026-03-03 17:48:49
1394	Omni 27	2026-03-03 17:48:49
1395	4020	2026-03-03 17:48:49
1396	B570e	2026-03-03 17:48:49
1397	Spectre X360	2026-03-03 17:48:49
1398	Sony	2026-03-03 17:48:49
1399	15-ac001ur	2026-03-03 17:48:49
1400	HP 1018	2026-03-03 17:48:49
1401	S145-15	2026-03-03 17:48:49
1402	13aw-207ur	2026-03-03 17:48:49
1403	Aspire 5551	2026-03-03 17:48:49
1404	MS-16W	2026-03-03 17:48:49
1405	Asus X550Z	2026-03-03 17:48:49
1406	MF4120	2026-03-03 17:48:49
1407	K55N	2026-03-03 17:48:49
1408	Ноутбук Asus X550C	2026-03-03 17:48:49
1409	DCP-1512R	2026-03-03 17:48:49
1410	6015	2026-03-03 17:48:49
1411	M475dn	2026-03-03 17:48:49
1412	132	2026-03-03 17:48:49
1413	Ноутбук HP 15-r272ur	2026-03-03 17:48:50
1414	X1-yoga	2026-03-03 17:48:50
1415	Ноутбук Lenovo B50-70	2026-03-03 17:48:50
1416	MF641CW	2026-03-03 17:48:50
1417	SCX-4521F	2026-03-03 17:48:50
1418	Ноутбук MSI MS-17E8	2026-03-03 17:48:50
1419	A315-41	2026-03-03 17:48:50
1420	Системный блок Elton	2026-03-03 17:48:50
1421	Ноутбук Lenovo Legion 7	2026-03-03 17:48:50
1422	HP M180n	2026-03-03 17:48:50
1423	Ноутбук Asus K750	2026-03-03 17:48:50
1424	CLP-310	2026-03-03 17:48:50
1425	Ноутбук Dell Vostro 15	2026-03-03 17:48:50
1426	Ga401I	2026-03-03 17:48:50
1427	TPN-C126	2026-03-03 17:48:50
1428	Ноутбук DNS W170ER	2026-03-03 17:48:50
1429	Flip Essential	2026-03-03 17:48:50
1430	M104a	2026-03-03 17:48:50
1431	Pheser 6000	2026-03-03 17:48:50
1432	R522M	2026-03-03 17:48:50
1433	GL752V	2026-03-03 17:48:50
1434	P1102s	2026-03-03 17:48:50
1435	V3-572G	2026-03-03 17:48:50
1436	2040dn	2026-03-03 17:48:50
1437	GL504G	2026-03-03 17:48:50
1438	MFC8520dn	2026-03-03 17:48:50
1439	CP1515n	2026-03-03 17:48:50
1440	A315-53-P8FK	2026-03-03 17:48:50
1441	LBP3010B	2026-03-03 17:48:50
1442	L5750DW	2026-03-03 17:48:50
1443	179атц	2026-03-03 17:48:50
1444	HT-210	2026-03-03 18:55:29
1445	CHOISE	2026-03-03 18:55:29
1446	10Квт и 8Квт	2026-03-03 18:55:29
1447	2100	2026-03-03 18:55:30
1448	M125rnw	2026-03-03 18:55:30
1449	One	2026-03-03 18:55:30
1450	M2735Dn	2026-03-03 18:55:30
1451	Cappuccino	2026-03-03 18:55:30
1452	B001	2026-03-03 18:55:30
1453	2023-08	2026-03-03 18:55:30
1454	Красный	2026-03-03 18:55:31
1455	M5526cdn	2026-03-03 18:55:31
1456	Серебристая	2026-03-03 18:55:31
1457	SP150	2026-03-03 18:55:31
1458	00020	2026-03-03 18:55:31
1459	Vw224	2026-03-04 08:58:31
1460	3010 и 2040	2026-03-04 10:18:15
1461	Fx608	2026-03-05 11:03:40
1462	15-db1231	2026-03-06 11:44:06
1463	- a315-24	2026-03-10 10:03:55
1464	Yoga 500	2026-03-11 11:43:35
1465	Legion	2026-03-12 13:37:51
1466	Dinamica plus	2026-03-14 12:25:46
1467	EA877	2026-03-19 08:53:42
1468	6230cidn	2026-03-20 14:58:31
1469	M6700DW	2026-03-23 11:12:27
1470	164100	2026-03-25 13:35:01
1471	SCX-3405	2026-03-26 08:32:15
1472	M6005	2026-03-31 06:45:12.065535
1473	K541	2026-03-31 08:48:46.191614
1474	A1369	2026-03-31 09:03:34.711737
1475	X550cc	2026-04-01 08:12:51.792837
1476	M6557NW	2026-04-01 14:50:45.555877
1477	8300W	2026-04-02 08:03:54.152835
1478	M203dn	2026-04-02 14:44:23.177648
1479	CM1415fn	2026-04-07 13:54:52.323355
\.


--
-- Data for Name: order_parts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_parts (id, order_id, part_id, name, quantity, price, purchase_price, created_at, base_price, discount_type, discount_value, warranty_days, executor_id) FROM stdin;
\.


--
-- Data for Name: order_services; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_services (id, order_id, service_id, name, quantity, price, created_at, base_price, cost_price, discount_type, discount_value, warranty_days, executor_id) FROM stdin;
\.


--
-- Data for Name: order_status_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_status_history (id, order_id, old_status_id, new_status_id, changed_by, changed_by_username, comment, created_at) FROM stdin;
\.


--
-- Data for Name: order_statuses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_statuses (id, code, name, color, is_default, sort_order, created_at, group_name, triggers_payment_modal, accrues_salary, is_archived, is_final, blocks_edit, requires_warranty, requires_comment, client_name, client_description, salary_rule_type, salary_rule_value) FROM stdin;
1	closed	Закрыт	#6b6b6b	0	5	2026-03-03 17:47:45	Закрытые успешно	1	1	0	1	1	0	0	\N	\N	\N	\N
2	закрыт_неуспешно	Закрыт неуспешно	#cccccc	0	10	2026-03-03 17:47:45	Закрытые неуспешно	0	0	0	1	1	0	0	\N	\N	\N	\N
3	новый	Новый	#0084ff	1	0	2026-03-03 17:47:48	Новые	0	0	0	0	0	0	0	\N	\N	\N	\N
4	ждет_запчасть	Ждет запчасть	#00ffaa	0	9	2026-03-03 17:47:48	Отложенные	0	0	0	0	1	0	1	\N	\N	\N	\N
5	в_работе_у_александра	В работе у Александра	#73ff00	0	6	2026-03-03 17:47:54	В работе	0	0	0	0	0	0	0	\N	\N	\N	\N
6	незабирашка	Незабирашка	#cccccc	0	11	2026-03-03 17:47:54	Отложенные	0	0	0	0	0	0	0	\N	\N	\N	\N
7	диагностика	Диагностика	#ff0000	0	8	2026-03-03 17:47:58	В работе	0	0	0	0	0	0	0	\N	\N	\N	\N
8	на_запчасти	На запчасти	#787878	0	12	2026-03-03 17:48:03	Закрытые неуспешно	0	0	0	1	1	0	0	\N	\N	\N	\N
9	согласование	Согласование	#ffc800	0	7	2026-03-03 17:48:38	В работе	0	0	0	0	0	0	0	\N	\N	\N	\N
10	v_rabote_u_andreya	В работе у Андрея	#ff00dd	0	3	2026-03-03 18:25:52	В работе	0	0	0	0	0	0	0	\N	\N	\N	\N
11	в_работе_у_сергея_01	В работе у Сергея 01	#007bff	0	4	2026-03-03 18:55:29	\N	0	0	0	0	0	0	0	\N	\N	\N	\N
12	v_rabote_u_sergeya	В работе у Сергея	#831100	0	2	2026-03-04 09:20:29	В работе	0	0	0	0	0	0	0	\N	\N	\N	\N
13	gotov	Готов	#ff6600	0	1	2026-03-08 08:51:07	Готовые	0	0	0	0	1	0	0	\N	\N	\N	\N
\.


--
-- Data for Name: order_symptoms; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_symptoms (id, order_id, symptom_id, created_at) FROM stdin;
\.


--
-- Data for Name: order_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_templates (id, name, description, template_data, created_by, is_public, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: order_visibility_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_visibility_history (id, order_id, hidden, changed_by, changed_at, reason) FROM stdin;
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.orders (id, order_id, device_id, customer_id, manager_id, master_id, status, prepayment, password, appearance, comment, created_at, updated_at, symptom_tags, intake_checklist, status_id, hidden, model, model_id, prepayment_cents, is_deleted, deleted_at, deleted_by_id, deleted_reason) FROM stdin;
\.


--
-- Data for Name: part_categories; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.part_categories (id, name, description, created_at, updated_at, parent_id) FROM stdin;
1	Импорт	\N	2026-03-03 17:47:44	2026-03-03 17:47:44	\N
2	SSD	\N	2026-03-03 17:47:44	2026-03-03 17:47:44	\N
3	Подушки, краска штемпельная	\N	2026-03-03 17:47:44	2026-03-03 17:47:44	\N
4	Изготовление печатей	\N	2026-03-03 17:47:44	2026-03-03 17:47:44	\N
5	Оснастки автоматические	\N	2026-03-03 17:47:44	2026-03-03 17:47:44	\N
6	Картриджи	\N	2026-03-03 17:47:44	2026-03-03 17:47:44	\N
7	Оснастки ручные	\N	2026-03-03 17:47:44	2026-03-03 17:47:44	\N
8	Чипы	\N	2026-03-03 17:47:44	2026-03-03 17:47:44	\N
\.


--
-- Data for Name: parts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parts (id, name, part_number, description, price, stock_quantity, min_quantity, category, supplier, created_at, updated_at, purchase_price, unit, warranty_days, is_deleted, comment, category_id, salary_rule_type, salary_rule_value) FROM stdin;
1	Товары по заказу	Товары по заказу	\N	0	2	0	\N	\N	2026-03-03 17:47:44	2026-03-03 18:59:53	0	шт	\N	0	\N	1	\N	\N
2	128 ГБ 2.5" SATA накопитель Apacer AS350 PANTHER [95.DB260.P100C]	1319613	\N	1990	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	1099	шт	\N	0	\N	2	\N	\N
3	240 ГБ 2.5" SATA накопитель Neo Forza NFS12 [NFS121SA324-6007200]	5030570	\N	2550	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	1450	шт	\N	0	\N	2	\N	\N
4	240 ГБ SSD M.2 накопитель WD Green [WDS240G3G0B]	WDS240G3G0B	\N	2000	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	1699	шт	\N	0	\N	2	\N	\N
5	9051 Pocket офисная настольная СИНЯЯ штемпельная подушка 65*82 мм рабочее поле 54*77 мм, с замком фиксатором	172768150	\N	500	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	140	шт	\N	0	\N	3	\N	\N
6	9052 Deskmate офисная настольная КРАСНАЯ штемпельная подушка 70*110 мм в упаковке 12 штук	172768090	\N	500	19	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	138	шт	\N	0	\N	3	\N	\N
7	NEW !!! Резина лазерная GRM CLASSICO LUXE, серая без запаха, размер A4, толщина 2.3мм (Германия) Акция!	509107000tn1	\N	3000	2	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	1050	шт	\N	0	\N	4	\N	\N
10	Картридж 211	\N	\N	1800	2	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	400	шт	\N	0	\N	6	\N	\N
11	Картридж 2375	\N	\N	1500	3	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	400	шт	\N	0	\N	6	\N	\N
12	Картридж CE285A	Ce285a	\N	1000	2	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	248	шт	\N	0	\N	6	\N	\N
13	Картридж CF283A	CF283A	\N	1000	5	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	314	шт	\N	0	\N	6	\N	\N
14	Картридж D104s	\N	\N	1500	3	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	400	шт	\N	0	\N	6	\N	\N
15	Картридж D111	\N	\N	1800	1	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	400	шт	\N	0	\N	6	\N	\N
16	Картридж Q2612A	Q2612A	\N	1000	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	500	шт	\N	0	\N	6	\N	\N
17	Картридж TK-1170	1170	\N	1000	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	500	шт	\N	0	\N	6	\N	\N
18	Осн.руч.дер LG 120х60мм Бежевый (77_18038)	120х60	\N	800	2	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	228	шт	\N	0	\N	7	\N	\N
19	Осн.руч.дер LG 200х80мм Бежевый (77_18040)	200х80	\N	1000	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	358	шт	\N	0	\N	7	\N	\N
23	Оснастка для штампа Trodat, размер клише 75х38мм	\N	\N	1000	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	450	шт	\N	0	\N	5	\N	\N
24	Подушка для оснастки Trodat 6/4642 Неокрашенная (77_7484)	6/4642	\N	300	11	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	150	шт	\N	0	\N	3	\N	\N
25	Подушка наст. Trodat 9051 90х50 Синий (77_25)	9051	\N	400	4	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	124	шт	\N	0	\N	3	\N	\N
26	Подушка наст. Trodat 9053 160х90 Неокрашенная (77_918)	9053	\N	800	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	377	шт	\N	0	\N	3	\N	\N
27	Подушка наст. Trodat 9054 210х148 Черный (77_17362)	9054	\N	1900	2	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	1000	шт	\N	0	\N	3	\N	\N
28	Подшипники вала выхода бумаги JC61-01177A/JC61-03782A (пара) для SCX-3400/2020/3405 и др.	JC61	\N	500	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	425	шт	\N	0	\N	6	\N	\N
29	Ролики для Kyocera 3шт	111	\N	300	14	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	100	шт	\N	0	\N	6	\N	\N
30	Ручная ПЛОСКАЯ оснастка д.40 мм для круглой печати с клеевым слоем и штемп.материалом для микротекста	141400008	\N	500	26	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	280	шт	\N	0	\N	7	\N	\N
31	Ручная оснастка с ГЕРБОМ д.40 мм для круглой печати с клеевым слоем РТКВ40 Акция!	141400000tn1	\N	500	5	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	23	шт	\N	0	\N	7	\N	\N
32	Чип для Pantum PC-211, 1.6K	\N	\N	400	0	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	100	шт	\N	0	\N	8	\N	\N
33	Штемпельная краска Trodat 7011 красная	7011r	\N	300	3	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	80	шт	\N	0	\N	3	\N	\N
34	Штемпельная краска Trodat 7011 черная	7011b	\N	300	3	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	80	шт	\N	0	\N	3	\N	\N
35	Штемпельная краска Trodat 7011 фиолетовая	7011p	\N	300	2	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	80	шт	\N	0	\N	3	\N	\N
36	Штемпельная подушка TRODAT (110*70 мм) неокрашенная, для красок на водной основе, 9052	9052	\N	600	1	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	200	шт	\N	0	\N	3	\N	\N
37	Штемпельная подушка TRODAT 9051, 90*50 мм, НЕОКРАШЕННАЯ, 191052	\N	\N	500	1	0	\N	\N	2026-03-03 17:47:44	2026-03-03 17:48:27	150	шт	\N	0	\N	3	\N	\N
9	Карманная оснастка для печатей, Trodat Micro printy 9342	9342	\N	1000	9	0	\N	\N	2026-03-03 17:47:44	2026-03-30 19:47:49.74161	280.0	шт	\N	0	\N	5	\N	\N
22	Оснастка для штампа Trodat 4913 IDEAL, размер клише 58х22мм черная, цвет оттиска синий	4913	\N	1000	4	0	\N	\N	2026-03-03 17:47:44	2026-03-30 19:48:26.178691	280.0	шт	\N	0	\N	5	\N	\N
21	Оснастка для штампа Trodat  30мм	4911	\N	1000	2	0	\N	\N	2026-03-03 17:47:44	2026-04-02 14:38:52.48339	280	шт	\N	0	\N	5	\N	\N
20	Оснастка д/штампа 38*14мм (3-строчный) deVENTE 4115304	3814	\N	1000	3	0	\N	\N	2026-03-03 17:47:44	2026-04-06 14:51:00.863374	280.0	шт	\N	0	\N	5	\N	\N
8	Автоматическая оснастка Trodat Printy 4642 4.0 NEW.	4642	\N	1000	6	0	\N	\N	2026-03-03 17:47:44	2026-04-07 14:45:57.704173	280.0	шт	\N	0	\N	5	\N	\N
\.


--
-- Data for Name: payment_receipts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payment_receipts (id, payment_id, receipt_type, status, provider, provider_receipt_id, payload, response, error, created_by_id, created_by_username, created_at, printed_at) FROM stdin;
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payments (id, order_id, amount, payment_type, payment_date, created_by, created_by_username, comment, created_at, is_cancelled, cancelled_at, cancelled_reason, cancelled_by_id, cancelled_by_username, kind, status, idempotency_key, external_provider, external_payment_id, captured_at, refunded_of_id) FROM stdin;
\.


--
-- Data for Name: permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.permissions (id, name, description, created_at) FROM stdin;
1	view_orders	Просмотр заявок	2025-12-04 16:16:31
2	create_orders	Создание заявок	2025-12-04 16:16:31
3	edit_orders	Редактирование заявок	2025-12-04 16:16:31
4	delete_orders	Удаление заявок	2025-12-04 16:16:31
5	view_customers	Просмотр клиентов	2025-12-04 16:16:31
6	create_customers	Создание клиентов	2025-12-04 16:16:31
7	edit_customers	Редактирование клиентов	2025-12-04 16:16:31
8	delete_customers	Удаление клиентов	2025-12-04 16:16:31
9	view_warehouse	Просмотр склада	2025-12-04 16:16:31
10	manage_warehouse	Управление складом	2025-12-04 16:16:31
11	view_reports	Просмотр отчетов	2025-12-04 16:16:31
12	manage_settings	Управление настройками	2025-12-04 16:16:31
13	manage_users	Управление пользователями	2025-12-04 16:16:31
14	salary.view	Просмотр модуля зарплаты	2026-01-18 15:33:06
15	view_finance	Просмотр финансового модуля	2026-01-20 17:40:26
16	manage_finance	Управление финансовым модулем	2026-01-20 17:40:26
17	view_shop	Просмотр модуля Магазин	2026-01-20 17:40:26
18	manage_shop	Управление модулем Магазин	2026-01-20 17:40:26
19	view_action_logs	Просмотр логов действий	2026-01-20 17:40:26
20	manage_statuses	Управление статусами заявок	2026-01-20 17:40:26
\.


--
-- Data for Name: print_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.print_templates (id, name, template_type, html_content, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: purchase_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.purchase_items (id, purchase_id, part_id, quantity, purchase_price, total_price, created_at) FROM stdin;
\.


--
-- Data for Name: purchases; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.purchases (id, supplier_id, supplier_name, purchase_date, total_amount, status, notes, created_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: role_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.role_permissions (role, permission_id) FROM stdin;
viewer	1
viewer	5
master	1
master	2
master	3
master	5
master	9
master	14
manager	6
manager	2
manager	7
manager	3
manager	16
manager	18
manager	20
manager	14
manager	5
manager	1
manager	17
manager	9
manager	10
manager	11
manager	15
manager	19
admin	2
admin	4
admin	3
admin	1
admin	6
admin	8
admin	7
admin	5
admin	10
admin	9
admin	11
admin	16
admin	15
admin	18
admin	17
admin	12
admin	20
admin	13
admin	19
admin	14
\.


--
-- Data for Name: salary_accruals; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.salary_accruals (id, order_id, shop_sale_id, user_id, role, amount_cents, base_amount_cents, profit_cents, rule_type, rule_value, calculated_from, calculated_from_id, service_id, part_id, vat_included, created_at) FROM stdin;
\.


--
-- Data for Name: salary_bonuses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.salary_bonuses (id, user_id, role, amount_cents, reason, order_id, bonus_date, created_by_id, created_by_username, created_at) FROM stdin;
\.


--
-- Data for Name: salary_fines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.salary_fines (id, user_id, role, amount_cents, reason, order_id, fine_date, created_by_id, created_by_username, created_at) FROM stdin;
\.


--
-- Data for Name: salary_payments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.salary_payments (id, user_id, role, amount_cents, payment_date, period_start, period_end, payment_type, comment, created_by_id, created_by_username, created_at, cash_transaction_id) FROM stdin;
\.


--
-- Data for Name: schema_migrations_pg; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schema_migrations_pg (version, name, applied_at) FROM stdin;
001	enable_extensions	2026-03-30 19:09:14.906975
002	fulltext_indexes	2026-03-30 19:09:14.955335
003	fix_id_defaults	2026-03-30 19:09:15.035966
004	perf_indexes	2026-03-30 19:09:15.128414
005	staff_chat	2026-04-05 18:58:53.6558
006	staff_chat_reactions	2026-04-06 18:51:03.560068
007	staff_chat_read_cursors	2026-04-10 00:00:00
\.


--
-- Data for Name: services; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.services (id, name, price, is_default, sort_order, created_at, updated_at, salary_rule_type, salary_rule_value) FROM stdin;
1	Диагностика	1000	0	2	2026-03-03 17:47:44	2026-03-03 17:47:44	\N	\N
2	Ремонт проектора	1000	0	1	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
3	Переклейка печати	200	0	3	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
4	Заправка картриджа TK-3160	1500	0	4	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	150
5	Восстановление данных	2500	0	5	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
6	Ремонт игровой консоли PS4/PS5	2500	0	6	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
7	Прошивка электронного устройства	1500	0	7	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
8	Заправка картриджа Xerox	600	0	8	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	150
9	Ремонт	1500	0	9	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
10	Ремонт квадрокоптера	3500	0	10	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
11	Ремонт цепей питания	4000	0	11	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
12	Переклейка чипа в картридже	150	0	12	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
13	Замена матрицы	7500	0	13	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
14	Заправка картриджа Kyocera TK-475	2500	0	14	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	150
15	Замена подсветки телевизора 32"	3500	0	15	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
16	Ремонт платы управления	2500	0	16	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
17	Замена АКБ	1000	0	17	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
18	Замена сенсорной панели	1500	0	18	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
19	Замена стекла камеры	500	0	19	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
20	Замена дисплея	4000	0	20	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
21	Замена провода питания	1000	0	21	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
22	Замена платы управления	6000	0	22	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
23	Полная чистка, замена термоинтерфейса	2500	0	23	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
24	Ремонт смартфона	1500	0	24	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
25	Ремонт джойстика игровой приставки	1500	0	25	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
26	Обслуживание и ремонт ноутбука	4000	0	26	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
27	Полная чистка/декальцинация	3500	0	27	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
28	Ремонт блока питания телевизора	3500	0	28	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
29	Ремонт системного блока	3000	0	29	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
30	Ремонт блока питания	2000	0	30	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
31	Установка и настройка ОС	2500	0	31	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
32	Копирование / перенос данных	500	0	32	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
33	Чистка матрицы зеркального фотоаппарата	1500	0	33	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
34	Прошивка BIOS видеокарты	2000	0	34	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
35	Восстановление печатной платы	1000	0	35	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
36	Ремонт стабилизатора	1800	0	36	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
37	Ремонт акустической-системы	3000	0	37	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
38	Заправка картриджа TK-7310	2500	0	38	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	150
39	Заправка картриджа Brother	500	0	39	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	150
40	Настройка ПО	1000	0	40	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
41	Прошивка BIOS ноутбук\\системный блок	3500	0	41	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
42	Ремонт сканера штрих-кодов	1500	0	42	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
43	Обслуживание и ремонт системного блока	3500	0	43	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
44	Ремонт POS-принтера	1000	0	44	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
45	Заправка картриджа Samsung SCX-4200	600	0	45	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	150
46	Прошивка принтера\\МФУ А4 формата	2500	0	46	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
47	Изготовление клише для автоматической оснастки	1000	0	47	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	500
48	Заправка картриджа Pantum PC-211	800	0	48	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	150
49	Заправка картриджа Kyocera TK-1150\\1170\\1200	800	0	49	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	150
50	Диагностика системного блока\\моноблока	2000	0	50	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
51	Диагностика ноутбука	2000	0	51	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
52	Диагностика PS4\\Xbox	1500	0	52	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
53	Замена светодиодной подсветки	1000	0	53	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
54	Техническое обслуживание телевизора до 55 диагонали	1500	0	54	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
55	Изготовление клише для печати без оснастки	1200	0	55	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	500
56	Изготовление клише печати для ручной оснастки	1000	0	56	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
57	Изготовление клише копии печати	1300	0	57	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	500
58	Техническое обслуживание принтера\\МФУ  А4	2500	0	58	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
59	Прошивка игровой консоли PS3/PS4/PS5	2500	0	59	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
60	Чистка системного блока\\моноблока	1000	0	60	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
61	Техническое обслуживание ноутбука (чистка)	2500	0	61	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
62	Установка\\переустановка операционной системы	2000	0	62	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
63	Заправка картриджа HP 1010\\285\\278\\2612\\435\\283\\	500	0	63	2026-03-03 17:47:44	2026-03-03 17:48:27	fixed	150
64	Ремонт пос принтера	2000	0	64	2026-03-03 17:47:44	2026-03-03 17:48:27	\N	\N
\.


--
-- Data for Name: shop_sale_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shop_sale_items (id, shop_sale_id, item_type, service_id, service_name, part_id, part_name, part_sku, quantity, price, purchase_price, total, created_at) FROM stdin;
\.


--
-- Data for Name: shop_sales; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shop_sales (id, customer_id, customer_name, customer_phone, manager_id, master_id, total_amount, discount, final_amount, paid_amount, payment_method, comment, sale_date, created_by_id, created_by_username, created_at, order_id) FROM stdin;
\.


--
-- Data for Name: staff_chat_attachments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.staff_chat_attachments (id, message_id, original_name, stored_name, mime_type, size_bytes, file_path, is_image, created_at) FROM stdin;
\.


--
-- Data for Name: staff_chat_messages; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.staff_chat_messages (id, room_key, user_id, username, actor_display_name, client_instance_id, message_text, created_at, edited_at, deleted_at) FROM stdin;
\.


--
-- Data for Name: staff_chat_reactions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.staff_chat_reactions (id, message_id, user_id, username, actor_display_name, client_instance_id, emoji, created_at) FROM stdin;
\.


--
-- Data for Name: staff_chat_read_cursors; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.staff_chat_read_cursors (id, room_key, user_id, username, actor_display_name, client_instance_id, last_read_message_id, updated_at) FROM stdin;
\.


--
-- Data for Name: stock_movements; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.stock_movements (id, part_id, movement_type, quantity, reference_id, reference_type, created_by, notes, created_at) FROM stdin;
\.


--
-- Data for Name: suppliers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.suppliers (id, name, contact_person, phone, email, address, inn, comment, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: symptoms; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.symptoms (id, name, sort_order, created_at) FROM stdin;
1	Заказ печати	1	2026-03-03 17:47:45
2	Полная чистка	2	2026-03-03 17:47:45
3	Пайка платы	3	2026-03-03 17:47:45
4	Не включается	4	2026-03-03 17:47:45
5	Сброс до заводских + оффис	5	2026-03-03 17:47:45
6	Замена стиков	6	2026-03-03 17:47:45
7	Ремонт МФУ	7	2026-03-03 17:47:45
8	Диагностика	8	2026-03-03 17:47:45
9	Нет Изо	9	2026-03-03 17:47:45
10	Чистка ps4	10	2026-03-03 17:47:45
11	Заказ печатей	11	2026-03-03 17:47:45
12	Течёт	12	2026-03-03 17:47:45
13	Грязная печать	13	2026-03-03 17:47:45
14	Замена блока питания	14	2026-03-03 17:47:45
15	Не загружается (синий экран)	15	2026-03-03 17:47:45
16	Отломана клемма	16	2026-03-03 17:47:45
17	Заправка картриджей	17	2026-03-03 17:47:45
18	Сломана защелка	18	2026-03-03 17:47:45
19	Чистка	19	2026-03-03 17:47:45
20	Не работает	20	2026-03-03 17:47:45
21	Не делает капучино	21	2026-03-03 17:47:45
22	Проблема с датчиком воды	22	2026-03-03 17:47:45
23	Чистка и замена термпасты	23	2026-03-03 17:47:45
24	Диагностика подсветки	24	2026-03-03 17:47:45
25	Переустановка ОС\\ замена жесткого диска	25	2026-03-03 17:47:45
26	Выключается при работе	26	2026-03-03 17:47:45
27	Не заряжается	27	2026-03-03 17:47:45
28	Запала кнопка	28	2026-03-03 17:47:45
29	Не берет бумагу	29	2026-03-03 17:47:45
30	Заказ картриджи	30	2026-03-03 17:47:45
31	Застревает	31	2026-03-03 17:47:45
32	Заказ картриджа	32	2026-03-03 17:47:45
33	Не работает автоподатчик	33	2026-03-03 17:47:45
34	Не работает клавиатура и тачпад (попала вода)	34	2026-03-03 17:47:45
35	Не видит бумагу / зажевывает	35	2026-03-03 17:47:46
36	Изготовление печати	36	2026-03-03 17:47:46
37	Заказ клише	37	2026-03-03 17:47:46
38	Замена конденсатора	38	2026-03-03 17:47:46
39	Замена гнезда	39	2026-03-03 17:47:46
40	Темный экран	40	2026-03-03 17:47:46
41	Замена термопасты	41	2026-03-03 17:47:46
42	Чистка/замена термопасты	42	2026-03-03 17:47:46
43	Переустановка ОС	43	2026-03-03 17:47:46
44	Выключается через несколько листов/ Не включаетс	44	2026-03-03 17:47:46
45	Нет изображения	45	2026-03-03 17:47:46
46	Диагностика\\Не работает сеть	46	2026-03-03 17:47:46
47	Не подключается к Wi-fi + заправка	47	2026-03-03 17:47:46
48	Диагностика системного блока	48	2026-03-03 17:47:46
49	Шумит	49	2026-03-03 17:47:46
50	Ноутбук после залития не включается	50	2026-03-03 17:47:46
51	Уходит в ошибку	51	2026-03-03 17:47:46
52	Сыпется тонер	52	2026-03-03 17:47:46
53	Мажет при печати	53	2026-03-03 17:47:46
54	Выдает ошибку не закрыта крышка	54	2026-03-03 17:47:46
55	Диагностика/ переброс данных моноблока	55	2026-03-03 17:47:46
56	Зависает картинка	56	2026-03-03 17:47:46
57	Перезагрузка при нагрузке	57	2026-03-03 17:47:46
58	Замена термоинтерфейса	58	2026-03-03 17:47:46
59	Не работает подсветка	59	2026-03-03 17:47:46
60	Ошибка фьюзера	60	2026-03-03 17:47:46
61	Не выдаёт изо	61	2026-03-03 17:47:46
62	Включается	62	2026-03-03 17:47:46
63	Но не греет	63	2026-03-03 17:47:46
64	Не запускается	64	2026-03-03 17:47:46
65	Ремонт платы	65	2026-03-03 17:47:46
66	Чистка системного блока	66	2026-03-03 17:47:46
67	После перепада напряжения не работают	67	2026-03-03 17:47:46
68	3 сервера	68	2026-03-03 17:47:46
69	Плохо течет вода (кофе)	69	2026-03-03 17:47:46
70	Не работает часть клавитауры	70	2026-03-03 17:47:46
71	Жует бумагу	71	2026-03-03 17:47:46
72	Диагностика принтера	72	2026-03-03 17:47:46
73	Не корректная работа	73	2026-03-03 17:47:46
74	Нет подсветки	74	2026-03-03 17:47:47
75	Не загружается (возможно попал под дождь)	75	2026-03-03 17:47:47
76	Плохо работает дисковод (не забирает диски)	76	2026-03-03 17:47:47
77	Гарантийный ремонт	77	2026-03-03 17:47:47
78	Заказ\\замена корпуса	78	2026-03-03 17:47:47
79	Не работает буква "Н" иногда нажимается сама	79	2026-03-03 17:47:47
80	Меняли клавиатуру	80	2026-03-03 17:47:47
81	Делали "мост"	81	2026-03-03 17:47:47
82	Хватает на 3 месяца	82	2026-03-03 17:47:47
83	Артефакты на экране после нескольких часов работы	83	2026-03-03 17:47:47
84	Диагностика комплектующих(сборка новых комплектующих)	84	2026-03-03 17:47:47
85	Диагностика материнской платы	85	2026-03-03 17:47:47
86	Залипает клавиша"2"	86	2026-03-03 17:47:47
87	Принтер	87	2026-03-03 17:47:47
88	Перенести комплектующие в новый корпус	88	2026-03-03 17:47:47
89	Грязная печать (гарантийный)	89	2026-03-03 17:47:47
90	Застрял штекер в разъеме зарядки	90	2026-03-03 17:47:47
91	Выливается вода на стол	91	2026-03-03 17:47:47
92	Грязная печать черного картриджа	92	2026-03-03 17:47:47
93	Не захватывает бумагу	93	2026-03-03 17:47:47
94	Диагностика дисковода	94	2026-03-03 17:47:47
95	Заказ штампа	95	2026-03-03 17:47:47
96	Оценка стоимости	96	2026-03-03 17:47:47
97	Плохое качество печати	97	2026-03-03 17:47:47
98	Захватывает лишний лист	98	2026-03-03 17:47:47
99	Переустановка ОС (белый экран)	99	2026-03-03 17:47:48
100	Сам делает. Двойной эспрессо делает сам	100	2026-03-03 17:47:48
101	Не даёт горячую воду	101	2026-03-03 17:47:48
102	Заказ картриджа HP 136A	102	2026-03-03 17:47:48
103	Ошибка картриджа	103	2026-03-03 17:47:48
104	Проверить на вирусы	104	2026-03-03 17:47:48
105	Не открывает PDF	105	2026-03-03 17:47:48
106	Некоторые папки превратились в файлы без разширений	106	2026-03-03 17:47:48
107	Полосы при сканировании	107	2026-03-03 17:47:48
108	Не определяется	108	2026-03-03 17:47:48
109	Тормозит	109	2026-03-03 17:47:48
110	После запаха гари	110	2026-03-03 17:47:48
111	Не видит картридж	111	2026-03-03 17:47:48
112	Заправка картриджа	112	2026-03-03 17:47:48
113	Диагностика разъёма	113	2026-03-03 17:47:48
114	Установка Win 10	114	2026-03-03 17:47:48
115	Установка Ос	115	2026-03-03 17:47:48
116	Диагностика\\Замена разъема питания	116	2026-03-03 17:47:48
117	Застревает бумага на выходе	117	2026-03-03 17:47:48
118	Капучинатор делает пену через раз	118	2026-03-03 17:47:48
119	Не дозирует молоко	119	2026-03-03 17:47:48
120	Полосы при печати	120	2026-03-03 17:47:48
121	Берет бумагу через раз. Замятие в середине	121	2026-03-03 17:47:48
122	Не берет бумагу (потеряна заглушка в лотке)	122	2026-03-03 17:47:48
123	Замятие бумаги	123	2026-03-03 17:47:48
124	Бракует тысячные купюры	124	2026-03-03 17:47:48
125	Не видит чипы	125	2026-03-03 17:47:48
126	Не загружается	126	2026-03-03 17:47:49
127	Синий экран после обновления	127	2026-03-03 17:47:49
128	Диагностика ноутбука	128	2026-03-03 17:47:49
129	Западают левые стики	129	2026-03-03 17:47:49
130	Установка ОС	130	2026-03-03 17:47:49
131	Ремонт	131	2026-03-03 17:47:49
132	Ошибка при работе	132	2026-03-03 17:47:49
133	Отбраковывает купюры	133	2026-03-03 17:47:49
134	Порван валик	134	2026-03-03 17:47:49
135	Диагностика матрицы	135	2026-03-03 17:47:49
136	Ошибка драм картриджа	136	2026-03-03 17:47:49
137	Ошибка диск повреждён	137	2026-03-03 17:47:49
138	5 коротких звуковых сигналов. Нет изображения	138	2026-03-03 17:47:49
139	Горит ошибка восклицательный знак	139	2026-03-03 17:47:49
140	Ошибка 01	140	2026-03-03 17:47:49
141	Не включается\\Не исправно работает\\заедает кнопка включения\\замена батареи	141	2026-03-03 17:47:49
142	Застряла бумага в печке	142	2026-03-03 17:47:49
143	Гудите через ~20 минут работы	143	2026-03-03 17:47:49
144	Лист выходит гармошкой	144	2026-03-03 17:47:49
145	Диагностика батареи	145	2026-03-03 17:47:49
146	Ошибка при работы	146	2026-03-03 17:47:49
147	Заказ клавиатуры	147	2026-03-03 17:47:49
148	Составить акт	148	2026-03-03 17:47:49
149	Потух во время работы (скачок напряжения)	149	2026-03-03 17:47:49
150	Не выходит в готовность	150	2026-03-03 17:47:49
151	Не печатает\\ замена экрана	151	2026-03-03 17:47:49
152	Диагностика (не включается купили на Авито	152	2026-03-03 17:47:49
153	Пробовали менять плату питания	153	2026-03-03 17:47:49
154	Не помогло)	154	2026-03-03 17:47:49
155	Дрифт левого стика	155	2026-03-03 17:47:50
156	Не включается после замены термопасты в другом сервисе	156	2026-03-03 17:47:50
157	Черна полоса слева	157	2026-03-03 17:47:50
158	Левый стик ведет влево	158	2026-03-03 17:47:50
159	Треск кулера	159	2026-03-03 17:47:50
160	Не видит жесткий диск	160	2026-03-03 17:47:50
161	Вырванный разъем	161	2026-03-03 17:47:50
162	Нет звука	162	2026-03-03 17:47:50
163	Серый фон	163	2026-03-03 17:47:50
164	Нет цветной печати	164	2026-03-03 17:47:50
165	Не показывает Изо	165	2026-03-03 17:47:50
166	Восстановление данных	166	2026-03-03 17:47:50
167	Сломался картридж	167	2026-03-03 17:47:50
168	Засыпан тонером	168	2026-03-03 17:47:50
169	Заказ батареи	169	2026-03-03 17:47:50
170	Перестал включаться	170	2026-03-03 17:47:50
171	Диагностика сканера	171	2026-03-03 17:47:50
172	Бледная печать/ cмазывает печать	172	2026-03-03 17:47:50
173	Сброс пароля	173	2026-03-03 17:47:50
174	Печать	174	2026-03-03 17:47:50
175	Не заржается	175	2026-03-03 17:47:50
176	Полоса при печати	176	2026-03-03 17:47:50
177	Складка на бумаге	177	2026-03-03 17:47:50
178	Бледная печать	178	2026-03-03 17:47:50
179	Ремонт часов	179	2026-03-03 17:47:50
180	Обслуживание	180	2026-03-03 17:47:50
181	Замена уплотнителей. Зависает пока не откроешь крышку	181	2026-03-03 17:47:50
182	1. Не видит картридж (перепрошивка)	182	2026-03-03 17:47:50
183	2. не берет бумагу	183	2026-03-03 17:47:50
184	Выходит белый лист	184	2026-03-03 17:47:50
185	Xerox черные полосы по краю	185	2026-03-03 17:47:50
186	Brother не захватывает бумагу	186	2026-03-03 17:47:50
187	Samsung диагностика	187	2026-03-03 17:47:50
188	Заказ штампов	188	2026-03-03 17:47:51
189	Застревает бумага	189	2026-03-03 17:47:51
190	Мало тонера	190	2026-03-03 17:47:51
191	Замените фотобарабан	191	2026-03-03 17:47:51
192	Микрофризы (читать переписку)	192	2026-03-03 17:47:51
193	Прошивка	193	2026-03-03 17:47:51
194	Заправка	194	2026-03-03 17:47:51
195	Артефакты на экране	195	2026-03-03 17:47:51
196	Зависает (часто во время отключения USB)	196	2026-03-03 17:47:51
197	Черные вертикальные полосы и белый экран при нагрузки (перегрев	197	2026-03-03 17:47:51
198	Не крутит кулер)	198	2026-03-03 17:47:51
199	Периодически не работает часть клавиатуры	199	2026-03-03 17:47:51
200	Не печатает по середине листа	200	2026-03-03 17:47:51
201	Проверить сканер	201	2026-03-03 17:47:51
202	Диагностика принетра	202	2026-03-03 17:47:51
203	Не даёт изо	203	2026-03-03 17:47:51
204	Сгорела после перепада напряжения	204	2026-03-03 17:47:51
205	Не работает часть экрана (после падения)	205	2026-03-03 17:47:51
206	Протекает	206	2026-03-03 17:47:51
207	Во время приготовления кофе. Проверить кнопку пара	207	2026-03-03 17:47:51
208	Заправили картридж чернилам	208	2026-03-03 17:47:51
209	Подготовить к работе. Черный экран и синяя полоса при включении. Была подобная проблема. Делали ранее у нас	209	2026-03-03 17:47:51
210	Не запускается диск	210	2026-03-03 17:47:52
211	Не загружается ОС	211	2026-03-03 17:47:52
212	До этого периодически был синий экран	212	2026-03-03 17:47:52
213	Не работают USB порты 3.0	213	2026-03-03 17:47:52
214	Выключается	214	2026-03-03 17:47:52
215	Перегревается ~ через 10 мин	215	2026-03-03 17:47:52
216	Требуется замена термоинтерфейса	216	2026-03-03 17:47:52
217	Печатает с полосой	217	2026-03-03 17:47:52
218	Нет подсветки на видеокарте	218	2026-03-03 17:47:52
219	Нет сигнала на монитор	219	2026-03-03 17:47:52
220	Не включается после удара	220	2026-03-03 17:47:52
221	Заказ фасксимиле	221	2026-03-03 17:47:52
222	Заказ картриджей 2 шт	222	2026-03-03 17:47:52
223	Не видит сигнал с компьтера	223	2026-03-03 17:47:52
224	Не делает кофе	224	2026-03-03 17:47:52
225	Жуёт бумагу	225	2026-03-03 17:47:52
226	Диагностика принтеров	226	2026-03-03 17:47:52
227	Застревает бумага спереди и сзади	227	2026-03-03 17:47:52
228	Заминает бумагу на выходе	228	2026-03-03 17:47:52
229	Заменить комплектующих	229	2026-03-03 17:47:52
230	Задержки мышки при ~ 0-2 часов игры	230	2026-03-03 17:47:52
231	Плохой контакт на выход наушников	231	2026-03-03 17:47:52
232	Не берет бумагу + заправка	232	2026-03-03 17:47:52
233	Ремонт петель	233	2026-03-03 17:47:52
234	Захватывает второй лист	234	2026-03-03 17:47:53
235	Бледно печатает	235	2026-03-03 17:47:53
236	Сломан ролик выхода бумаги	236	2026-03-03 17:47:53
237	Трещит	237	2026-03-03 17:47:53
238	Замена драма	238	2026-03-03 17:47:53
239	Зависает	239	2026-03-03 17:47:53
240	Тормозит во время работы (ОС)	240	2026-03-03 17:47:53
241	Отключается зарядка ~ через 3 минуты	241	2026-03-03 17:47:53
242	Устаановка ОС	242	2026-03-03 17:47:53
243	Установка ОС + драйвера + ПО	243	2026-03-03 17:47:53
244	Установка ОС + программы	244	2026-03-03 17:47:53
245	Нет видеосигнала	245	2026-03-03 17:47:53
246	Короткое замыкание на плате	246	2026-03-03 17:47:53
247	Ошибка видеокарты	247	2026-03-03 17:47:53
248	Не определяется компьютером	248	2026-03-03 17:47:53
249	Чистка ноутбука	249	2026-03-03 17:47:53
331	Клавиатуры	331	2026-03-03 17:47:58
250	Не подключается к компьютеру	250	2026-03-03 17:47:53
251	Требуется замена термопасты	251	2026-03-03 17:47:53
252	Светло печатает после замены первого картриджа за 10 лет возможно вышел из строя блок проявки либо тонер плохой	252	2026-03-03 17:47:53
253	Не намагничивает на магнитный вал	253	2026-03-03 17:47:53
254	Не устанавливается и не запускается часть программ	254	2026-03-03 17:47:54
255	Заказ печати и клише	255	2026-03-03 17:47:54
256	Проверить жесткий диск	256	2026-03-03 17:47:54
257	Сборка ПК	257	2026-03-03 17:47:54
258	Акт дефектовки	258	2026-03-03 17:47:54
259	Не подключается к Wi-Fi	259	2026-03-03 17:47:54
260	Отключается Сеть	260	2026-03-03 17:47:54
261	Полная диагностика	261	2026-03-03 17:47:54
262	Общая сигнализация	262	2026-03-03 17:47:54
263	Не работает клавиатура	263	2026-03-03 17:47:54
264	Не подключается к сетям Wi-Fi	264	2026-03-03 17:47:54
265	Не включается + ремонт кнопки включения	265	2026-03-03 17:47:54
266	Ремонт флэшки	266	2026-03-03 17:47:54
267	Перепаивали кондецаторы	267	2026-03-03 17:47:54
268	Включается и не начинает работу	268	2026-03-03 17:47:54
269	Ошибка сканера	269	2026-03-03 17:47:54
270	Не запекает печка	270	2026-03-03 17:47:54
271	Греется	271	2026-03-03 17:47:55
272	Чистка и замена термопасты	272	2026-03-03 17:47:55
273	Залитие сладким чаем	273	2026-03-03 17:47:55
274	Не включается после замены термопасты	274	2026-03-03 17:47:55
275	Погнуты ножки	275	2026-03-03 17:47:55
276	Замена клавиатуры	276	2026-03-03 17:47:55
277	Проверить микрофон	277	2026-03-03 17:47:55
278	Принтер чеков	278	2026-03-03 17:47:55
279	Чистку с заменой термопасты + добвить оперативную память	279	2026-03-03 17:47:55
280	Горит белый индикатор CPU	280	2026-03-03 17:47:55
281	Системный блок не запускается	281	2026-03-03 17:47:55
282	Не видит сеть	282	2026-03-03 17:47:55
283	Нет Изображения на мониторе	283	2026-03-03 17:47:55
284	Диагностика разьема зарядки	284	2026-03-03 17:47:55
285	Переустановка Ос	285	2026-03-03 17:47:55
286	Переустановка	286	2026-03-03 17:47:55
287	Чистка и замена термопасты видеокарты	287	2026-03-03 17:47:55
288	Залитие	288	2026-03-03 17:47:56
289	Долгое нахождение в воде	289	2026-03-03 17:47:56
290	Диагностика Веб камеры	290	2026-03-03 17:47:56
291	Заказ драм картриджей	291	2026-03-03 17:47:56
292	Порвана термопленка	292	2026-03-03 17:47:56
293	Заказ факсимиле	293	2026-03-03 17:47:56
294	Установка ОС на новый ноутбук	294	2026-03-03 17:47:56
295	Установка виндовс	295	2026-03-03 17:47:56
296	Мажет желтым цветом	296	2026-03-03 17:47:56
297	Замена правого стика	297	2026-03-03 17:47:56
298	Печати	298	2026-03-03 17:47:56
299	Полосил при включении	299	2026-03-03 17:47:56
300	Потом перестал включаться	300	2026-03-03 17:47:56
301	Поженить принтер с ноутбуком	301	2026-03-03 17:47:56
302	Потух во время работы	302	2026-03-03 17:47:56
303	Заказ драм-картриджа	303	2026-03-03 17:47:56
304	Застрял диск	304	2026-03-03 17:47:56
305	Разбита матриц	305	2026-03-03 17:47:56
306	Зажовывает бумагу со лотков	306	2026-03-03 17:47:56
307	Не заражается	307	2026-03-03 17:47:56
308	Не работает ксерокс	308	2026-03-03 17:47:56
309	Треснуло стекло сканера	309	2026-03-03 17:47:57
310	Жует бумагу на входе	310	2026-03-03 17:47:57
311	Не печатает с новым картриджем	311	2026-03-03 17:47:57
312	Сброс до заводских	312	2026-03-03 17:47:57
313	Полосит	313	2026-03-03 17:47:57
314	Запускается	314	2026-03-03 17:47:57
315	Но без изображения	315	2026-03-03 17:47:57
316	Полосы на экране	316	2026-03-03 17:47:57
317	Искрит вилка	317	2026-03-03 17:47:57
318	Ошибка E0	318	2026-03-03 17:47:57
319	Плохо работает клавиатура. Отошла задняя крышка	319	2026-03-03 17:47:57
320	Нет подключения к сетям (после установки и удаления ВПН)	320	2026-03-03 17:47:57
321	Печатает черные полосы с двух сторон	321	2026-03-03 17:47:57
322	Жуёт бумагу на выходе	322	2026-03-03 17:47:57
323	Ошибка фотобарабана	323	2026-03-03 17:47:57
324	Не включатся	324	2026-03-03 17:47:57
325	Блок питания	325	2026-03-03 17:47:57
326	Петля	326	2026-03-03 17:47:58
327	Рябит экран (попал под дождь)	327	2026-03-03 17:47:58
328	Намотало бумагу в печку	328	2026-03-03 17:47:58
329	Сломаны драм картриджи и узел очистки ленты переноса	329	2026-03-03 17:47:58
330	Не включается. Запала кнопка включения	330	2026-03-03 17:47:58
745	Жует	745	2026-03-03 17:48:25
332	Застрял диск + банковская карта	332	2026-03-03 17:47:58
333	Застряла бумага	333	2026-03-03 17:47:58
334	Забыли пароль Windows	334	2026-03-03 17:47:58
335	Не держит АКБ	335	2026-03-03 17:47:58
336	Бьет током на корпус	336	2026-03-03 17:47:58
337	Не держит аккумулятор (работает только от сети)	337	2026-03-03 17:47:58
338	Не включается (тухнет индикатор зарядки в момент подключения к ноутбуку)	338	2026-03-03 17:47:58
339	Чистка принтера	339	2026-03-03 17:47:58
340	Замятие бумаги в печке	340	2026-03-03 17:47:58
341	Залитие жидкость	341	2026-03-03 17:47:58
342	Зажевывает бумагу	342	2026-03-03 17:47:58
343	Не делает кофе. Ошибка	343	2026-03-03 17:47:58
344	Не крутит двигатель (проверить плату)	344	2026-03-03 17:47:58
345	Не держит аккумулятор	345	2026-03-03 17:47:58
346	Тихий звук	346	2026-03-03 17:47:58
347	Синий экран (переустановка с сохранением данных. папку "Проект" перенести на диск D)	347	2026-03-03 17:47:59
348	Установить ВПН	348	2026-03-03 17:47:59
349	Не работает кнопка Backspase (замена клавиатуры)	349	2026-03-03 17:47:59
350	Залипание левых стиков	350	2026-03-03 17:47:59
351	Распечатка текста	351	2026-03-03 17:47:59
352	Долгая загрузка	352	2026-03-03 17:47:59
353	Быстро разряжается	353	2026-03-03 17:47:59
354	Прошивка принтера	354	2026-03-03 17:47:59
355	Заказать зарядку	355	2026-03-03 17:47:59
356	Аккумулятор и проверить и установить ОС	356	2026-03-03 17:47:59
357	Ремонт петли и гнезда зарядки	357	2026-03-03 17:47:59
358	Установка Oc	358	2026-03-03 17:47:59
359	Поменять микросхемы на плате	359	2026-03-03 17:47:59
360	Артефакты на экране при нажатии	360	2026-03-03 17:47:59
361	Треск при включении	361	2026-03-03 17:47:59
362	Читка от пыли	362	2026-03-03 17:47:59
363	Замена термопасты на процессоре и видеокарте	363	2026-03-03 17:47:59
364	Прошивка Bios	364	2026-03-03 17:47:59
365	Отключение UEFI	365	2026-03-03 17:47:59
366	Снятие блокировки	366	2026-03-03 17:47:59
367	Треск	367	2026-03-03 17:47:59
368	Намотало бумагу	368	2026-03-03 17:47:59
369	Чистка от накипи	369	2026-03-03 17:47:59
370	Заправка картриджей АБС Трэвэл	370	2026-03-03 17:48:00
371	Замена тканевой накладки	371	2026-03-03 17:48:00
372	Не включается после скачка напряжения	372	2026-03-03 17:48:00
373	Чистка + замена термопасты	373	2026-03-03 17:48:00
374	Ошибка поддона	374	2026-03-03 17:48:00
375	Ошибка	375	2026-03-03 17:48:00
376	Заказ картриджи и фотобарабана	376	2026-03-03 17:48:00
377	Сброс пароля Windows	377	2026-03-03 17:48:00
378	Проверить клавиатуру	378	2026-03-03 17:48:00
379	Переустановка ОС Win10 (без сохранения данных)	379	2026-03-03 17:48:00
380	Синий экран	380	2026-03-03 17:48:00
381	Замена тефлонового вала	381	2026-03-03 17:48:00
382	Точки при печати (чистка)	382	2026-03-03 17:48:00
383	Не включается с двумя модулями памяти. Проверить сокет	383	2026-03-03 17:48:00
384	Тормозит переустановка ОС с программами	384	2026-03-03 17:48:01
385	Убрать энергосберегающий режим	385	2026-03-03 17:48:01
386	Подключить принтер к ноутбуку	386	2026-03-03 17:48:01
387	Включается через раз (с зарядкой не включается)	387	2026-03-03 17:48:01
388	Не включается (диагностика)	388	2026-03-03 17:48:01
389	Залили водой	389	2026-03-03 17:48:01
390	Мнёт бумагу	390	2026-03-03 17:48:01
391	Вирусы	391	2026-03-03 17:48:01
392	Установка Офис	392	2026-03-03 17:48:01
393	Не работают USB с правой стороны	393	2026-03-03 17:48:01
394	Нет доступных сетей	394	2026-03-03 17:48:01
395	Не подает воду	395	2026-03-03 17:48:01
396	Уже чистили в октябре сейчас снова такая же проблема	396	2026-03-03 17:48:01
397	Не видит диск	397	2026-03-03 17:48:01
398	Вылетают игры на рабочий стол (~5-10 минут)	398	2026-03-03 17:48:01
399	Не загружается после отключения света	399	2026-03-03 17:48:02
400	Розовые полосы на экране	400	2026-03-03 17:48:02
401	Не подключается к сети WIFI	401	2026-03-03 17:48:02
402	Три сигнала при включении	402	2026-03-03 17:48:02
403	Добавить оперативку	403	2026-03-03 17:48:02
404	Заклинил заварочный блок	404	2026-03-03 17:48:02
405	Переустановка + драйвера + активация	405	2026-03-03 17:48:02
406	Принетр	406	2026-03-03 17:48:02
407	Отходит экран	407	2026-03-03 17:48:02
408	Петли	408	2026-03-03 17:48:02
409	Не работает кнопа "Время"	409	2026-03-03 17:48:02
410	Включается не с первого раза	410	2026-03-03 17:48:02
411	Декальцинация	411	2026-03-03 17:48:02
412	Мерцает экран	412	2026-03-03 17:48:02
413	Диагностика iMac	413	2026-03-03 17:48:02
414	Залит сладкой жидкостью	414	2026-03-03 17:48:02
415	Выключается при игре на дисках от PS5	415	2026-03-03 17:48:02
416	Зажевывает лист	416	2026-03-03 17:48:02
417	Черна полоса снизу	417	2026-03-03 17:48:02
418	Выключается через 5-10 мин. работы	418	2026-03-03 17:48:02
419	Черный экране	419	2026-03-03 17:48:03
420	Заказ печаи	420	2026-03-03 17:48:03
421	Зажевывает бумагу на входе	421	2026-03-03 17:48:03
422	Заказ картриджей	422	2026-03-03 17:48:03
423	Пропал вай-фай	423	2026-03-03 17:48:03
424	Пролили кофе на клавиатуру (слева сверху)	424	2026-03-03 17:48:03
425	Выключается после нагрева	425	2026-03-03 17:48:03
426	Установить Teams	426	2026-03-03 17:48:03
427	Перепрошивка принтера	427	2026-03-03 17:48:03
428	Ремонт креплений + возможна замена матрицы	428	2026-03-03 17:48:03
429	Задваивает изображение (проверить фотобарабан)	429	2026-03-03 17:48:03
430	Не читает диски	430	2026-03-03 17:48:03
431	Залит жидкостью Не включается	431	2026-03-03 17:48:03
432	Ремонт петель и крышки	432	2026-03-03 17:48:04
433	-	433	2026-03-03 17:48:04
434	Диагностика картриджа	434	2026-03-03 17:48:04
435	Установка win 11	435	2026-03-03 17:48:04
436	Программы для фото-видео	436	2026-03-03 17:48:04
437	Телеграмм	437	2026-03-03 17:48:04
438	Вк	438	2026-03-03 17:48:04
439	Не берет бумагу с автоподатчика сканера	439	2026-03-03 17:48:04
440	Выключается при открытии любой программы	440	2026-03-03 17:48:04
441	Заказ Штампа	441	2026-03-03 17:48:04
442	Не печатает	442	2026-03-03 17:48:04
443	Не держит заряд	443	2026-03-03 17:48:04
444	Собрать из двух один	444	2026-03-03 17:48:04
445	Замена панели	445	2026-03-03 17:48:04
446	Замена матрицы	446	2026-03-03 17:48:04
447	Плохая печать	447	2026-03-03 17:48:04
448	Не сканирует с пк	448	2026-03-03 17:48:04
449	Диагностика разьема	449	2026-03-03 17:48:04
450	Диагностика зарядки	450	2026-03-03 17:48:04
451	Замена драм-картриджа	451	2026-03-03 17:48:04
452	Диагностика разъёма питания	452	2026-03-03 17:48:04
453	Ремонт разъема питания	453	2026-03-03 17:48:04
454	Белые полосы при печати	454	2026-03-03 17:48:05
455	Разъем зарядки	455	2026-03-03 17:48:05
456	Проверка и замена hdd	456	2026-03-03 17:48:05
457	Переустановка системы	457	2026-03-03 17:48:05
458	Печатает черный лист	458	2026-03-03 17:48:05
459	Не работает кулер новый или чистка	459	2026-03-03 17:48:05
460	Требуется чистка	460	2026-03-03 17:48:05
461	+ оперативка добавить	461	2026-03-03 17:48:05
462	+ посмотреть экран	462	2026-03-03 17:48:05
463	Не включается ноутбук	463	2026-03-03 17:48:05
464	Медленно работает	464	2026-03-03 17:48:05
465	(доп. замена аккумулятора)	465	2026-03-03 17:48:05
466	Полоса при сканировании	466	2026-03-03 17:48:05
467	Ремонт принтера + заправка картриджа	467	2026-03-03 17:48:05
468	Выключилась во врем работы	468	2026-03-03 17:48:05
469	Ошибки	469	2026-03-03 17:48:05
470	Бесконечная инициализация	470	2026-03-03 17:48:05
471	Не работает тач	471	2026-03-03 17:48:05
472	Проверить температуру	472	2026-03-03 17:48:05
473	Громкость в приложениях	473	2026-03-03 17:48:05
474	Активация Win	474	2026-03-03 17:48:05
475	Не работают джойстики после ремонта HDMI	475	2026-03-03 17:48:05
476	Синий экран при работе (при подключении принтера)	476	2026-03-03 17:48:05
477	Не хватает места	477	2026-03-03 17:48:05
478	Звук и микрофон	478	2026-03-03 17:48:05
479	Зажевывет бумагу	479	2026-03-03 17:48:05
480	Проблемы с подачей бумаги	480	2026-03-03 17:48:05
481	Скачек напряжения	481	2026-03-03 17:48:05
482	Перенос данных с 2-х HDD на внешний HDD	482	2026-03-03 17:48:06
483	Не загружаетс	483	2026-03-03 17:48:06
484	Диагностика Ps5 нет изображения	484	2026-03-03 17:48:06
485	Гудит вентилятор (возможно скачок напряжения)	485	2026-03-03 17:48:06
486	Полоса при печати и сканировании	486	2026-03-03 17:48:06
487	Пролили кофе (мат. плата)	487	2026-03-03 17:48:06
488	Выливает воду в поддон (проверить поршень)	488	2026-03-03 17:48:06
489	Скрежет при печати	489	2026-03-03 17:48:06
490	Плавится разъем зарядки	490	2026-03-03 17:48:06
491	Протекает вода на стол (после транспортировки)	491	2026-03-03 17:48:06
492	Выключается сразу после включения	492	2026-03-03 17:48:06
493	Не включается мини компьютер	493	2026-03-03 17:48:06
494	Ремонт петли + Апгрейд SSD + RAM	494	2026-03-03 17:48:07
495	Печатает пустой	495	2026-03-03 17:48:07
496	Берет лишние листы	496	2026-03-03 17:48:07
497	Чистка Кофемашины	497	2026-03-03 17:48:07
498	Проблемы с питанием	498	2026-03-03 17:48:07
499	Зажевывает бумагу на выходе	499	2026-03-03 17:48:07
500	После обновления не загружается	500	2026-03-03 17:48:07
501	Пишет "нет кофе"	501	2026-03-03 17:48:07
502	Заказ картриджей 2 шт.	502	2026-03-03 17:48:07
503	Печатет пустые листы	503	2026-03-03 17:48:07
504	Ремонт POS принтеров	504	2026-03-03 17:48:07
505	Темный экран при включении	505	2026-03-03 17:48:07
506	Не включается (доп. замена клавиатуры)	506	2026-03-03 17:48:07
507	Не читает blue ray диски	507	2026-03-03 17:48:07
508	Горит красный индикатор	508	2026-03-03 17:48:07
509	Ошибки при работе (буквы на черном экране)	509	2026-03-03 17:48:07
510	Нет изображения (шлейф или матрица)	510	2026-03-03 17:48:07
511	Шумит вентилятор	511	2026-03-03 17:48:07
512	Чистка с заменой термопасты + переустановка ОС	512	2026-03-03 17:48:07
513	Синий экран (диагностика)	513	2026-03-03 17:48:07
514	Замена аккумулятора	514	2026-03-03 17:48:07
515	Грязна печать	515	2026-03-03 17:48:08
516	Пролили кофе	516	2026-03-03 17:48:08
517	Замена дисковода ps4	517	2026-03-03 17:48:08
518	Тормозит (чистка)	518	2026-03-03 17:48:08
519	Тускнеет изображение через ~5 мин. работы	519	2026-03-03 17:48:08
520	Установка программ	520	2026-03-03 17:48:08
521	Белая полоса после заправки картриджа	521	2026-03-03 17:48:08
522	Дефекты при печати	522	2026-03-03 17:48:08
523	Не загружается (диагностика)	523	2026-03-03 17:48:08
524	Белый экран (матрица или шлейф)	524	2026-03-03 17:48:08
525	Найти новый акб	525	2026-03-03 17:48:08
526	Ремонт POS принтера	526	2026-03-03 17:48:08
527	Нет изображения на матрице	527	2026-03-03 17:48:08
528	Ошибка 0	528	2026-03-03 17:48:09
529	Мажет	529	2026-03-03 17:48:09
530	Не печатет с компьютера	530	2026-03-03 17:48:09
531	Ремонт панели	531	2026-03-03 17:48:09
532	Заклинил картридж	532	2026-03-03 17:48:09
533	Застрял штекер	533	2026-03-03 17:48:09
534	Декальценация	534	2026-03-03 17:48:09
535	Ревизия уплотнителей. Замена штуцера	535	2026-03-03 17:48:09
536	Застревает бумага на входе	536	2026-03-03 17:48:09
537	Западает кнопка	537	2026-03-03 17:48:09
538	Не включается после залития водой	538	2026-03-03 17:48:09
539	Дрифтят оба стика	539	2026-03-03 17:48:09
540	Подключение USB	540	2026-03-03 17:48:09
541	Чистка с заменой термопасты + установка ОС (данные не нужны)	541	2026-03-03 17:48:09
542	Не определяет	542	2026-03-03 17:48:09
543	Пишет "Вставьте картридж"	543	2026-03-03 17:48:09
544	Не включается после отключения света	544	2026-03-03 17:48:09
545	Завис	545	2026-03-03 17:48:09
546	Барахлит динамик	546	2026-03-03 17:48:09
547	Плохо работают кнопки R2 и L2	547	2026-03-03 17:48:09
548	Зажевывает бумагу снизу	548	2026-03-03 17:48:09
549	Не видит уровень воды	549	2026-03-03 17:48:09
550	Ремонт соленоида	550	2026-03-03 17:48:09
551	Выливает воду	551	2026-03-03 17:48:09
552	Чистка счетчика	552	2026-03-03 17:48:09
553	Висит поиск по странице в браузере	553	2026-03-03 17:48:10
554	Добавить оперативную память	554	2026-03-03 17:48:10
555	Жесткий диск	555	2026-03-03 17:48:10
556	Печатает с черной полоской	556	2026-03-03 17:48:10
557	Грязная печать (новый картридж?)	557	2026-03-03 17:48:10
558	Слетела система	558	2026-03-03 17:48:10
559	Переустановка с сохранением данных	559	2026-03-03 17:48:10
560	Жует бумагу (сыплется тонер)	560	2026-03-03 17:48:10
561	POS принтер	561	2026-03-03 17:48:10
562	Засыпан молотым кофе	562	2026-03-03 17:48:10
563	Не загружается (при переустановки сохранить фотки)	563	2026-03-03 17:48:10
564	Не мелит кофе	564	2026-03-03 17:48:10
565	Залитие ноутбука	565	2026-03-03 17:48:10
566	Обслуживание чистка	566	2026-03-03 17:48:10
567	Замена трубок в манипуле	567	2026-03-03 17:48:10
568	Ремонт кнопки	568	2026-03-03 17:48:10
569	Обновить систему	569	2026-03-03 17:48:10
570	Установка обновления и драйверов	570	2026-03-03 17:48:10
571	Чистка от пыли	571	2026-03-03 17:48:10
572	Ошибка долейте воды	572	2026-03-03 17:48:11
573	Замена термопленки	573	2026-03-03 17:48:11
574	Пачкает	574	2026-03-03 17:48:11
575	Залитие жидкостью (энергетик)	575	2026-03-03 17:48:11
576	Застревает бумага на входе и на выходе	576	2026-03-03 17:48:11
577	Отключается через 15 мин	577	2026-03-03 17:48:11
578	Ps4 прошивка	578	2026-03-03 17:48:11
579	Ps4	579	2026-03-03 17:48:11
580	Мешает цвета	580	2026-03-03 17:48:11
581	Восстановление жесткого диска	581	2026-03-03 17:48:11
582	Проблема в печке	582	2026-03-03 17:48:12
583	Не запускает систему	583	2026-03-03 17:48:12
584	Левый стик	584	2026-03-03 17:48:12
585	Тянет в лево	585	2026-03-03 17:48:12
586	Нет изо на мониторе	586	2026-03-03 17:48:12
587	Выключается после изменения яркости клавиатуры	587	2026-03-03 17:48:12
588	Сброс счетчиков	588	2026-03-03 17:48:12
589	Отключается изображение	589	2026-03-03 17:48:12
590	Установка системы	590	2026-03-03 17:48:12
591	Диагностика Wi-Fi	591	2026-03-03 17:48:12
592	Внезапное выключение	592	2026-03-03 17:48:12
593	Не работает панель	593	2026-03-03 17:48:12
594	Жует бумагу в печке	594	2026-03-03 17:48:13
595	Диагностика и ремонт системного блока	595	2026-03-03 17:48:13
596	Диагностика( пролистывает страницу вниз) чистка	596	2026-03-03 17:48:13
597	Замена АКБ	597	2026-03-03 17:48:13
598	Синий экран при загрузки	598	2026-03-03 17:48:13
599	Не загружается (переустановка ОС)	599	2026-03-03 17:48:13
600	Заказ печати и заправка	600	2026-03-03 17:48:13
601	Замена крышки ноутбука с петлями	601	2026-03-03 17:48:13
602	Не заряжается после выдергивания шнура	602	2026-03-03 17:48:14
603	Чистка (шумит вентилятор)	603	2026-03-03 17:48:14
604	Дергается правый стик	604	2026-03-03 17:48:14
605	Залитие водой	605	2026-03-03 17:48:14
606	Замятие бумаги в области картриджа	606	2026-03-03 17:48:14
607	Треск при печати	607	2026-03-03 17:48:14
608	Шумит система охлаждения	608	2026-03-03 17:48:14
609	Не подключается WiFi	609	2026-03-03 17:48:14
610	Отключается Wi-Fi	610	2026-03-03 17:48:14
611	Замена жёсткого диска и переустановка системы	611	2026-03-03 17:48:14
612	Не заряжается после смены ОС	612	2026-03-03 17:48:14
613	Заказ картриджп	613	2026-03-03 17:48:14
614	Установка ПО	614	2026-03-03 17:48:14
615	Сборка Пк	615	2026-03-03 17:48:14
616	Чистка геймпада	616	2026-03-03 17:48:14
617	Переустановка ОС с программами	617	2026-03-03 17:48:14
618	Активация Windows	618	2026-03-03 17:48:14
619	Не включается после подключения HDMI кабеля	619	2026-03-03 17:48:14
620	Заправка картриджи	620	2026-03-03 17:48:15
621	Дрифт правого стика	621	2026-03-03 17:48:15
622	Зажевывает бумагу и не тянет	622	2026-03-03 17:48:15
623	Не работает кнопка	623	2026-03-03 17:48:15
624	Диагностика POS-принтера	624	2026-03-03 17:48:15
625	Обслуживание видеокарты	625	2026-03-03 17:48:15
626	Не выдаёт видеосигнал	626	2026-03-03 17:48:16
627	Замятие на входе	627	2026-03-03 17:48:16
628	Не включается после подключения USB-точилки	628	2026-03-03 17:48:16
629	Факсимиле	629	2026-03-03 17:48:16
630	Профилактика	630	2026-03-03 17:48:16
631	Шумит вентилятор (чистка или замена)	631	2026-03-03 17:48:16
632	Замена разъема USB	632	2026-03-03 17:48:16
633	Мало памяти HDD	633	2026-03-03 17:48:16
634	Переставляли ОЗУ	634	2026-03-03 17:48:16
635	ЦП 100%	635	2026-03-03 17:48:16
636	Проблема с печатью	636	2026-03-03 17:48:16
637	Три индикатора	637	2026-03-03 17:48:16
638	Сильный перегрев процессора	638	2026-03-03 17:48:16
639	После замены видеокарты перестал включаться	639	2026-03-03 17:48:16
640	Нет сигнала	640	2026-03-03 17:48:16
641	Не работает принтер	641	2026-03-03 17:48:16
642	Заказ печатей 2 шт.	642	2026-03-03 17:48:16
643	Активация	643	2026-03-03 17:48:16
644	Ремонт петли	644	2026-03-03 17:48:17
645	Замятие	645	2026-03-03 17:48:17
646	Ошибка Error 79	646	2026-03-03 17:48:17
647	Ошибки при печати	647	2026-03-03 17:48:17
648	Изготовление клише	648	2026-03-03 17:48:17
649	Установка ОС на новый SSD диск	649	2026-03-03 17:48:17
650	Залит	650	2026-03-03 17:48:17
651	Чистка игровой консоли	651	2026-03-03 17:48:17
652	Залили газировкой	652	2026-03-03 17:48:17
653	Горят три индикатора	653	2026-03-03 17:48:17
654	Ошибка "Обратитесь в СЦ"	654	2026-03-03 17:48:17
655	Установка драйверов	655	2026-03-03 17:48:17
656	Пачкает при печати	656	2026-03-03 17:48:17
657	Выливает кофе в поддон	657	2026-03-03 17:48:17
658	Отломана направляющая	658	2026-03-03 17:48:17
659	Треск в кофемолке	659	2026-03-03 17:48:17
660	Замена стика	660	2026-03-03 17:48:18
661	Сканирует не до конца	661	2026-03-03 17:48:18
662	Заправка картриджей 11 шт.	662	2026-03-03 17:48:18
663	Заказ копии печати	663	2026-03-03 17:48:18
664	Не пропечатывает пол листа	664	2026-03-03 17:48:18
665	Штампы	665	2026-03-03 17:48:18
666	Не включает	666	2026-03-03 17:48:18
667	Заказ печати врача	667	2026-03-03 17:48:18
668	Заказ печатей 2 шт	668	2026-03-03 17:48:18
669	Грзная печать	669	2026-03-03 17:48:18
670	Печатает белый лист	670	2026-03-03 17:48:18
671	Замена накопителя	671	2026-03-03 17:48:19
672	Установка ОС и ПО	672	2026-03-03 17:48:19
673	Не пропускает бумагу (жует)	673	2026-03-03 17:48:19
674	Brother Застревает бумага	674	2026-03-03 17:48:19
675	Заправка. HP бледная печать	675	2026-03-03 17:48:19
676	Photoshop	676	2026-03-03 17:48:19
677	Скачать драйвера для принтеров HP OfficeJet 7110 и HP DeskJet 1000 Printer J110 series	677	2026-03-03 17:48:19
678	Сыплется картридж	678	2026-03-03 17:48:19
679	Восстановление петель крышки матрицы	679	2026-03-03 17:48:19
680	Скрипит	680	2026-03-03 17:48:19
681	Замена разъёма платы принтера	681	2026-03-03 17:48:19
682	Печатает с полосами	682	2026-03-03 17:48:20
683	Застревает бумага в печке	683	2026-03-03 17:48:20
684	Плохо печатает	684	2026-03-03 17:48:20
685	Не берёт бумагу	685	2026-03-03 17:48:20
686	Диагностика HDD	686	2026-03-03 17:48:20
687	Восстановление петель	687	2026-03-03 17:48:20
688	Не берёт бумагу и не печатает картридж	688	2026-03-03 17:48:21
689	2 печ в *.png	689	2026-03-03 17:48:21
690	Изготовление штампа	690	2026-03-03 17:48:21
691	Заправка картриджа 285A	691	2026-03-03 17:48:21
692	Заправка картриджа Бразер 2275	692	2026-03-03 17:48:21
693	Замятие при двусторонней печати	693	2026-03-03 17:48:21
694	Проблема с печатью. Двоит изображение	694	2026-03-03 17:48:21
695	Замена динамиков	695	2026-03-03 17:48:22
696	Не работает дисковод	696	2026-03-03 17:48:22
697	Не включается системный блок	697	2026-03-03 17:48:22
698	Чистка и покупка новых картриджей	698	2026-03-03 17:48:22
699	Заправка картриджа TN 2375	699	2026-03-03 17:48:22
700	Не ополаскивает после включения	700	2026-03-03 17:48:22
701	Печать треугольная	701	2026-03-03 17:48:22
702	Требуется ремонт печки	702	2026-03-03 17:48:22
703	Не работает после перепада электричества	703	2026-03-03 17:48:22
704	Греется сильно	704	2026-03-03 17:48:22
705	Была чистка весной.	705	2026-03-03 17:48:22
706	Проблема с роликами	706	2026-03-03 17:48:23
707	До этого двоил текст	707	2026-03-03 17:48:23
708	Возможно нужна заправка картриджа.	708	2026-03-03 17:48:23
709	Печать факсимиль	709	2026-03-03 17:48:23
710	Написать заключение	710	2026-03-03 17:48:23
711	Заправка картриджа Пантум 2шт	711	2026-03-03 17:48:23
712	Сгорел транзистор	712	2026-03-03 17:48:23
713	Проверить цепь до видеокарты	713	2026-03-03 17:48:23
714	Ноутбук собрать	714	2026-03-03 17:48:23
715	Залит колой	715	2026-03-03 17:48:23
716	Не включается экран на ноутбуке	716	2026-03-03 17:48:23
717	Припаять провод	717	2026-03-03 17:48:23
718	Ремонт кнопок включения	718	2026-03-03 17:48:23
719	Проверка после предыдущей заправка	719	2026-03-03 17:48:23
720	Долго загружается	720	2026-03-03 17:48:23
721	Заказать аккумулятор	721	2026-03-03 17:48:24
722	Сломалась плата	722	2026-03-03 17:48:24
723	АКБ	723	2026-03-03 17:48:24
724	Диагностика разъема питания	724	2026-03-03 17:48:24
725	Замена диска	725	2026-03-03 17:48:24
726	Проверить работу Wi-Fi	726	2026-03-03 17:48:24
727	Перенастроить	727	2026-03-03 17:48:24
728	Прошить	728	2026-03-03 17:48:24
729	Разболталось гнездо для зарядки	729	2026-03-03 17:48:24
730	Установка программы для 3д моделирования	730	2026-03-03 17:48:24
731	Замена батареи	731	2026-03-03 17:48:24
732	Заправка Картриджа	732	2026-03-03 17:48:24
733	Замена левого 3d аналога	733	2026-03-03 17:48:24
734	Почистить	734	2026-03-03 17:48:24
735	Устранить лишний предмет из блока захвата бумаги	735	2026-03-03 17:48:24
736	Ремонт зарядного устройства	736	2026-03-03 17:48:24
737	Перепрошивка	737	2026-03-03 17:48:24
738	В одном картридже пружинка слетела	738	2026-03-03 17:48:24
739	Нужно поставить на место	739	2026-03-03 17:48:24
740	Запрвка	740	2026-03-03 17:48:24
741	Не включается после залития	741	2026-03-03 17:48:25
742	Замена дисплея	742	2026-03-03 17:48:25
743	Замена кнопки	743	2026-03-03 17:48:25
744	Не печатет принтер	744	2026-03-03 17:48:25
746	Не берет с нижнего лотка	746	2026-03-03 17:48:25
747	Чистка ленты переноса	747	2026-03-03 17:48:25
748	Зажевывает с верхнего лотка	748	2026-03-03 17:48:25
749	Не включается (попала вода)	749	2026-03-03 17:48:25
750	Проблема с системой охлаждения	750	2026-03-03 17:48:25
751	Ремонт провода	751	2026-03-03 17:48:25
752	Замена реле	752	2026-03-03 17:48:25
753	Замена разъема	753	2026-03-03 17:48:25
754	Проблема с разъёмом питания	754	2026-03-03 17:48:25
755	После морской воды	755	2026-03-03 17:48:26
756	Нет картинки	756	2026-03-03 17:48:26
757	Не включается после замыкания	757	2026-03-03 17:48:26
758	Изготовление клише 3 шт	758	2026-03-03 17:48:26
759	Диагшностика	759	2026-03-03 17:48:26
760	Не вставляется заварочный блок	760	2026-03-03 17:48:26
761	Выливается водв вместо кофе	761	2026-03-03 17:48:26
762	Не работает объектив	762	2026-03-03 17:48:26
763	Периодически не работает	763	2026-03-03 17:48:27
764	Замена левого стика	764	2026-03-03 17:48:27
765	Замена клавиатура	765	2026-03-03 17:48:27
766	Не делает капучино + полная чистка год не включали	766	2026-03-03 17:48:27
767	Бывает включается бывает нет мигает индикатор и все	767	2026-03-03 17:48:27
768	Зажевывает	768	2026-03-03 17:48:27
769	Замена плат управления с донора	769	2026-03-03 17:48:27
770	Не работает после воды	770	2026-03-03 17:48:27
771	Замена подсветки	771	2026-03-03 17:48:27
772	Восстановление корпуса после падения	772	2026-03-03 17:48:28
773	Нижней платы с разъемом.	773	2026-03-03 17:48:28
774	Замена ЗЧ	774	2026-03-03 17:48:28
775	Проблемы с загрузкой	775	2026-03-03 17:48:28
776	Пачкает.	776	2026-03-03 17:48:28
777	Завис в режиме очистки	777	2026-03-03 17:48:28
778	Остановка ОС на новый диск + AnyDesk и AmmyAdmin	778	2026-03-03 17:48:28
779	Диагностика после другого "мастера"	779	2026-03-03 17:48:28
780	Ошибка 13	780	2026-03-03 17:48:28
781	Не видит потдон.	781	2026-03-03 17:48:28
782	Перенос данных	782	2026-03-03 17:48:28
783	Не включается после залития.	783	2026-03-03 17:48:28
784	Самопроизвольное отключение	784	2026-03-03 17:48:28
785	Верхний лоток не берёт бумагу	785	2026-03-03 17:48:29
786	Заказ печатей 3 шт.	786	2026-03-03 17:48:29
787	Дрифт стика	787	2026-03-03 17:48:29
788	Оторван провод от кнопки включения	788	2026-03-03 17:48:29
789	Заправка картриджей 16 шт	789	2026-03-03 17:48:29
790	Гудят лин. выходы	790	2026-03-03 17:48:29
791	Замена акб	791	2026-03-03 17:48:29
792	Через ~15 минут работы пропадает изображение.	792	2026-03-03 17:48:29
793	Нет контакта на картридж	793	2026-03-03 17:48:29
794	Намотало файл в печке	794	2026-03-03 17:48:29
795	Замена 3d аналога	795	2026-03-03 17:48:29
796	Подготовить к работе	796	2026-03-03 17:48:29
797	Заказ печати 2 шт	797	2026-03-03 17:48:29
798	Не включается (черный экран)	798	2026-03-03 17:48:29
799	Заказ клише 2 шт	799	2026-03-03 17:48:30
800	Подготовить к работе после долгого неиспользования	800	2026-03-03 17:48:30
801	Чистка (повторно)	801	2026-03-03 17:48:30
802	RT и правый стик-нажатие	802	2026-03-03 17:48:30
803	Собрать после самостоятельной замены АКБ	803	2026-03-03 17:48:30
804	Не берет с лотка	804	2026-03-03 17:48:30
805	Не включается (кнопка)	805	2026-03-03 17:48:30
806	Не молет кофемолка	806	2026-03-03 17:48:30
807	Ремонт объектива	807	2026-03-03 17:48:30
808	Заправка картриджей 2 шт.	808	2026-03-03 17:48:30
809	Замена печки	809	2026-03-03 17:48:30
810	Чистка матрицы	810	2026-03-03 17:48:31
811	Не подает бумагу	811	2026-03-03 17:48:31
812	Перепрошивка BIOS	812	2026-03-03 17:48:31
813	Восстановление дорожет	813	2026-03-03 17:48:31
814	Переустановка О.С.	814	2026-03-03 17:48:31
815	Ремонт микроволновки	815	2026-03-03 17:48:31
816	Не работает wi-fi	816	2026-03-03 17:48:31
817	Заправка картриджей 2шт	817	2026-03-03 17:48:31
818	Не работает bluetooth	818	2026-03-03 17:48:31
819	Застряла бумага на входе в принтер	819	2026-03-03 17:48:31
820	Заправка картриджей (2шт.)	820	2026-03-03 17:48:31
821	Восстановление после залития.	821	2026-03-03 17:48:31
822	Не работает один мотор	822	2026-03-03 17:48:31
823	Не печатает по сети	823	2026-03-03 17:48:31
824	Замена камеры	824	2026-03-03 17:48:31
825	Не берет бумагу с нижнего лотка	825	2026-03-03 17:48:31
826	Берет два листа с автоподатчика	826	2026-03-03 17:48:31
827	Диагностика (замятия бумаги)	827	2026-03-03 17:48:31
828	Зажевывает бумагу в печке	828	2026-03-03 17:48:31
829	Диагностика после падения	829	2026-03-03 17:48:31
830	Грязная печать + полоса	830	2026-03-03 17:48:31
831	После скачка напряжения не работает	831	2026-03-03 17:48:31
832	Не наливает кофе	832	2026-03-03 17:48:31
833	Перегрев	833	2026-03-03 17:48:31
834	Не заряжается АКБ	834	2026-03-03 17:48:32
835	Подготовить к работе. Не прокручивает бумагу (чистка)	835	2026-03-03 17:48:32
836	Не включается.	836	2026-03-03 17:48:32
837	Гудит	837	2026-03-03 17:48:32
838	Застревает бумагу	838	2026-03-03 17:48:32
839	Не раегирует сенсор	839	2026-03-03 17:48:32
840	Замена топ-кейса	840	2026-03-03 17:48:32
841	Крышка матрицы	841	2026-03-03 17:48:32
842	Разъем зу.	842	2026-03-03 17:48:32
843	Черная полоса счерху	843	2026-03-03 17:48:32
844	Нет выхода HDMI	844	2026-03-03 17:48:32
845	Не берет бумагу (повторно)	845	2026-03-03 17:48:32
846	Не включается от БП	846	2026-03-03 17:48:32
847	Не открываются программы	847	2026-03-03 17:48:32
848	Не вствавлятеся заварочный блок	848	2026-03-03 17:48:32
849	Некорректная работа консоли	849	2026-03-03 17:48:32
850	Цокает в левом канале	850	2026-03-03 17:48:32
851	Желты и Красный не печатает	851	2026-03-03 17:48:32
852	Восстановление внешнего накопителя	852	2026-03-03 17:48:32
853	Оплачен	853	2026-03-03 17:48:32
854	Не заргужается	854	2026-03-03 17:48:32
855	Не работает верх	855	2026-03-03 17:48:32
856	Проверка подключения	856	2026-03-03 17:48:33
857	Диагностика подключения	857	2026-03-03 17:48:33
858	После выключения света перестали работать	858	2026-03-03 17:48:33
859	Не заряжается.	859	2026-03-03 17:48:33
860	Почистить от вируса	860	2026-03-03 17:48:33
861	Не работает R2	861	2026-03-03 17:48:33
862	ПО	862	2026-03-03 17:48:33
863	Не работает звук	863	2026-03-03 17:48:33
864	Телевизор не включается	864	2026-03-03 17:48:33
865	Заправить картридж	865	2026-03-03 17:48:33
866	Расшатался разъем	866	2026-03-03 17:48:33
867	Сыпется картридж	867	2026-03-03 17:48:33
868	Не видит SSD	868	2026-03-03 17:48:33
869	Перенос данных с накопителя	869	2026-03-03 17:48:33
870	Зажевывает бумагу в районе печки.	870	2026-03-03 17:48:33
871	Заправить	871	2026-03-03 17:48:33
872	При сканировании жует бумагу	872	2026-03-03 17:48:33
873	При печати жует бумагу	873	2026-03-03 17:48:33
874	Полосит. Диагностика	874	2026-03-03 17:48:33
875	Установка П.О.	875	2026-03-03 17:48:33
876	Заказ	876	2026-03-03 17:48:33
877	Не работает верхний правый бампер (rb)	877	2026-03-03 17:48:33
878	Через 5-10мин.	878	2026-03-03 17:48:33
879	Не включается после сервисного центра "Педант"	879	2026-03-03 17:48:33
880	Настроить браузер.	880	2026-03-03 17:48:33
881	После скачка напряжения не включается	881	2026-03-03 17:48:33
882	Не реагирует на кнопку пуск	882	2026-03-03 17:48:33
883	Так же был треск после первого отключения	883	2026-03-03 17:48:33
884	Не заряжает	884	2026-03-03 17:48:33
885	Не едет	885	2026-03-03 17:48:33
886	Не включаются.	886	2026-03-03 17:48:33
887	Печатает белым	887	2026-03-03 17:48:33
888	Нет подсветки.	888	2026-03-03 17:48:33
889	Сливает промывочную воду в отсек для жмыха	889	2026-03-03 17:48:33
890	Не работает блютус	890	2026-03-03 17:48:33
891	Чёрный экран	891	2026-03-03 17:48:33
892	Ремонт печки	892	2026-03-03 17:48:33
893	Нет инициализации	893	2026-03-03 17:48:33
894	Не выходит диск	894	2026-03-03 17:48:33
895	Ошибка ОС	895	2026-03-03 17:48:33
896	Не работает кофемолка	896	2026-03-03 17:48:33
897	Ремонт слота карты памяти	897	2026-03-03 17:48:33
898	Восстановление корпуса	898	2026-03-03 17:48:33
899	Не нагревает и не держит температуру	899	2026-03-03 17:48:33
900	Замена ОЗУ	900	2026-03-03 17:48:33
901	Установка SSD	901	2026-03-03 17:48:33
902	Периодически не молет	902	2026-03-03 17:48:33
903	Датчик рышки.	903	2026-03-03 17:48:33
904	Перепрошить	904	2026-03-03 17:48:33
905	Периодически глючит сенсор (после перезагрузки все норм)	905	2026-03-03 17:48:33
906	Заказ ролика захвата SCX4200	906	2026-03-03 17:48:33
907	Не включается после воды	907	2026-03-03 17:48:33
908	Диагностика. Проблемы с печкой	908	2026-03-03 17:48:34
909	Не берет бумагу с автоподатчика	909	2026-03-03 17:48:34
910	Чистка замена термопасты	910	2026-03-03 17:48:34
911	Чистка и установка по	911	2026-03-03 17:48:34
912	После замены экрана	912	2026-03-03 17:48:34
913	Не могут войти	913	2026-03-03 17:48:34
914	Включается и выключается	914	2026-03-03 17:48:34
915	Заказ картриджа Brother	915	2026-03-03 17:48:34
916	Не моет	916	2026-03-03 17:48:34
917	Черные полосы	917	2026-03-03 17:48:34
918	Не наливает кофе.	918	2026-03-03 17:48:34
919	Через 40 секенд после включения-выключается	919	2026-03-03 17:48:34
920	Заказ АКБ	920	2026-03-03 17:48:34
921	Застревает второй лист	921	2026-03-03 17:48:34
922	Сборка системного блока	922	2026-03-03 17:48:34
923	Проверить картридж	923	2026-03-03 17:48:34
924	Замена гнезда USB	924	2026-03-03 17:48:34
925	Не дает изображение	925	2026-03-03 17:48:34
926	Грязно печатает	926	2026-03-03 17:48:34
927	Печатает символы	927	2026-03-03 17:48:34
928	Перестановка ОС	928	2026-03-03 17:48:34
929	Не читает новые купюры	929	2026-03-03 17:48:34
930	Бледная печать. Не пропечатывает по краям листа	930	2026-03-03 17:48:34
931	Двоит изображение	931	2026-03-03 17:48:34
932	Застревает лист	932	2026-03-03 17:48:34
933	Замена фотобарабана	933	2026-03-03 17:48:34
934	Ракеля	934	2026-03-03 17:48:34
935	Тонера	935	2026-03-03 17:48:34
936	Пятна подсветки	936	2026-03-03 17:48:34
937	Не ловит каналы.	937	2026-03-03 17:48:34
938	Дисплея	938	2026-03-03 17:48:34
939	Разъема.	939	2026-03-03 17:48:34
940	Диагностика (медленно работает)	940	2026-03-03 17:48:34
941	Диагностика (ошибка)	941	2026-03-03 17:48:35
942	Форматирование ж/д	942	2026-03-03 17:48:35
943	Ремонт наушников	943	2026-03-03 17:48:35
944	Заказ картриджа Canon 725	944	2026-03-03 17:48:35
945	Не вкючается	945	2026-03-03 17:48:35
946	Не работает вход микрофона	946	2026-03-03 17:48:35
947	Заказ картриджа 44A	947	2026-03-03 17:48:35
948	Проблема с дисководом	948	2026-03-03 17:48:35
949	Белые полосы при печати чёрным цветом	949	2026-03-03 17:48:35
950	При попытке самостоятельно установить дополнительную оперативную память замкнули контакты на плате ноутбука	950	2026-03-03 17:48:35
951	Не моет.	951	2026-03-03 17:48:35
952	Самопроизвольное включение	952	2026-03-03 17:48:35
953	Проверить HDMI	953	2026-03-03 17:48:35
954	Замена экрана на айфон 10	954	2026-03-03 17:48:35
955	Плохо работает	955	2026-03-03 17:48:35
956	Повышенное напряжение выхода	956	2026-03-03 17:48:35
957	Жует при копировании	957	2026-03-03 17:48:35
958	Не всегда видит картридж	958	2026-03-03 17:48:35
959	Не всегда определяется ПК	959	2026-03-03 17:48:35
960	Ездит  по кругу	960	2026-03-03 17:48:35
961	Чернит	961	2026-03-03 17:48:35
962	Отключается	962	2026-03-03 17:48:35
963	Ремонт звукоснимателя	963	2026-03-03 17:48:35
964	Прошивка + заправка 2 шт	964	2026-03-03 17:48:35
965	Настройка	965	2026-03-03 17:48:35
966	Драйвер Wi-fi	966	2026-03-03 17:48:35
967	Замена USB	967	2026-03-03 17:48:35
968	Установить ПО	968	2026-03-03 17:48:35
969	Датчик воды	969	2026-03-03 17:48:35
970	Чистка и сервисное обслуживание видеокарты	970	2026-03-03 17:48:35
971	Иногда не работает	971	2026-03-03 17:48:35
972	Мех. неисправность	972	2026-03-03 17:48:35
973	Сообщение "откройте кран"	973	2026-03-03 17:48:35
974	Мигает	974	2026-03-03 17:48:35
975	Не удается завершить обновление ОС	975	2026-03-03 17:48:35
976	Не реагирует на команды	976	2026-03-03 17:48:35
977	Треск в районе печки	977	2026-03-03 17:48:35
978	Работает 16 мин.	978	2026-03-03 17:48:35
979	Не берет бумагу снижнего лотка	979	2026-03-03 17:48:35
980	Полосы	980	2026-03-03 17:48:35
981	Не греет.	981	2026-03-03 17:48:36
982	Ошибка Е1	982	2026-03-03 17:48:36
983	Сломан разъем ЗУ	983	2026-03-03 17:48:36
984	Не включается (белый экран)	984	2026-03-03 17:48:36
985	Перегревается	985	2026-03-03 17:48:36
986	Черный экран	986	2026-03-03 17:48:36
987	Сбились настройки	987	2026-03-03 17:48:36
988	Не печатает с покупным картриджем	988	2026-03-03 17:48:36
989	Самопроизвольное выключение	989	2026-03-03 17:48:36
990	Не держит нагрузку	990	2026-03-03 17:48:36
991	Перезагружается через 5мин.	991	2026-03-03 17:48:36
992	Белый экран Pantum	992	2026-03-03 17:48:36
993	Диагностика HP	993	2026-03-03 17:48:36
994	Не работают джойстики неб провода	994	2026-03-03 17:48:36
995	Не ключается	995	2026-03-03 17:48:36
996	Не заряжаются	996	2026-03-03 17:48:36
997	Заказ и замена дисплея	997	2026-03-03 17:48:36
998	Не работает выход HDMI	998	2026-03-03 17:48:37
999	Вылетает из игр	999	2026-03-03 17:48:37
1000	ОС	1000	2026-03-03 17:48:37
1001	Ошибка 7990	1001	2026-03-03 17:48:37
1002	Выбивает автомат	1002	2026-03-03 17:48:37
1003	Заказ картриджа 106A	1003	2026-03-03 17:48:37
1004	Не переключает на 7кв и сбрасывает нагрузкуку	1004	2026-03-03 17:48:37
1005	Не идет вода	1005	2026-03-03 17:48:37
1006	Замена	1006	2026-03-03 17:48:37
1007	Не работают USB порты	1007	2026-03-03 17:48:37
1008	Не греет левая часть	1008	2026-03-03 17:48:37
1009	Ошибка "Нет воды"	1009	2026-03-03 17:48:37
1010	Выливает воду в дренаж	1010	2026-03-03 17:48:37
1011	Не наливает.	1011	2026-03-03 17:48:37
1012	Половина экрана не работает	1012	2026-03-03 17:48:37
1013	Замена поддона	1013	2026-03-03 17:48:37
1014	Профилактика петель	1014	2026-03-03 17:48:37
1015	Не работает одно колесо	1015	2026-03-03 17:48:37
1016	Сломано антенное гнездо	1016	2026-03-03 17:48:37
1017	Умер SSD	1017	2026-03-03 17:48:37
1018	Не работает основная камера.	1018	2026-03-03 17:48:37
1019	Зависание во время работы	1019	2026-03-03 17:48:37
1020	Нет басов у одной из колонок.	1020	2026-03-03 17:48:38
1021	Пропадает изображение вовремя загрузки	1021	2026-03-03 17:48:38
1022	Забегал сенсор температуры	1022	2026-03-03 17:48:38
1023	Потом выдало ошибку	1023	2026-03-03 17:48:38
1024	Динамик хрипит при басах	1024	2026-03-03 17:48:38
1025	Сыпется картридж.	1025	2026-03-03 17:48:38
1026	Не вкл/ не работает клавиатура.	1026	2026-03-03 17:48:38
1027	Не видит воду	1027	2026-03-03 17:48:38
1028	Не работает.	1028	2026-03-03 17:48:38
1029	Переустановить винду на 7	1029	2026-03-03 17:48:38
1030	Дисковод	1030	2026-03-03 17:48:38
1031	Тачпад	1031	2026-03-03 17:48:38
1032	Полосит не берет бумагу	1032	2026-03-03 17:48:38
1033	Не дует живот и руки.	1033	2026-03-03 17:48:38
1034	Хрипит после падения	1034	2026-03-03 17:48:38
1035	Не горит дисплей	1035	2026-03-03 17:48:38
1036	Не реагирует на кнопки.	1036	2026-03-03 17:48:38
1037	Замена барабана	1037	2026-03-03 17:48:38
1038	Проверить верхний лоток	1038	2026-03-03 17:48:38
1039	Выдает ошибки	1039	2026-03-03 17:48:38
1040	Заменить стик/диагностика.	1040	2026-03-03 17:48:38
1041	Сохранить информацию.	1041	2026-03-03 17:48:38
1042	Установка О.С.	1042	2026-03-03 17:48:38
1043	Программ.	1043	2026-03-03 17:48:38
1044	Ошибка препядствия	1044	2026-03-03 17:48:38
1045	Произвольное отключение	1045	2026-03-03 17:48:38
1046	Запах гари	1046	2026-03-03 17:48:38
1047	Заменить термопленку и прижимной вал	1047	2026-03-03 17:48:38
1048	Выливает кофе поддон	1048	2026-03-03 17:48:38
1049	Перезагружается	1049	2026-03-03 17:48:38
1050	Не подключается wi-fi/	1050	2026-03-03 17:48:38
1051	Заказ картриджа Ricoh	1051	2026-03-03 17:48:38
1052	E5	1052	2026-03-03 17:48:38
1053	Моргает подсветка	1053	2026-03-03 17:48:38
1054	Постоянно берет бумагу	1054	2026-03-03 17:48:39
1055	Бледная печать с одной стороны	1055	2026-03-03 17:48:39
1056	Не работает кнопка спуска.	1056	2026-03-03 17:48:39
1057	Диагностика (после обновления слетели игры)	1057	2026-03-03 17:48:39
1058	Не видит видеокарту	1058	2026-03-03 17:48:39
1059	Не устанавливаются драйвера	1059	2026-03-03 17:48:39
1060	Ездит по кругу	1060	2026-03-03 17:48:39
1061	Застревает бумага при входе	1061	2026-03-03 17:48:39
1062	Выдает ошибку	1062	2026-03-03 17:48:39
1063	Не включили	1063	2026-03-03 17:48:39
1064	Работает 30 сек.	1064	2026-03-03 17:48:39
1065	Моргает всеми индикаторами	1065	2026-03-03 17:48:39
1066	Периодически печатает черный лист	1066	2026-03-03 17:48:39
1067	Треск при работе	1067	2026-03-03 17:48:39
1068	Не холодит верх.	1068	2026-03-03 17:48:39
1069	Не работает камера.	1069	2026-03-03 17:48:39
1070	Картридж	1070	2026-03-03 17:48:39
1071	Самопроизвольное выключение. Диагностика	1071	2026-03-03 17:48:39
1072	Чистка.	1072	2026-03-03 17:48:39
1073	Не держит нагрузку.	1073	2026-03-03 17:48:39
1074	Бумага не заходит в печку	1074	2026-03-03 17:48:39
1075	Не работает табло	1075	2026-03-03 17:48:39
1076	Не печатает. После отключения света	1076	2026-03-03 17:48:39
1077	Ошибка охлаждения	1077	2026-03-03 17:48:39
1078	Хрипит звук.	1078	2026-03-03 17:48:40
1079	Не читает USB.	1079	2026-03-03 17:48:40
1080	Не загружается.	1080	2026-03-03 17:48:40
1081	Не работает охлаждение	1081	2026-03-03 17:48:40
1082	Проверить под нагрузкой.	1082	2026-03-03 17:48:40
1083	Диагностика.	1083	2026-03-03 17:48:40
1084	Провести ТО	1084	2026-03-03 17:48:40
1085	Работает 2 мин	1085	2026-03-03 17:48:40
1086	Ошибка.	1086	2026-03-03 17:48:40
1087	Двоится изо спустя ~30мин.	1087	2026-03-03 17:48:40
1088	Картриджи	1088	2026-03-03 17:48:40
1089	Заменить термо вал	1089	2026-03-03 17:48:40
1090	Не греет	1090	2026-03-03 17:48:40
1091	Замена вентилятора	1091	2026-03-03 17:48:40
1092	Чистка матрицы.	1092	2026-03-03 17:48:40
1093	Деформирует лист	1093	2026-03-03 17:48:40
1094	Нет высоких.	1094	2026-03-03 17:48:40
1095	Не печатает.	1095	2026-03-03 17:48:40
1096	Периодически отключается	1096	2026-03-03 17:48:40
1097	Не работают кнопки.	1097	2026-03-03 17:48:40
1098	Выход 280	1098	2026-03-03 17:48:40
1099	Отключается.	1099	2026-03-03 17:48:40
1100	Не работает вспышка	1100	2026-03-03 17:48:40
1101	Не фокусируется.	1101	2026-03-03 17:48:40
1102	Глючит	1102	2026-03-03 17:48:40
1103	Перезагружается.	1103	2026-03-03 17:48:40
1104	Гряхная печать	1104	2026-03-03 17:48:40
1105	Замятие в печке	1105	2026-03-03 17:48:41
1106	Искрит.	1106	2026-03-03 17:48:41
1107	Полосит.	1107	2026-03-03 17:48:41
1108	Заказ и замена матрицы	1108	2026-03-03 17:48:41
1109	Не видит накопитель	1109	2026-03-03 17:48:41
1110	Шумят вентиляторы на видеокарте.	1110	2026-03-03 17:48:41
1111	Стик заклинивает вверх	1111	2026-03-03 17:48:41
1112	Заказ картриджа HP 106A + PC-211	1112	2026-03-03 17:48:41
1113	Ошибка замятие бумаги	1113	2026-03-03 17:48:41
1114	Пишет вставьте USB	1114	2026-03-03 17:48:41
1115	Проверить сканетр	1115	2026-03-03 17:48:41
1116	Заказ БП	1116	2026-03-03 17:48:41
1117	Грязная печать Kyocera	1117	2026-03-03 17:48:41
1118	Печатает пустой лист	1118	2026-03-03 17:48:41
1119	Зажевывает бумагу.	1119	2026-03-03 17:48:41
1120	Диагностика Pantum	1120	2026-03-03 17:48:41
1121	Не закрывается крышка	1121	2026-03-03 17:48:41
1122	Не работает (ошибка)	1122	2026-03-03 17:48:41
1123	Не включается от АКБ	1123	2026-03-03 17:48:41
1124	После заправки плохо печатает	1124	2026-03-03 17:48:41
1125	Треск в разъеме питания	1125	2026-03-03 17:48:41
1126	Отбраковка	1126	2026-03-03 17:48:41
1127	Не выдвигается лоток для дисков	1127	2026-03-03 17:48:41
1128	Не включается (ошибка)	1128	2026-03-03 17:48:41
1129	Тусклое изображение	1129	2026-03-03 17:48:41
1130	Ошибка 504	1130	2026-03-03 17:48:41
1131	Заказ картриджа + заправка	1131	2026-03-03 17:48:41
1132	Проверить шлейф матрицы.	1132	2026-03-03 17:48:41
1133	Не работает сканер	1133	2026-03-03 17:48:42
1134	Не звряжается	1134	2026-03-03 17:48:42
1135	Замена энкодера.	1135	2026-03-03 17:48:42
1136	Установить MS-Office	1136	2026-03-03 17:48:42
1137	Не открывает *.PDF	1137	2026-03-03 17:48:42
1138	Замена термоинтерфейса.	1138	2026-03-03 17:48:42
1139	Диагностика после залития	1139	2026-03-03 17:48:42
1140	Ошибка "восстановление системы"	1140	2026-03-03 17:48:42
1141	Глючат стики	1141	2026-03-03 17:48:42
1142	Сломана петля	1142	2026-03-03 17:48:42
1143	Не заряжается. + Ускорить работу (ОС)	1143	2026-03-03 17:48:42
1144	Не работает сенсор	1144	2026-03-03 17:48:42
1145	Не видит сеть.	1145	2026-03-03 17:48:42
1146	Завсисает при включении	1146	2026-03-03 17:48:42
1147	Зажевывает купюры	1147	2026-03-03 17:48:42
1148	Ошибка 142	1148	2026-03-03 17:48:42
1149	Западает буква "Н"	1149	2026-03-03 17:48:42
1150	Аренда принтера до 31.08	1150	2026-03-03 17:48:42
1151	Не работает капучинатор	1151	2026-03-03 17:48:42
1152	Проверить фильтр	1152	2026-03-03 17:48:42
1153	Не включается (задымилась)	1153	2026-03-03 17:48:42
1154	Не заряжается (раньше заряжался при закрытой крышке)	1154	2026-03-03 17:48:42
1155	Хрипит динамик.	1155	2026-03-03 17:48:42
1156	Ремонт сканера	1156	2026-03-03 17:48:42
1157	Зависает через 5 мин. работы.	1157	2026-03-03 17:48:42
1158	Утонул в море.	1158	2026-03-03 17:48:42
1159	Залипание левого стика	1159	2026-03-03 17:48:42
1160	Жует бумагу на выходе	1160	2026-03-03 17:48:42
1161	Ремонт геймпада	1161	2026-03-03 17:48:42
1162	Не греют	1162	2026-03-03 17:48:42
1163	Не закрывается крышка АКБ	1163	2026-03-03 17:48:42
1164	Дергается изображение	1164	2026-03-03 17:48:42
1165	Периодически выключается.	1165	2026-03-03 17:48:42
1166	Трещит вентилятор	1166	2026-03-03 17:48:42
1167	Фонит	1167	2026-03-03 17:48:43
1168	Пахло гарью	1168	2026-03-03 17:48:43
1169	Черные полосы при печати	1169	2026-03-03 17:48:43
1170	Не берет бумагу после залития (проверить сканер)	1170	2026-03-03 17:48:43
1171	Протекает.	1171	2026-03-03 17:48:43
1172	Застревает на выходе	1172	2026-03-03 17:48:43
1173	Пачкает картридж	1173	2026-03-03 17:48:43
1174	Tefal не выходит в готовность	1174	2026-03-03 17:48:43
1175	Polaris не дает пар	1175	2026-03-03 17:48:43
1176	Дефект при сканировании	1176	2026-03-03 17:48:43
1177	Захватывает несколько листов после 5-10-го листа	1177	2026-03-03 17:48:43
1178	Не включается после "хлопка"	1178	2026-03-03 17:48:43
1179	Накопителя	1179	2026-03-03 17:48:43
1180	Задней крышки.	1180	2026-03-03 17:48:43
1181	Ошибка правого колеса.	1181	2026-03-03 17:48:43
1182	Не видит зарядку	1182	2026-03-03 17:48:43
1183	Заказ картриджа  TN-2375 для Brother	1183	2026-03-03 17:48:43
1184	Черная полоса	1184	2026-03-03 17:48:43
1185	Жует бумагу + заправка	1185	2026-03-03 17:48:43
1186	Замена термопасты.	1186	2026-03-03 17:48:43
1187	Нет изображения.	1187	2026-03-03 17:48:43
1188	Гудит фен	1188	2026-03-03 17:48:43
1189	Излом провода плойка	1189	2026-03-03 17:48:43
1190	Чистка дезинфекция	1190	2026-03-03 17:48:43
1191	Восстановление петель ноутбука	1191	2026-03-03 17:48:43
1192	ОЗУ	1192	2026-03-03 17:48:43
1193	Не аключается.	1193	2026-03-03 17:48:43
1194	Не берет бумагу.	1194	2026-03-03 17:48:43
1195	Горит ошибка.	1195	2026-03-03 17:48:43
1196	Декальцинация + перепутаны чашки	1196	2026-03-03 17:48:43
1197	Выключатеся через 10-15 сек	1197	2026-03-03 17:48:43
1198	Ошибка сканера 13	1198	2026-03-03 17:48:43
1199	Замена платы питаня	1199	2026-03-03 17:48:44
1200	Ошибки при работе	1200	2026-03-03 17:48:44
1201	Треск во время работы	1201	2026-03-03 17:48:44
1202	Щелчки при захвате бумаги	1202	2026-03-03 17:48:44
1203	Выдает ошибку при запуске игр.	1203	2026-03-03 17:48:44
1204	Самопроизвольное мерцание экрана	1204	2026-03-03 17:48:44
1205	Аренда принтера на 4 дня	1205	2026-03-03 17:48:44
1206	Смазанная печать	1206	2026-03-03 17:48:44
1207	Пищит.	1207	2026-03-03 17:48:44
1208	Переустановка ОС с переносом данных	1208	2026-03-03 17:48:44
1209	Выходы тюльпанов	1209	2026-03-03 17:48:44
1210	Выход питания	1210	2026-03-03 17:48:44
1211	Регуляторы	1211	2026-03-03 17:48:44
1212	Установка MS Office	1212	2026-03-03 17:48:44
1213	Фиолетовый цвет экрана	1213	2026-03-03 17:48:44
1214	Плохо передает цвета	1214	2026-03-03 17:48:44
1215	Пластелин в разъеме зарядки	1215	2026-03-03 17:48:44
1216	Не загружается ОС.	1216	2026-03-03 17:48:44
1217	Ошибка гидросистемы	1217	2026-03-03 17:48:44
1218	Не включается (замена клавиатуры)	1218	2026-03-03 17:48:44
1219	Не подает вода	1219	2026-03-03 17:48:44
1220	Не загружает ОС	1220	2026-03-03 17:48:44
1221	Заказ картриджа CF218	1221	2026-03-03 17:48:44
1222	Дефекты изображения	1222	2026-03-03 17:48:44
1223	Заказ картриджа HP44A	1223	2026-03-03 17:48:44
1224	Заказ картриджа EP-27	1224	2026-03-03 17:48:44
1225	Аренда принтера на 7 дней	1225	2026-03-03 17:48:44
1226	Замена предохранителя	1226	2026-03-03 17:48:45
1227	Заказ чернил	1227	2026-03-03 17:48:45
1228	MS Office	1228	2026-03-03 17:48:45
1229	Антивирусное ПО	1229	2026-03-03 17:48:45
1230	Corel Draw	1230	2026-03-03 17:48:45
1231	Adobe DC	1231	2026-03-03 17:48:45
1232	Не крутит	1232	2026-03-03 17:48:45
1233	Зависает изображение	1233	2026-03-03 17:48:45
1234	Заказ фотобарабана CF259	1234	2026-03-03 17:48:45
1235	Зажевывает второй лист	1235	2026-03-03 17:48:45
1236	Выключается через 10-15мин.	1236	2026-03-03 17:48:45
1237	Не работает гироскоп. (не проходит калибровку)	1237	2026-03-03 17:48:45
1238	Пропайка цепей питания после залития	1238	2026-03-03 17:48:45
1239	Замена вентиляторов СО	1239	2026-03-03 17:48:45
1240	Ошибка при помоле.	1240	2026-03-03 17:48:45
1241	Некорректно работает	1241	2026-03-03 17:48:45
1242	Выключается через 10-15 мин.	1242	2026-03-03 17:48:45
1243	Пищит	1243	2026-03-03 17:48:45
1244	Не реагирует на поворот левого стика джойстика	1244	2026-03-03 17:48:45
1245	Аренда принтера с 21.04 по 21.06	1245	2026-03-03 17:48:45
1246	Сборка сист. блока и установка ОС	1246	2026-03-03 17:48:45
1247	Нет изображения после падения	1247	2026-03-03 17:48:45
1248	Чистка принтера + Изготовление клише	1248	2026-03-03 17:48:45
1249	Зависает задание на печать	1249	2026-03-03 17:48:45
1250	Ошибка фотобарабан	1250	2026-03-03 17:48:45
1251	Ремонт платы бойлера	1251	2026-03-03 17:48:45
1252	Замена лаз. головки	1252	2026-03-03 17:48:45
1253	Не работает регулятор громкости.	1253	2026-03-03 17:48:45
1254	После грозы.	1254	2026-03-03 17:48:45
1255	Отключается при загрузке	1255	2026-03-03 17:48:45
1256	Заказ картриджа HP 285A	1256	2026-03-03 17:48:45
1257	Работает но не греет	1257	2026-03-03 17:48:45
1258	Ремонт разъёма питания	1258	2026-03-03 17:48:45
1259	Не заряжаеться	1259	2026-03-03 17:48:45
1260	Отключается при запуске	1260	2026-03-03 17:48:45
1261	Прошивка + заправка	1261	2026-03-03 17:48:45
1262	Пропадает сеть Wi-Fi	1262	2026-03-03 17:48:45
1263	Не крутятся щетки	1263	2026-03-03 17:48:46
1264	Артефакты изображения ~5мин.	1264	2026-03-03 17:48:46
1265	Выключается при нагрузке	1265	2026-03-03 17:48:46
1266	Быстро разряжаеться	1266	2026-03-03 17:48:46
1267	Заказ печати 45 мм	1267	2026-03-03 17:48:46
1268	Аренда принтера	1268	2026-03-03 17:48:46
1269	Прикипела печка	1269	2026-03-03 17:48:46
1270	Не заряжается (мигает) Возможно попадание воды	1270	2026-03-03 17:48:46
1271	Припаять разъем	1271	2026-03-03 17:48:46
1272	Замена разъема microUSB	1272	2026-03-03 17:48:46
1273	Не читает диски.	1273	2026-03-03 17:48:46
1274	Сломан HDMI	1274	2026-03-03 17:48:46
1275	Периодически не включается	1275	2026-03-03 17:48:46
1276	Не отрывает привод	1276	2026-03-03 17:48:46
1277	Ремонт принтеров	1277	2026-03-03 17:48:46
1278	Замена разъёма	1278	2026-03-03 17:48:46
1279	Диагностика + ремонт	1279	2026-03-03 17:48:46
1280	Ошибка "Взлет невозможен"	1280	2026-03-03 17:48:46
1281	Попал посторонний предмет	1281	2026-03-03 17:48:46
1282	Захватывает два листа	1282	2026-03-03 17:48:46
1283	Прошивка принтера + заправка	1283	2026-03-03 17:48:46
1284	Чистка принтера + заказ нового картриджа (2500 руб.)	1284	2026-03-03 17:48:46
1285	Чистка принтера и заправка	1285	2026-03-03 17:48:46
1286	Чистка замена ТП	1286	2026-03-03 17:48:46
1287	Работает 3 минуты и отключается	1287	2026-03-03 17:48:46
1288	Не реагирует на пульт	1288	2026-03-03 17:48:46
1289	Хруст	1289	2026-03-03 17:48:47
1290	Выпала шестерня. Заправить черный картридж	1290	2026-03-03 17:48:47
1291	Не включается (выключается через 1-3 сек)	1291	2026-03-03 17:48:47
1292	Заказ картриджа HP12A	1292	2026-03-03 17:48:47
1293	Отключается блютуз через 30 мин.	1293	2026-03-03 17:48:47
1294	Замена заднего механизма	1294	2026-03-03 17:48:47
1295	Не работает часть клавиатуры	1295	2026-03-03 17:48:47
1296	Нет звука и изображения	1296	2026-03-03 17:48:47
1297	Ремонт петли крышки матрицы	1297	2026-03-03 17:48:47
1298	Отключается во время работы	1298	2026-03-03 17:48:47
1299	Застряла бумага + заправка	1299	2026-03-03 17:48:47
1300	Модернизация	1300	2026-03-03 17:48:47
1301	Не работает (после воды)	1301	2026-03-03 17:48:47
1302	Не стартует ОС	1302	2026-03-03 17:48:47
1303	Нет звука на внутренние динамики	1303	2026-03-03 17:48:47
1304	Просыпает тонер	1304	2026-03-03 17:48:47
1305	Не заряжается. Петля. Перенос данных с доп. диска	1305	2026-03-03 17:48:47
1306	Отсутствует кнопка включения	1306	2026-03-03 17:48:47
1307	Замена аккумулятора и замена разъема питания	1307	2026-03-03 17:48:47
1308	Треск в динамике	1308	2026-03-03 17:48:47
1309	Разблокировка и настройка учётной записи	1309	2026-03-03 17:48:47
1310	Не берет зарядку	1310	2026-03-03 17:48:47
1311	Отходит рамка крышки матрицы	1311	2026-03-03 17:48:47
1312	Заказ картриджа Kyocera TK-5230K	1312	2026-03-03 17:48:47
1313	Ошибка Е4	1313	2026-03-03 17:48:48
1314	Писк во время работы (повторно)	1314	2026-03-03 17:48:48
1315	Не работает экран	1315	2026-03-03 17:48:48
1316	Выше 160 выключается	1316	2026-03-03 17:48:48
1317	Выключается ноутбук после залития чем то сладким	1317	2026-03-03 17:48:48
1318	Прошивка биос запуск системы и насстройка вайфай блютуса	1318	2026-03-03 17:48:48
1319	ЗАПРАВКА КАРТРИДЖА	1319	2026-03-03 17:48:48
1320	Не включаются запах гари	1320	2026-03-03 17:48:48
1321	Выключается ноутбук	1321	2026-03-03 17:48:48
1322	Не работает датчик наличия воды (после чистки от накипи)	1322	2026-03-03 17:48:48
1323	Мигает кнопка	1323	2026-03-03 17:48:48
1324	Не выходит бумага из принтера	1324	2026-03-03 17:48:48
1325	Нагревается	1325	2026-03-03 17:48:48
1326	Поставить office + picture manager	1326	2026-03-03 17:48:48
1327	Писк во время работы	1327	2026-03-03 17:48:48
1328	Выключается во время выпекания	1328	2026-03-03 17:48:48
1329	Не стартует	1329	2026-03-03 17:48:48
1330	Заменить оперативную память	1330	2026-03-03 17:48:48
1331	Нет звука на колонках (диагностика платы)	1331	2026-03-03 17:48:48
1332	Не работает колесико	1332	2026-03-03 17:48:48
1333	Прошивка принтера + заправка картриджа	1333	2026-03-03 17:48:48
1334	Не крутит пластинку	1334	2026-03-03 17:48:48
1335	Не включается BT	1335	2026-03-03 17:48:48
1336	Падает напряжение на плате	1336	2026-03-03 17:48:48
1337	Тормозит (Увеличить ОП)	1337	2026-03-03 17:48:48
1338	Отходит разъем зарядки	1338	2026-03-03 17:48:48
1339	Диагностика. Нет изображения	1339	2026-03-03 17:48:48
1340	Не выключается с кнопки. СОГЛАСОВАТЬ ЦЕНУ РЕМОНТА!	1340	2026-03-03 17:48:48
1341	Не загружается дальше BIOS	1341	2026-03-03 17:48:48
1342	Скачок напряжения	1342	2026-03-03 17:48:48
1343	Не работает автоподатчик (шлейф)	1343	2026-03-03 17:48:48
1344	Застрял картридж	1344	2026-03-03 17:48:48
1345	Диагностика видеокарты (окисление)	1345	2026-03-03 17:48:48
1346	Настройка ПО	1346	2026-03-03 17:48:49
1347	Не читается	1347	2026-03-03 17:48:49
1348	Дымит печка	1348	2026-03-03 17:48:49
1349	Застревает бумага при 2-х сторонней печати	1349	2026-03-03 17:48:49
1350	Не включается после использования металлической посуды	1350	2026-03-03 17:48:49
1351	Не работает датчик наличия воды	1351	2026-03-03 17:48:49
1352	Не берет бумагу из нижнего лотка. Ремонт боковой крышки	1352	2026-03-03 17:48:49
1353	Не определяется по проводу	1353	2026-03-03 17:48:49
1354	Не читает диск (шумин) + джойстик не заряжается	1354	2026-03-03 17:48:49
1355	Попало кофе в левый стик	1355	2026-03-03 17:48:49
1356	Ремонт геймпада PS4	1356	2026-03-03 17:48:49
1357	Не захватывает бумагу  со всех лотков	1357	2026-03-03 17:48:49
1358	Не работает ряд боковых кнопок	1358	2026-03-03 17:48:49
1359	Техобслуживание (двусторонняя печать + захват бумаги)	1359	2026-03-03 17:48:49
1360	Пропадает звук (шатается аудио разъем)	1360	2026-03-03 17:48:49
1361	Перезагружается в течении 15-20 минут	1361	2026-03-03 17:48:49
1362	Сборка + установка ОС	1362	2026-03-03 17:48:49
1363	Отсутствует беспроводная сеть Wi-Fi	1363	2026-03-03 17:48:49
1364	Диагностика принтера + заправка картриджа Q2612A	1364	2026-03-03 17:48:49
1365	Разблокировка учетной записи	1365	2026-03-03 17:48:49
1366	Перепрошивка + заправка	1366	2026-03-03 17:48:49
1367	Отключается при запуске игр	1367	2026-03-03 17:48:49
1368	Замена разъема зарядки	1368	2026-03-03 17:48:49
1369	Не подключается интернет через нижнюю панель	1369	2026-03-03 17:48:49
1370	Заказ картриджа HP 106	1370	2026-03-03 17:48:49
1371	Не включается (Проблема блока питания)	1371	2026-03-03 17:48:49
1372	Приофилактика	1372	2026-03-03 17:48:49
1373	Не печатает с компьютера	1373	2026-03-03 17:48:49
1374	Чистка + профилактика	1374	2026-03-03 17:48:49
1375	Заказ картриджа HP85A	1375	2026-03-03 17:48:49
1376	Клише ИП (пример)	1376	2026-03-03 17:48:50
1377	Обслуживание и диагностика (лампа сканера)	1377	2026-03-03 17:48:50
1378	Диагностика. Печатает желтый лист. Захватывает два листа. Замятия.	1378	2026-03-03 17:48:50
1379	Не включается (клавиатура не работает и не надо). Заменить жесткий диск на SSD. Связаться через мессенджер по согласованию	1379	2026-03-03 17:48:50
1380	Ошибка памяти расходных материалов	1380	2026-03-03 17:48:50
1381	Выливает воду в поддон	1381	2026-03-03 17:48:50
1382	Заказ картриджа TN-2375	1382	2026-03-03 17:48:50
1383	Заправка картриджей (7 шт)	1383	2026-03-03 17:48:50
1384	Ремонт БП	1384	2026-03-03 17:48:50
1385	Изготовление печати ИП	1385	2026-03-03 17:48:50
1386	Не загружается после обновления ОС	1386	2026-03-03 17:48:50
1387	Чистка PS	1387	2026-03-03 17:48:50
1388	Не заряжается джойстик	1388	2026-03-03 17:48:50
1389	Выключается во время загрузки	1389	2026-03-03 17:48:50
1390	Настройка сканирования на ноутбуке	1390	2026-03-03 17:48:50
1391	Мерцание экрана	1391	2026-03-03 17:48:50
1392	Перезагрузка	1392	2026-03-03 17:48:50
1393	Заправка картриджей 12 шт.	1393	2026-03-03 17:48:50
1394	Проблема с разъемом USB (не заряжается)	1394	2026-03-03 17:48:50
1395	Чистка принтера + заправка	1395	2026-03-03 17:48:50
1396	Налипают остатки бумаги	1396	2026-03-03 17:48:50
1397	Ошибка при печати	1397	2026-03-03 17:48:50
1398	Не вращается венитлятор	1398	2026-03-03 17:48:50
1399	Оценка	1399	2026-03-03 17:48:50
1400	Не видит жёсткий диск	1400	2026-03-03 17:48:50
1401	Заказ Драм-картридж 7Q 101R00664 для Xerox B205/B210/B215 (10k) - 2 шт	1401	2026-03-03 17:48:50
1402	Пролили воду (не печатает с компьютера)	1402	2026-03-03 17:48:50
1403	Не работает стик при нажатии вверх	1403	2026-03-03 17:48:50
1404	Собрать	1404	2026-03-03 17:48:50
1405	Жует бумагу (печка)	1405	2026-03-03 17:48:50
1406	Не берет бумагу + диагностика	1406	2026-03-03 17:48:50
1407	Нестабильная работа	1407	2026-03-03 17:48:50
1408	Заправка картриджей 203 - 8 шт.  (+1 брак)	1408	2026-03-03 17:48:50
1409	Не работает дисплей (не переключат сеть)	1409	2026-03-03 17:48:50
1410	505 - 1 шт.	1410	2026-03-03 17:48:50
1411	285 - 5 шт.	1411	2026-03-03 17:48:50
1412	HP12A - 3 шт.	1412	2026-03-03 17:48:50
1413	Ремонт автоподатчика + замена фотобарабана	1413	2026-03-03 17:48:50
1414	Диагностика и ремонт	1414	2026-03-03 17:48:51
1415	Ремонт разъёма клавиатуры	1415	2026-03-03 17:48:51
1416	Сломан вал	1416	2026-03-03 18:55:29
1417	Фоним сабвуфер	1417	2026-03-03 18:55:29
1418	Удаление\\ установка офиса	1418	2026-03-03 18:55:29
1419	Бьёт током	1419	2026-03-03 18:55:29
1420	Чистка и замена кнопки	1420	2026-03-03 18:55:29
1421	Ошибка "Открыта крышка"	1421	2026-03-03 18:55:29
1422	Полностью разрядился и не включается	1422	2026-03-03 18:55:29
1423	Замена двигателя	1423	2026-03-03 18:55:29
1424	Петля плохо закрывается	1424	2026-03-03 18:55:29
1425	Черный лист при печати	1425	2026-03-03 18:55:30
1426	Перезагрузка через время после запуска	1426	2026-03-03 18:55:30
1427	Постоянная перезагрузка	1427	2026-03-03 18:55:30
1428	Заказ печти	1428	2026-03-03 18:55:30
1429	Ошибка Е0	1429	2026-03-03 18:55:30
1430	Замена жидкости охлаждения	1430	2026-03-03 18:55:30
1431	Просит очистить от гущи	1431	2026-03-03 18:55:30
1432	Зависает при работе	1432	2026-03-03 18:55:30
1433	Пропадают USB порты (вместо 12В показывает 2В)	1433	2026-03-03 18:55:30
1434	Работает только от сети	1434	2026-03-03 18:55:30
1435	Восстановить работу моноблока	1435	2026-03-03 18:55:30
1436	Ошибка после обновления (не распознает привод)	1436	2026-03-03 18:55:30
1437	Не устанавливается Windows 10	1437	2026-03-03 18:55:30
1438	Разбита матрица	1438	2026-03-03 18:55:30
1439	После чистки от пыли пропало Изо	1439	2026-03-03 18:55:31
1440	Не работает левый стик	1440	2026-03-03 18:55:31
1441	Установка Windows 10 Pro	1441	2026-03-03 18:55:31
1442	Программы	1442	2026-03-03 18:55:31
1443	Драйвера	1443	2026-03-03 18:55:31
1444	Anydesk (+ Оффис по инструкции от М-Видео)	1444	2026-03-03 18:55:31
1445	Серый фон с рамкой	1445	2026-03-03 18:55:31
1446	Не печатает файл большого объема (pdf более 40Мб)	1446	2026-03-03 18:55:31
1447	Не работает блютуз	1447	2026-03-03 18:55:31
1448	USB и AUX	1448	2026-03-03 18:55:31
1449	Не включается после отключения электричества	1449	2026-03-03 18:55:31
1450	Левый геймпад (диагностика)	1450	2026-03-03 18:55:31
1451	Мерцает	1451	2026-03-04 08:58:36
1452	Выключается после землетрясени	1452	2026-03-04 08:58:36
1453	Темнит и зажевывает бумагу	1453	2026-03-04 10:18:27
1454	Пролили кофе на клавиатуру	1454	2026-03-10 06:56:43
1455	Сбрасывает подключение к сети	1455	2026-03-11 11:44:48
1456	Не работают клавиши на тачпаде	1456	2026-03-11 11:44:48
1457	Не работает Google Crome	1457	2026-03-12 08:00:45
1458	Ошибка при загрузки	1458	2026-03-12 08:05:11
1459	Грязная печать с левой стороны	1459	2026-03-12 10:53:09
1460	Греет	1460	2026-03-13 14:49:05
1461	Но режимы не работают	1461	2026-03-13 14:49:05
1462	Чистка от накипи подтекает	1462	2026-03-14 12:26:17
1463	Не работают задние порты USB (после переезда)	1463	2026-03-16 10:48:13
1464	Чистка декальценация	1464	2026-03-19 08:54:01
1465	Берет бумагу через раз	1465	2026-03-20 14:41:31
1466	Не запускает систему/диагностика	1466	2026-03-21 11:36:42
1467	Чистка от пыли треск при нагрузке	1467	2026-03-23 10:13:18
1468	Выключается во время печати	1468	2026-03-23 11:13:08
1469	Нет минусовой дорожки	1469	2026-03-24 09:12:15
1470	Ошибка 10	1470	2026-03-24 12:21:31
1471	Синий экран с разным кодом ошибки в разный момент времени.	1471	2026-03-24 13:10:09
1472	Чистка и замена термопасты на процессоре и видеокарте	1472	2026-03-24 13:10:09
1473	Заряжается только до 40%	1473	2026-03-24 14:39:18
1474	Звук есть	1474	2026-03-25 11:07:00
1475	Экран потух	1475	2026-03-25 11:07:00
1476	Не сканирует	1476	2026-03-25 13:35:31
1477	Черный лист	1477	2026-03-25 13:35:31
1478	Не всегда захватывает бумагу	1478	2026-03-26 08:33:34
1479	Замена HDMI	1479	2026-03-26 11:43:18
1480	Замена сетевой карты + чистка с заменой термопасты	1480	2026-04-01 08:14:12.287211
1481	Потух и не запускается	1481	2026-04-02 08:04:25.49561
\.


--
-- Data for Name: system_settings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.system_settings (id, key, value, description, updated_at) FROM stdin;
184	payment_method_cash_label	Наличные	Подпись способа оплаты cash	2026-03-03 18:41:36
186	payment_method_transfer_label	Перевод	Подпись способа оплаты transfer	2026-03-03 18:41:36
188	vat_enabled	0	Учитывать НДС в расчете зарплаты (1 = да, 0 = нет)	2026-03-03 18:41:36
189	vat_rate	0.0	Ставка НДС в процентах (по умолчанию 0%)	2026-03-03 18:41:36
194	logo_max_width	400	Максимальная ширина логотипа в печати (px)	2026-03-04 06:49:02
195	logo_max_height	200	Максимальная высота логотипа в печати (px)	2026-03-04 06:49:02
196	print_page_size	A4	Формат печати	2026-03-04 06:49:02
197	print_margin_mm	7	Поля печати (мм)	2026-03-04 06:49:02
187	payment_method_custom_methods	[]	Дополнительные способы оплаты (JSON)	2026-03-03 18:41:36
185	payment_method_card_label		Подпись способа оплаты card	2026-03-03 18:41:36
\.


--
-- Data for Name: task_checklists; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.task_checklists (id, task_id, item_text, is_completed, item_order, created_at) FROM stdin;
\.


--
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tasks (id, order_id, title, description, assigned_to, created_by, deadline, priority, status, created_at, updated_at, completed_at) FROM stdin;
\.


--
-- Data for Name: transaction_categories; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.transaction_categories (id, name, type, description, color, is_system, is_active, sort_order, created_at) FROM stdin;
1	Оплата услуг	income	Оплата за ремонтные работы	#28a745	1	1	1	2025-12-20 07:30:05
2	Продажа товаров	income	Продажа запчастей и аксессуаров	#17a2b8	1	1	2	2025-12-20 07:30:05
3	Предоплата	income	Предоплата от клиента	#ffc107	1	1	3	2025-12-20 07:30:05
5	Закупка товаров	expense	Закупка запчастей и товаров	#dc3545	1	1	5	2025-12-20 07:30:05
6	Зарплата	expense	Выплата заработной платы	#fd7e14	1	1	6	2025-12-20 07:30:05
15	Оплата по заявке	income	Системная категория: Оплата по заявке	#6c757d	1	1	999	2026-01-03 17:38:38
16	Возврат по заявке	expense	Системная категория: Возврат по заявке	#6c757d	1	1	999	2026-01-03 18:33:29
322	Выплата зарплаты	expense	Системная категория: Выплата зарплаты	#6c757d	1	1	999	2026-01-20 15:32:57
334	Выемка наличных директором	expense		#e83e8c	0	1	1000	2026-03-02 18:46:33
335	Уборка	expense	Уборзица	#6610f2	0	1	1001	2026-03-12 08:10:23
336	Внутренний перевод (списание)	expense	Системная категория: Внутренний перевод (списание)	#6c757d	1	1	999	2026-03-12 17:26:45
337	Внутренний перевод (зачисление)	income	Системная категория: Внутренний перевод (зачисление)	#6c757d	1	1	999	2026-03-12 17:26:45
338	Обед	expense	обет	#fd7e14	0	1	1002	2026-03-13 16:13:40
339	Отрисовка печатей	expense		#20c997	0	1	1003	2026-03-19 14:59:12
\.


--
-- Data for Name: user_role_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_role_history (id, user_id, changed_by, changed_by_username, old_role, new_role, old_permission_ids, new_permission_ids, change_type, comment, created_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, username, password_hash, role, created_at, last_login, is_active, display_name) FROM stdin;
8	admin	scrypt:32768:8:1$0VLlWVyDrKeltFa3$ba8291de4d098309b3edc26df32eb133becc54bc3e1ba95a8b04b1a5157399bc60e354128c30de5a65be0e1e944c031407b38890261d8bca29018e09f4cffa04	admin	2026-04-07 20:10:55.11334	\N	1	Demo Admin
9	manager	scrypt:32768:8:1$0VLlWVyDrKeltFa3$ba8291de4d098309b3edc26df32eb133becc54bc3e1ba95a8b04b1a5157399bc60e354128c30de5a65be0e1e944c031407b38890261d8bca29018e09f4cffa04	manager	2026-04-07 20:10:55.11334	\N	1	Demo Manager
10	master	scrypt:32768:8:1$0VLlWVyDrKeltFa3$ba8291de4d098309b3edc26df32eb133becc54bc3e1ba95a8b04b1a5157399bc60e354128c30de5a65be0e1e944c031407b38890261d8bca29018e09f4cffa04	master	2026-04-07 20:10:55.11334	\N	1	Demo Master
11	viewer	scrypt:32768:8:1$0VLlWVyDrKeltFa3$ba8291de4d098309b3edc26df32eb133becc54bc3e1ba95a8b04b1a5157399bc60e354128c30de5a65be0e1e944c031407b38890261d8bca29018e09f4cffa04	viewer	2026-04-07 20:10:55.11334	\N	1	Demo Viewer
\.


--
-- Data for Name: warehouse_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.warehouse_logs (id, operation_type, part_id, part_name, part_number, user_id, username, quantity, old_value, new_value, notes, ip_address, created_at, category_id) FROM stdin;
\.


--
-- Name: action_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.action_logs_id_seq', 1, false);


--
-- Name: appearance_tags_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.appearance_tags_id_seq', 413, true);


--
-- Name: cash_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.cash_transactions_id_seq', 1, false);


--
-- Name: comment_attachments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.comment_attachments_id_seq', 1, false);


--
-- Name: customer_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.customer_tokens_id_seq', 1, false);


--
-- Name: customer_wallet_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.customer_wallet_transactions_id_seq', 1, false);


--
-- Name: customers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.customers_id_seq', 1, false);


--
-- Name: device_brands_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.device_brands_id_seq', 463, true);


--
-- Name: device_types_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.device_types_id_seq', 364, true);


--
-- Name: devices_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.devices_id_seq', 1, false);


--
-- Name: general_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.general_settings_id_seq', 1, true);


--
-- Name: inventory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.inventory_id_seq', 1, false);


--
-- Name: inventory_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.inventory_items_id_seq', 1, false);


--
-- Name: managers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.managers_id_seq', 7, true);


--
-- Name: masters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.masters_id_seq', 5, true);


--
-- Name: notification_preferences_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notification_preferences_id_seq', 1, false);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notifications_id_seq', 1, false);


--
-- Name: order_appearance_tags_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_appearance_tags_id_seq', 1, false);


--
-- Name: order_comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_comments_id_seq', 1, false);


--
-- Name: order_models_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_models_id_seq', 1479, true);


--
-- Name: order_parts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_parts_id_seq', 1, false);


--
-- Name: order_services_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_services_id_seq', 1, false);


--
-- Name: order_status_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_status_history_id_seq', 1, false);


--
-- Name: order_statuses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_statuses_id_seq', 13, true);


--
-- Name: order_symptoms_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_symptoms_id_seq', 1, false);


--
-- Name: order_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_templates_id_seq', 1, false);


--
-- Name: order_visibility_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_visibility_history_id_seq', 1, false);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.orders_id_seq', 1, false);


--
-- Name: part_categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.part_categories_id_seq', 8, true);


--
-- Name: parts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.parts_id_seq', 37, true);


--
-- Name: payment_receipts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.payment_receipts_id_seq', 1, false);


--
-- Name: payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.payments_id_seq', 1, false);


--
-- Name: permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.permissions_id_seq', 20, true);


--
-- Name: print_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.print_templates_id_seq', 1, false);


--
-- Name: purchase_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.purchase_items_id_seq', 1, false);


--
-- Name: purchases_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.purchases_id_seq', 1, false);


--
-- Name: salary_accruals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.salary_accruals_id_seq', 1, false);


--
-- Name: salary_bonuses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.salary_bonuses_id_seq', 1, false);


--
-- Name: salary_fines_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.salary_fines_id_seq', 1, false);


--
-- Name: salary_payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.salary_payments_id_seq', 1, false);


--
-- Name: services_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.services_id_seq', 64, true);


--
-- Name: shop_sale_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shop_sale_items_id_seq', 1, false);


--
-- Name: shop_sales_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shop_sales_id_seq', 1, false);


--
-- Name: staff_chat_attachments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.staff_chat_attachments_id_seq', 1, false);


--
-- Name: staff_chat_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.staff_chat_messages_id_seq', 1, false);


--
-- Name: staff_chat_reactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.staff_chat_reactions_id_seq', 1, false);


--
-- Name: staff_chat_read_cursors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.staff_chat_read_cursors_id_seq', 1, false);


--
-- Name: stock_movements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.stock_movements_id_seq', 1, false);


--
-- Name: suppliers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.suppliers_id_seq', 1, false);


--
-- Name: symptoms_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.symptoms_id_seq', 1481, true);


--
-- Name: system_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.system_settings_id_seq', 197, true);


--
-- Name: task_checklists_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.task_checklists_id_seq', 1, false);


--
-- Name: tasks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tasks_id_seq', 1, false);


--
-- Name: transaction_categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.transaction_categories_id_seq', 339, true);


--
-- Name: user_role_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_role_history_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 11, true);


--
-- Name: warehouse_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.warehouse_logs_id_seq', 1, false);


--
-- Name: action_logs action_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_logs
    ADD CONSTRAINT action_logs_pkey PRIMARY KEY (id);


--
-- Name: appearance_tags appearance_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.appearance_tags
    ADD CONSTRAINT appearance_tags_pkey PRIMARY KEY (id);


--
-- Name: cash_transactions cash_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cash_transactions
    ADD CONSTRAINT cash_transactions_pkey PRIMARY KEY (id);


--
-- Name: comment_attachments comment_attachments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comment_attachments
    ADD CONSTRAINT comment_attachments_pkey PRIMARY KEY (id);


--
-- Name: customer_tokens customer_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_tokens
    ADD CONSTRAINT customer_tokens_pkey PRIMARY KEY (id);


--
-- Name: customer_wallet_transactions customer_wallet_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_wallet_transactions
    ADD CONSTRAINT customer_wallet_transactions_pkey PRIMARY KEY (id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: device_brands device_brands_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_brands
    ADD CONSTRAINT device_brands_pkey PRIMARY KEY (id);


--
-- Name: device_types device_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_types
    ADD CONSTRAINT device_types_pkey PRIMARY KEY (id);


--
-- Name: devices devices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (id);


--
-- Name: general_settings general_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.general_settings
    ADD CONSTRAINT general_settings_pkey PRIMARY KEY (id);


--
-- Name: inventory_items inventory_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_items
    ADD CONSTRAINT inventory_items_pkey PRIMARY KEY (id);


--
-- Name: inventory inventory_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory
    ADD CONSTRAINT inventory_pkey PRIMARY KEY (id);


--
-- Name: managers managers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.managers
    ADD CONSTRAINT managers_pkey PRIMARY KEY (id);


--
-- Name: masters masters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.masters
    ADD CONSTRAINT masters_pkey PRIMARY KEY (id);


--
-- Name: notification_preferences notification_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_preferences
    ADD CONSTRAINT notification_preferences_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: order_appearance_tags order_appearance_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_appearance_tags
    ADD CONSTRAINT order_appearance_tags_pkey PRIMARY KEY (id);


--
-- Name: order_comments order_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_comments
    ADD CONSTRAINT order_comments_pkey PRIMARY KEY (id);


--
-- Name: order_models order_models_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_models
    ADD CONSTRAINT order_models_pkey PRIMARY KEY (id);


--
-- Name: order_parts order_parts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_parts
    ADD CONSTRAINT order_parts_pkey PRIMARY KEY (id);


--
-- Name: order_services order_services_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_services
    ADD CONSTRAINT order_services_pkey PRIMARY KEY (id);


--
-- Name: order_status_history order_status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_status_history
    ADD CONSTRAINT order_status_history_pkey PRIMARY KEY (id);


--
-- Name: order_statuses order_statuses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_statuses
    ADD CONSTRAINT order_statuses_pkey PRIMARY KEY (id);


--
-- Name: order_symptoms order_symptoms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_symptoms
    ADD CONSTRAINT order_symptoms_pkey PRIMARY KEY (id);


--
-- Name: order_templates order_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_templates
    ADD CONSTRAINT order_templates_pkey PRIMARY KEY (id);


--
-- Name: order_visibility_history order_visibility_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_visibility_history
    ADD CONSTRAINT order_visibility_history_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: part_categories part_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.part_categories
    ADD CONSTRAINT part_categories_pkey PRIMARY KEY (id);


--
-- Name: parts parts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parts
    ADD CONSTRAINT parts_pkey PRIMARY KEY (id);


--
-- Name: payment_receipts payment_receipts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_receipts
    ADD CONSTRAINT payment_receipts_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: print_templates print_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.print_templates
    ADD CONSTRAINT print_templates_pkey PRIMARY KEY (id);


--
-- Name: purchase_items purchase_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_items
    ADD CONSTRAINT purchase_items_pkey PRIMARY KEY (id);


--
-- Name: purchases purchases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchases
    ADD CONSTRAINT purchases_pkey PRIMARY KEY (id);


--
-- Name: role_permissions role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (role, permission_id);


--
-- Name: salary_accruals salary_accruals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salary_accruals
    ADD CONSTRAINT salary_accruals_pkey PRIMARY KEY (id);


--
-- Name: salary_bonuses salary_bonuses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salary_bonuses
    ADD CONSTRAINT salary_bonuses_pkey PRIMARY KEY (id);


--
-- Name: salary_fines salary_fines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salary_fines
    ADD CONSTRAINT salary_fines_pkey PRIMARY KEY (id);


--
-- Name: salary_payments salary_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salary_payments
    ADD CONSTRAINT salary_payments_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations_pg schema_migrations_pg_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations_pg
    ADD CONSTRAINT schema_migrations_pg_pkey PRIMARY KEY (version);


--
-- Name: services services_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.services
    ADD CONSTRAINT services_pkey PRIMARY KEY (id);


--
-- Name: shop_sale_items shop_sale_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shop_sale_items
    ADD CONSTRAINT shop_sale_items_pkey PRIMARY KEY (id);


--
-- Name: shop_sales shop_sales_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shop_sales
    ADD CONSTRAINT shop_sales_pkey PRIMARY KEY (id);


--
-- Name: staff_chat_attachments staff_chat_attachments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_attachments
    ADD CONSTRAINT staff_chat_attachments_pkey PRIMARY KEY (id);


--
-- Name: staff_chat_messages staff_chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_messages
    ADD CONSTRAINT staff_chat_messages_pkey PRIMARY KEY (id);


--
-- Name: staff_chat_reactions staff_chat_reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_reactions
    ADD CONSTRAINT staff_chat_reactions_pkey PRIMARY KEY (id);


--
-- Name: staff_chat_read_cursors staff_chat_read_cursors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_read_cursors
    ADD CONSTRAINT staff_chat_read_cursors_pkey PRIMARY KEY (id);


--
-- Name: stock_movements stock_movements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_movements
    ADD CONSTRAINT stock_movements_pkey PRIMARY KEY (id);


--
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (id);


--
-- Name: symptoms symptoms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.symptoms
    ADD CONSTRAINT symptoms_pkey PRIMARY KEY (id);


--
-- Name: system_settings system_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_pkey PRIMARY KEY (id);


--
-- Name: task_checklists task_checklists_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_checklists
    ADD CONSTRAINT task_checklists_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: transaction_categories transaction_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transaction_categories
    ADD CONSTRAINT transaction_categories_pkey PRIMARY KEY (id);


--
-- Name: user_role_history user_role_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role_history
    ADD CONSTRAINT user_role_history_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: warehouse_logs warehouse_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_logs
    ADD CONSTRAINT warehouse_logs_pkey PRIMARY KEY (id);


--
-- Name: action_logs_idx_action_logs_action_type_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX action_logs_idx_action_logs_action_type_pg ON public.action_logs USING btree (action_type);


--
-- Name: action_logs_idx_action_logs_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX action_logs_idx_action_logs_created_at_pg ON public.action_logs USING btree (created_at);


--
-- Name: action_logs_idx_action_logs_created_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX action_logs_idx_action_logs_created_pg ON public.action_logs USING btree (created_at);


--
-- Name: action_logs_idx_action_logs_entity_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX action_logs_idx_action_logs_entity_pg ON public.action_logs USING btree (entity_type, entity_id);


--
-- Name: action_logs_idx_action_logs_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX action_logs_idx_action_logs_user_id_pg ON public.action_logs USING btree (user_id);


--
-- Name: appearance_tags_idx_appearance_tags_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX appearance_tags_idx_appearance_tags_name_pg ON public.appearance_tags USING btree (name);


--
-- Name: appearance_tags_idx_appearance_tags_sort_order_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX appearance_tags_idx_appearance_tags_sort_order_pg ON public.appearance_tags USING btree (sort_order);


--
-- Name: appearance_tags_sqlite_autoindex_appearance_tags_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX appearance_tags_sqlite_autoindex_appearance_tags_1_pg ON public.appearance_tags USING btree (name);


--
-- Name: cash_transactions_idx_cash_transactions_category_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cash_transactions_idx_cash_transactions_category_pg ON public.cash_transactions USING btree (category_id);


--
-- Name: cash_transactions_idx_cash_transactions_date_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cash_transactions_idx_cash_transactions_date_pg ON public.cash_transactions USING btree (transaction_date);


--
-- Name: cash_transactions_idx_cash_transactions_date_type_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cash_transactions_idx_cash_transactions_date_type_pg ON public.cash_transactions USING btree (transaction_date, transaction_type);


--
-- Name: cash_transactions_idx_cash_transactions_not_cancelled_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cash_transactions_idx_cash_transactions_not_cancelled_pg ON public.cash_transactions USING btree (is_cancelled);


--
-- Name: cash_transactions_idx_cash_transactions_order_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cash_transactions_idx_cash_transactions_order_pg ON public.cash_transactions USING btree (order_id);


--
-- Name: cash_transactions_idx_cash_transactions_payment_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cash_transactions_idx_cash_transactions_payment_id_pg ON public.cash_transactions USING btree (payment_id);


--
-- Name: cash_transactions_idx_cash_transactions_shop_sale_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cash_transactions_idx_cash_transactions_shop_sale_id_pg ON public.cash_transactions USING btree (shop_sale_id);


--
-- Name: cash_transactions_idx_cash_transactions_type_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cash_transactions_idx_cash_transactions_type_pg ON public.cash_transactions USING btree (transaction_type);


--
-- Name: comment_attachments_idx_comment_attachments_comment_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX comment_attachments_idx_comment_attachments_comment_id_pg ON public.comment_attachments USING btree (comment_id);


--
-- Name: customer_tokens_idx_customer_tokens_customer_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX customer_tokens_idx_customer_tokens_customer_id_pg ON public.customer_tokens USING btree (customer_id);


--
-- Name: customer_tokens_idx_customer_tokens_expires_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX customer_tokens_idx_customer_tokens_expires_at_pg ON public.customer_tokens USING btree (expires_at);


--
-- Name: customer_tokens_idx_customer_tokens_token_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX customer_tokens_idx_customer_tokens_token_pg ON public.customer_tokens USING btree (token);


--
-- Name: customer_tokens_sqlite_autoindex_customer_tokens_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX customer_tokens_sqlite_autoindex_customer_tokens_1_pg ON public.customer_tokens USING btree (token);


--
-- Name: customer_wallet_transactions_idx_wallet_tx_customer_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX customer_wallet_transactions_idx_wallet_tx_customer_id_pg ON public.customer_wallet_transactions USING btree (customer_id);


--
-- Name: customer_wallet_transactions_idx_wallet_tx_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX customer_wallet_transactions_idx_wallet_tx_order_id_pg ON public.customer_wallet_transactions USING btree (order_id);


--
-- Name: customer_wallet_transactions_idx_wallet_tx_payment_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX customer_wallet_transactions_idx_wallet_tx_payment_id_pg ON public.customer_wallet_transactions USING btree (payment_id);


--
-- Name: customers_idx_customers_email_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX customers_idx_customers_email_pg ON public.customers USING btree (email);


--
-- Name: customers_idx_customers_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX customers_idx_customers_name_pg ON public.customers USING btree (name);


--
-- Name: customers_idx_customers_name_phone_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX customers_idx_customers_name_phone_pg ON public.customers USING btree (name, phone);


--
-- Name: customers_idx_customers_phone_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX customers_idx_customers_phone_pg ON public.customers USING btree (phone);


--
-- Name: customers_sqlite_autoindex_customers_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX customers_sqlite_autoindex_customers_1_pg ON public.customers USING btree (phone);


--
-- Name: device_brands_idx_device_brands_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX device_brands_idx_device_brands_name_pg ON public.device_brands USING btree (name);


--
-- Name: device_brands_idx_device_brands_sort_order_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX device_brands_idx_device_brands_sort_order_pg ON public.device_brands USING btree (sort_order);


--
-- Name: device_brands_sqlite_autoindex_device_brands_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX device_brands_sqlite_autoindex_device_brands_1_pg ON public.device_brands USING btree (name);


--
-- Name: device_types_idx_device_types_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX device_types_idx_device_types_name_pg ON public.device_types USING btree (name);


--
-- Name: device_types_idx_device_types_sort_order_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX device_types_idx_device_types_sort_order_pg ON public.device_types USING btree (sort_order);


--
-- Name: device_types_sqlite_autoindex_device_types_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX device_types_sqlite_autoindex_device_types_1_pg ON public.device_types USING btree (name);


--
-- Name: devices_idx_devices_customer_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX devices_idx_devices_customer_id_pg ON public.devices USING btree (customer_id);


--
-- Name: devices_idx_devices_customer_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX devices_idx_devices_customer_pg ON public.devices USING btree (customer_id);


--
-- Name: devices_idx_devices_device_brand_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX devices_idx_devices_device_brand_id_pg ON public.devices USING btree (device_brand_id);


--
-- Name: devices_idx_devices_device_type_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX devices_idx_devices_device_type_id_pg ON public.devices USING btree (device_type_id);


--
-- Name: devices_idx_devices_serial_number_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX devices_idx_devices_serial_number_pg ON public.devices USING btree (serial_number);


--
-- Name: devices_idx_devices_serial_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX devices_idx_devices_serial_pg ON public.devices USING btree (serial_number);


--
-- Name: idx_cash_txn_date_transaction_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cash_txn_date_transaction_date ON public.cash_transactions USING btree (date(transaction_date));


--
-- Name: idx_cash_txn_date_type_method; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cash_txn_date_type_method ON public.cash_transactions USING btree (transaction_date, transaction_type, payment_method);


--
-- Name: idx_cash_txn_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cash_txn_order_id ON public.cash_transactions USING btree (order_id);


--
-- Name: idx_cash_txn_shop_sale_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cash_txn_shop_sale_id ON public.cash_transactions USING btree (shop_sale_id);


--
-- Name: idx_customers_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customers_created_at ON public.customers USING btree (created_at);


--
-- Name: idx_customers_fts_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customers_fts_search ON public.customers USING gin (to_tsvector('simple'::regconfig, ((((COALESCE(name, ''::text) || ' '::text) || COALESCE(phone, ''::text)) || ' '::text) || COALESCE(email, ''::text))));


--
-- Name: idx_customers_phone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customers_phone ON public.customers USING btree (phone);


--
-- Name: idx_order_parts_date_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_parts_date_created_at ON public.order_parts USING btree (date(created_at));


--
-- Name: idx_order_parts_order_id_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_parts_order_id_created_at ON public.order_parts USING btree (order_id, created_at);


--
-- Name: idx_order_services_date_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_services_date_created_at ON public.order_services USING btree (date(created_at));


--
-- Name: idx_order_services_order_id_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_services_order_id_created_at ON public.order_services USING btree (order_id, created_at);


--
-- Name: idx_order_status_history_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_status_history_created_at ON public.order_status_history USING btree (created_at);


--
-- Name: idx_order_status_history_date_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_status_history_date_created_at ON public.order_status_history USING btree (date(created_at));


--
-- Name: idx_order_status_history_order_status_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_status_history_order_status_time ON public.order_status_history USING btree (order_id, new_status_id, created_at);


--
-- Name: idx_orders_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_created_at ON public.orders USING btree (created_at);


--
-- Name: idx_orders_created_at_visible; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_created_at_visible ON public.orders USING btree (created_at) WHERE ((hidden = 0) OR (hidden IS NULL));


--
-- Name: idx_orders_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_customer_id ON public.orders USING btree (customer_id);


--
-- Name: idx_orders_date_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_date_created_at ON public.orders USING btree (date(created_at));


--
-- Name: idx_orders_date_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_date_updated_at ON public.orders USING btree (date(updated_at));


--
-- Name: idx_orders_fts_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_fts_search ON public.orders USING gin (to_tsvector('simple'::regconfig, ((((((COALESCE(order_id, ''::text) || ' '::text) || COALESCE(comment, ''::text)) || ' '::text) || COALESCE(symptom_tags, ''::text)) || ' '::text) || COALESCE(appearance, ''::text))));


--
-- Name: idx_orders_hidden; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_hidden ON public.orders USING btree (hidden);


--
-- Name: idx_orders_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_status_id ON public.orders USING btree (status_id);


--
-- Name: idx_orders_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_updated_at ON public.orders USING btree (updated_at);


--
-- Name: idx_parts_fts_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parts_fts_search ON public.parts USING gin (to_tsvector('simple'::regconfig, ((((COALESCE(name, ''::text) || ' '::text) || COALESCE(part_number, ''::text)) || ' '::text) || COALESCE(description, ''::text))));


--
-- Name: idx_payments_date_payment_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_date_payment_date ON public.payments USING btree (date(payment_date));


--
-- Name: idx_payments_order_id_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_order_id_date ON public.payments USING btree (order_id, payment_date);


--
-- Name: idx_shop_sales_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shop_sales_created_at ON public.shop_sales USING btree (created_at);


--
-- Name: idx_shop_sales_date_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shop_sales_date_created_at ON public.shop_sales USING btree (date(created_at));


--
-- Name: idx_shop_sales_date_sale_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shop_sales_date_sale_date ON public.shop_sales USING btree (date(sale_date));


--
-- Name: idx_shop_sales_sale_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shop_sales_sale_date ON public.shop_sales USING btree (sale_date);


--
-- Name: idx_staff_chat_attachments_message; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_staff_chat_attachments_message ON public.staff_chat_attachments USING btree (message_id);


--
-- Name: idx_staff_chat_messages_room_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_staff_chat_messages_room_created ON public.staff_chat_messages USING btree (room_key, created_at DESC);


--
-- Name: idx_staff_chat_messages_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_staff_chat_messages_user_created ON public.staff_chat_messages USING btree (user_id, created_at DESC);


--
-- Name: idx_staff_chat_reactions_message; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_staff_chat_reactions_message ON public.staff_chat_reactions USING btree (message_id);


--
-- Name: idx_staff_chat_reactions_message_emoji; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_staff_chat_reactions_message_emoji ON public.staff_chat_reactions USING btree (message_id, emoji);


--
-- Name: idx_stock_movements_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stock_movements_created_at ON public.stock_movements USING btree (created_at);


--
-- Name: idx_stock_movements_date_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stock_movements_date_created_at ON public.stock_movements USING btree (date(created_at));


--
-- Name: idx_transaction_categories_type_sort; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_categories_type_sort ON public.transaction_categories USING btree (type, sort_order);


--
-- Name: inventory_idx_inventory_date_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX inventory_idx_inventory_date_pg ON public.inventory USING btree (inventory_date);


--
-- Name: inventory_idx_inventory_status_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX inventory_idx_inventory_status_pg ON public.inventory USING btree (status);


--
-- Name: inventory_items_idx_inventory_items_inventory_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX inventory_items_idx_inventory_items_inventory_id_pg ON public.inventory_items USING btree (inventory_id);


--
-- Name: inventory_items_idx_inventory_items_part_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX inventory_items_idx_inventory_items_part_id_pg ON public.inventory_items USING btree (part_id);


--
-- Name: managers_idx_managers_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX managers_idx_managers_user_id_pg ON public.managers USING btree (user_id);


--
-- Name: managers_sqlite_autoindex_managers_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX managers_sqlite_autoindex_managers_1_pg ON public.managers USING btree (name);


--
-- Name: masters_idx_masters_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX masters_idx_masters_user_id_pg ON public.masters USING btree (user_id);


--
-- Name: masters_sqlite_autoindex_masters_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX masters_sqlite_autoindex_masters_1_pg ON public.masters USING btree (name);


--
-- Name: notification_preferences_idx_notification_preferences_user_id_p; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX notification_preferences_idx_notification_preferences_user_id_p ON public.notification_preferences USING btree (user_id);


--
-- Name: notification_preferences_sqlite_autoindex_notification_preferen; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX notification_preferences_sqlite_autoindex_notification_preferen ON public.notification_preferences USING btree (user_id, notification_type);


--
-- Name: notifications_idx_notifications_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX notifications_idx_notifications_created_at_pg ON public.notifications USING btree (created_at);


--
-- Name: notifications_idx_notifications_entity_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX notifications_idx_notifications_entity_pg ON public.notifications USING btree (entity_type, entity_id);


--
-- Name: notifications_idx_notifications_read_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX notifications_idx_notifications_read_at_pg ON public.notifications USING btree (read_at);


--
-- Name: notifications_idx_notifications_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX notifications_idx_notifications_user_id_pg ON public.notifications USING btree (user_id);


--
-- Name: order_appearance_tags_idx_order_appearance_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_appearance_tags_idx_order_appearance_order_id_pg ON public.order_appearance_tags USING btree (order_id);


--
-- Name: order_appearance_tags_idx_order_appearance_tag_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_appearance_tags_idx_order_appearance_tag_id_pg ON public.order_appearance_tags USING btree (appearance_tag_id);


--
-- Name: order_appearance_tags_sqlite_autoindex_order_appearance_tags_1_; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX order_appearance_tags_sqlite_autoindex_order_appearance_tags_1_ ON public.order_appearance_tags USING btree (order_id, appearance_tag_id);


--
-- Name: order_comments_idx_order_comments_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_comments_idx_order_comments_created_at_pg ON public.order_comments USING btree (created_at);


--
-- Name: order_comments_idx_order_comments_new_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_comments_idx_order_comments_new_created_at_pg ON public.order_comments USING btree (created_at);


--
-- Name: order_comments_idx_order_comments_new_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_comments_idx_order_comments_new_order_id_pg ON public.order_comments USING btree (order_id);


--
-- Name: order_comments_idx_order_comments_order_created_desc_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_comments_idx_order_comments_order_created_desc_pg ON public.order_comments USING btree (order_id, created_at);


--
-- Name: order_comments_idx_order_comments_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_comments_idx_order_comments_order_id_pg ON public.order_comments USING btree (order_id);


--
-- Name: order_comments_idx_order_comments_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_comments_idx_order_comments_user_id_pg ON public.order_comments USING btree (user_id);


--
-- Name: order_models_idx_order_models_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_models_idx_order_models_name_pg ON public.order_models USING btree (name);


--
-- Name: order_models_sqlite_autoindex_order_models_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX order_models_sqlite_autoindex_order_models_1_pg ON public.order_models USING btree (name);


--
-- Name: order_parts_idx_order_parts_order_id_alt_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_parts_idx_order_parts_order_id_alt_pg ON public.order_parts USING btree (order_id);


--
-- Name: order_parts_idx_order_parts_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_parts_idx_order_parts_order_id_pg ON public.order_parts USING btree (order_id);


--
-- Name: order_parts_idx_order_parts_part_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_parts_idx_order_parts_part_id_pg ON public.order_parts USING btree (part_id);


--
-- Name: order_services_idx_order_services_order_id_alt_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_services_idx_order_services_order_id_alt_pg ON public.order_services USING btree (order_id);


--
-- Name: order_services_idx_order_services_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_services_idx_order_services_order_id_pg ON public.order_services USING btree (order_id);


--
-- Name: order_services_idx_order_services_service_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_services_idx_order_services_service_id_pg ON public.order_services USING btree (service_id);


--
-- Name: order_status_history_idx_order_status_history_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_status_history_idx_order_status_history_created_at_pg ON public.order_status_history USING btree (created_at);


--
-- Name: order_status_history_idx_order_status_history_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_status_history_idx_order_status_history_order_id_pg ON public.order_status_history USING btree (order_id);


--
-- Name: order_statuses_idx_order_statuses_code_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_statuses_idx_order_statuses_code_pg ON public.order_statuses USING btree (code);


--
-- Name: order_statuses_idx_order_statuses_is_default_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_statuses_idx_order_statuses_is_default_pg ON public.order_statuses USING btree (is_default);


--
-- Name: order_statuses_idx_order_statuses_sort_order_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_statuses_idx_order_statuses_sort_order_pg ON public.order_statuses USING btree (sort_order);


--
-- Name: order_statuses_sqlite_autoindex_order_statuses_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX order_statuses_sqlite_autoindex_order_statuses_1_pg ON public.order_statuses USING btree (code);


--
-- Name: order_symptoms_idx_order_symptoms_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_symptoms_idx_order_symptoms_order_id_pg ON public.order_symptoms USING btree (order_id);


--
-- Name: order_symptoms_idx_order_symptoms_symptom_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_symptoms_idx_order_symptoms_symptom_id_pg ON public.order_symptoms USING btree (symptom_id);


--
-- Name: order_symptoms_sqlite_autoindex_order_symptoms_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX order_symptoms_sqlite_autoindex_order_symptoms_1_pg ON public.order_symptoms USING btree (order_id, symptom_id);


--
-- Name: order_templates_idx_order_templates_created_by_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_templates_idx_order_templates_created_by_pg ON public.order_templates USING btree (created_by);


--
-- Name: order_templates_idx_order_templates_is_public_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_templates_idx_order_templates_is_public_pg ON public.order_templates USING btree (is_public);


--
-- Name: order_visibility_history_idx_order_visibility_history_changed_a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_visibility_history_idx_order_visibility_history_changed_a ON public.order_visibility_history USING btree (changed_at);


--
-- Name: order_visibility_history_idx_order_visibility_history_order_id_; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_visibility_history_idx_order_visibility_history_order_id_ ON public.order_visibility_history USING btree (order_id);


--
-- Name: orders_idx_orders_created_at_desc_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_created_at_desc_pg ON public.orders USING btree (created_at);


--
-- Name: orders_idx_orders_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_created_at_pg ON public.orders USING btree (created_at);


--
-- Name: orders_idx_orders_created_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_created_pg ON public.orders USING btree (created_at);


--
-- Name: orders_idx_orders_customer_created_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_customer_created_pg ON public.orders USING btree (customer_id, created_at);


--
-- Name: orders_idx_orders_customer_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_customer_id_pg ON public.orders USING btree (customer_id);


--
-- Name: orders_idx_orders_customer_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_customer_pg ON public.orders USING btree (customer_id);


--
-- Name: orders_idx_orders_device_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_device_id_pg ON public.orders USING btree (device_id);


--
-- Name: orders_idx_orders_device_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_device_pg ON public.orders USING btree (device_id);


--
-- Name: orders_idx_orders_hidden_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_hidden_created_at_pg ON public.orders USING btree (hidden, created_at);


--
-- Name: orders_idx_orders_hidden_deleted_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_hidden_deleted_pg ON public.orders USING btree (hidden, is_deleted);


--
-- Name: orders_idx_orders_hidden_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_hidden_pg ON public.orders USING btree (hidden);


--
-- Name: orders_idx_orders_is_deleted_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_is_deleted_pg ON public.orders USING btree (is_deleted);


--
-- Name: orders_idx_orders_manager_created_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_manager_created_pg ON public.orders USING btree (manager_id, created_at);


--
-- Name: orders_idx_orders_manager_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_manager_id_pg ON public.orders USING btree (manager_id);


--
-- Name: orders_idx_orders_master_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_master_id_pg ON public.orders USING btree (master_id);


--
-- Name: orders_idx_orders_master_status_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_master_status_pg ON public.orders USING btree (master_id, status_id);


--
-- Name: orders_idx_orders_model_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_model_id_pg ON public.orders USING btree (model_id);


--
-- Name: orders_idx_orders_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_order_id_pg ON public.orders USING btree (order_id);


--
-- Name: orders_idx_orders_prepayment_cents_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_prepayment_cents_pg ON public.orders USING btree (prepayment_cents);


--
-- Name: orders_idx_orders_status_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_status_created_at_pg ON public.orders USING btree (status_id, created_at);


--
-- Name: orders_idx_orders_status_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_status_id_pg ON public.orders USING btree (status_id);


--
-- Name: orders_idx_orders_status_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_status_pg ON public.orders USING btree (status);


--
-- Name: orders_idx_orders_updated_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_idx_orders_updated_at_pg ON public.orders USING btree (updated_at);


--
-- Name: orders_sqlite_autoindex_orders_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX orders_sqlite_autoindex_orders_1_pg ON public.orders USING btree (order_id);


--
-- Name: part_categories_idx_part_categories_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX part_categories_idx_part_categories_name_pg ON public.part_categories USING btree (name);


--
-- Name: part_categories_idx_part_categories_parent_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX part_categories_idx_part_categories_parent_id_pg ON public.part_categories USING btree (parent_id);


--
-- Name: part_categories_sqlite_autoindex_part_categories_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX part_categories_sqlite_autoindex_part_categories_1_pg ON public.part_categories USING btree (name);


--
-- Name: part_categories_ux_part_categories_name_parent_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX part_categories_ux_part_categories_name_parent_pg ON public.part_categories USING btree (name);


--
-- Name: parts_idx_parts_category_deleted_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parts_idx_parts_category_deleted_pg ON public.parts USING btree (category, is_deleted);


--
-- Name: parts_idx_parts_category_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parts_idx_parts_category_id_pg ON public.parts USING btree (category_id);


--
-- Name: parts_idx_parts_category_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parts_idx_parts_category_pg ON public.parts USING btree (category);


--
-- Name: parts_idx_parts_category_stock_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parts_idx_parts_category_stock_pg ON public.parts USING btree (category, stock_quantity);


--
-- Name: parts_idx_parts_is_deleted_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parts_idx_parts_is_deleted_pg ON public.parts USING btree (is_deleted);


--
-- Name: parts_idx_parts_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parts_idx_parts_name_pg ON public.parts USING btree (name);


--
-- Name: parts_idx_parts_part_number_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parts_idx_parts_part_number_pg ON public.parts USING btree (part_number);


--
-- Name: parts_idx_parts_stock_quantity_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parts_idx_parts_stock_quantity_pg ON public.parts USING btree (stock_quantity);


--
-- Name: parts_idx_parts_unit_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parts_idx_parts_unit_pg ON public.parts USING btree (unit);


--
-- Name: parts_ux_parts_name_part_number_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX parts_ux_parts_name_part_number_pg ON public.parts USING btree (name, part_number);


--
-- Name: payment_receipts_idx_payment_receipts_payment_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payment_receipts_idx_payment_receipts_payment_id_pg ON public.payment_receipts USING btree (payment_id);


--
-- Name: payments_idx_payments_not_cancelled_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payments_idx_payments_not_cancelled_pg ON public.payments USING btree (is_cancelled);


--
-- Name: payments_idx_payments_order_created_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payments_idx_payments_order_created_pg ON public.payments USING btree (order_id, created_at);


--
-- Name: payments_idx_payments_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payments_idx_payments_order_id_pg ON public.payments USING btree (order_id);


--
-- Name: payments_idx_payments_payment_date_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payments_idx_payments_payment_date_pg ON public.payments USING btree (payment_date);


--
-- Name: payments_idx_payments_payment_type_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payments_idx_payments_payment_type_pg ON public.payments USING btree (payment_type);


--
-- Name: payments_idx_payments_status_created_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payments_idx_payments_status_created_pg ON public.payments USING btree (status, created_at);


--
-- Name: payments_ux_payments_idempotency_key_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX payments_ux_payments_idempotency_key_pg ON public.payments USING btree (idempotency_key);


--
-- Name: permissions_idx_permissions_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX permissions_idx_permissions_name_pg ON public.permissions USING btree (name);


--
-- Name: permissions_sqlite_autoindex_permissions_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX permissions_sqlite_autoindex_permissions_1_pg ON public.permissions USING btree (name);


--
-- Name: print_templates_idx_print_templates_template_type_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX print_templates_idx_print_templates_template_type_pg ON public.print_templates USING btree (template_type);


--
-- Name: print_templates_sqlite_autoindex_print_templates_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX print_templates_sqlite_autoindex_print_templates_1_pg ON public.print_templates USING btree (name);


--
-- Name: purchase_items_idx_purchase_items_part_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX purchase_items_idx_purchase_items_part_id_pg ON public.purchase_items USING btree (part_id);


--
-- Name: purchase_items_idx_purchase_items_purchase_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX purchase_items_idx_purchase_items_purchase_id_pg ON public.purchase_items USING btree (purchase_id);


--
-- Name: purchases_idx_purchases_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX purchases_idx_purchases_created_at_pg ON public.purchases USING btree (created_at);


--
-- Name: purchases_idx_purchases_purchase_date_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX purchases_idx_purchases_purchase_date_pg ON public.purchases USING btree (purchase_date);


--
-- Name: purchases_idx_purchases_status_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX purchases_idx_purchases_status_pg ON public.purchases USING btree (status);


--
-- Name: purchases_idx_purchases_supplier_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX purchases_idx_purchases_supplier_id_pg ON public.purchases USING btree (supplier_id);


--
-- Name: role_permissions_idx_role_permissions_permission_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX role_permissions_idx_role_permissions_permission_pg ON public.role_permissions USING btree (permission_id);


--
-- Name: role_permissions_idx_role_permissions_role_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX role_permissions_idx_role_permissions_role_pg ON public.role_permissions USING btree (role);


--
-- Name: role_permissions_sqlite_autoindex_role_permissions_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX role_permissions_sqlite_autoindex_role_permissions_1_pg ON public.role_permissions USING btree (role, permission_id);


--
-- Name: salary_accruals_idx_salary_accruals_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_accruals_idx_salary_accruals_created_at_pg ON public.salary_accruals USING btree (created_at);


--
-- Name: salary_accruals_idx_salary_accruals_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_accruals_idx_salary_accruals_order_id_pg ON public.salary_accruals USING btree (order_id);


--
-- Name: salary_accruals_idx_salary_accruals_role_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_accruals_idx_salary_accruals_role_pg ON public.salary_accruals USING btree (role);


--
-- Name: salary_accruals_idx_salary_accruals_shop_sale_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_accruals_idx_salary_accruals_shop_sale_id_pg ON public.salary_accruals USING btree (shop_sale_id);


--
-- Name: salary_accruals_idx_salary_accruals_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_accruals_idx_salary_accruals_user_id_pg ON public.salary_accruals USING btree (user_id);


--
-- Name: salary_bonuses_idx_salary_bonuses_date_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_bonuses_idx_salary_bonuses_date_pg ON public.salary_bonuses USING btree (bonus_date);


--
-- Name: salary_bonuses_idx_salary_bonuses_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_bonuses_idx_salary_bonuses_order_id_pg ON public.salary_bonuses USING btree (order_id);


--
-- Name: salary_bonuses_idx_salary_bonuses_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_bonuses_idx_salary_bonuses_user_id_pg ON public.salary_bonuses USING btree (user_id, role);


--
-- Name: salary_fines_idx_salary_fines_date_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_fines_idx_salary_fines_date_pg ON public.salary_fines USING btree (fine_date);


--
-- Name: salary_fines_idx_salary_fines_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_fines_idx_salary_fines_order_id_pg ON public.salary_fines USING btree (order_id);


--
-- Name: salary_fines_idx_salary_fines_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_fines_idx_salary_fines_user_id_pg ON public.salary_fines USING btree (user_id, role);


--
-- Name: salary_payments_idx_salary_payments_cash_transaction_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_payments_idx_salary_payments_cash_transaction_id_pg ON public.salary_payments USING btree (cash_transaction_id);


--
-- Name: salary_payments_idx_salary_payments_date_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_payments_idx_salary_payments_date_pg ON public.salary_payments USING btree (payment_date);


--
-- Name: salary_payments_idx_salary_payments_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX salary_payments_idx_salary_payments_user_id_pg ON public.salary_payments USING btree (user_id, role);


--
-- Name: services_idx_services_is_default_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX services_idx_services_is_default_pg ON public.services USING btree (is_default);


--
-- Name: services_idx_services_sort_order_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX services_idx_services_sort_order_pg ON public.services USING btree (sort_order);


--
-- Name: services_ux_services_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX services_ux_services_name_pg ON public.services USING btree (name);


--
-- Name: shop_sale_items_idx_shop_sale_items_sale_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX shop_sale_items_idx_shop_sale_items_sale_pg ON public.shop_sale_items USING btree (shop_sale_id);


--
-- Name: shop_sales_idx_shop_sales_customer_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX shop_sales_idx_shop_sales_customer_pg ON public.shop_sales USING btree (customer_id);


--
-- Name: shop_sales_idx_shop_sales_date_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX shop_sales_idx_shop_sales_date_pg ON public.shop_sales USING btree (sale_date);


--
-- Name: stock_movements_idx_stock_movements_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stock_movements_idx_stock_movements_created_at_pg ON public.stock_movements USING btree (created_at);


--
-- Name: stock_movements_idx_stock_movements_date_type_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stock_movements_idx_stock_movements_date_type_pg ON public.stock_movements USING btree (created_at, movement_type);


--
-- Name: stock_movements_idx_stock_movements_movement_type_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stock_movements_idx_stock_movements_movement_type_pg ON public.stock_movements USING btree (movement_type);


--
-- Name: stock_movements_idx_stock_movements_part_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stock_movements_idx_stock_movements_part_id_pg ON public.stock_movements USING btree (part_id);


--
-- Name: stock_movements_idx_stock_movements_reference_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stock_movements_idx_stock_movements_reference_pg ON public.stock_movements USING btree (reference_type, reference_id);


--
-- Name: suppliers_idx_suppliers_is_active_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX suppliers_idx_suppliers_is_active_pg ON public.suppliers USING btree (is_active);


--
-- Name: suppliers_idx_suppliers_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX suppliers_idx_suppliers_name_pg ON public.suppliers USING btree (name);


--
-- Name: suppliers_sqlite_autoindex_suppliers_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX suppliers_sqlite_autoindex_suppliers_1_pg ON public.suppliers USING btree (name);


--
-- Name: symptoms_idx_symptoms_name_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX symptoms_idx_symptoms_name_pg ON public.symptoms USING btree (name);


--
-- Name: symptoms_idx_symptoms_sort_order_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX symptoms_idx_symptoms_sort_order_pg ON public.symptoms USING btree (sort_order);


--
-- Name: symptoms_sqlite_autoindex_symptoms_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX symptoms_sqlite_autoindex_symptoms_1_pg ON public.symptoms USING btree (name);


--
-- Name: system_settings_idx_system_settings_key_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_settings_idx_system_settings_key_pg ON public.system_settings USING btree (key);


--
-- Name: system_settings_sqlite_autoindex_system_settings_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX system_settings_sqlite_autoindex_system_settings_1_pg ON public.system_settings USING btree (key);


--
-- Name: task_checklists_idx_task_checklists_task_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX task_checklists_idx_task_checklists_task_id_pg ON public.task_checklists USING btree (task_id);


--
-- Name: tasks_idx_tasks_assigned_to_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tasks_idx_tasks_assigned_to_pg ON public.tasks USING btree (assigned_to);


--
-- Name: tasks_idx_tasks_created_by_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tasks_idx_tasks_created_by_pg ON public.tasks USING btree (created_by);


--
-- Name: tasks_idx_tasks_deadline_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tasks_idx_tasks_deadline_pg ON public.tasks USING btree (deadline);


--
-- Name: tasks_idx_tasks_order_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tasks_idx_tasks_order_id_pg ON public.tasks USING btree (order_id);


--
-- Name: tasks_idx_tasks_status_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tasks_idx_tasks_status_pg ON public.tasks USING btree (status);


--
-- Name: transaction_categories_ux_transaction_categories_name_type_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX transaction_categories_ux_transaction_categories_name_type_pg ON public.transaction_categories USING btree (name, type);


--
-- Name: uq_staff_chat_reactions_actor; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_staff_chat_reactions_actor ON public.staff_chat_reactions USING btree (message_id, user_id, actor_display_name, client_instance_id, emoji);


--
-- Name: idx_staff_chat_read_cursors_room; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_staff_chat_read_cursors_room ON public.staff_chat_read_cursors USING btree (room_key);


--
-- Name: uq_staff_chat_read_cursors_actor; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_staff_chat_read_cursors_actor ON public.staff_chat_read_cursors USING btree (room_key, user_id, actor_display_name, client_instance_id);


--
-- Name: user_role_history_idx_user_role_history_changed_by_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_role_history_idx_user_role_history_changed_by_pg ON public.user_role_history USING btree (changed_by);


--
-- Name: user_role_history_idx_user_role_history_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_role_history_idx_user_role_history_created_at_pg ON public.user_role_history USING btree (created_at);


--
-- Name: user_role_history_idx_user_role_history_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_role_history_idx_user_role_history_user_id_pg ON public.user_role_history USING btree (user_id);


--
-- Name: users_idx_users_is_active_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX users_idx_users_is_active_pg ON public.users USING btree (is_active);


--
-- Name: users_idx_users_role_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX users_idx_users_role_pg ON public.users USING btree (role);


--
-- Name: users_idx_users_username_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX users_idx_users_username_pg ON public.users USING btree (username);


--
-- Name: users_sqlite_autoindex_users_1_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX users_sqlite_autoindex_users_1_pg ON public.users USING btree (username);


--
-- Name: ux_salary_accruals_business_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_salary_accruals_business_key ON public.salary_accruals USING btree (order_id, user_id, role, rule_type, rule_value, calculated_from, COALESCE(calculated_from_id, ('-1'::integer)::bigint), amount_cents, base_amount_cents, profit_cents, COALESCE(vat_included, (0)::bigint));


--
-- Name: warehouse_logs_idx_warehouse_logs_category_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX warehouse_logs_idx_warehouse_logs_category_id_pg ON public.warehouse_logs USING btree (category_id);


--
-- Name: warehouse_logs_idx_warehouse_logs_created_at_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX warehouse_logs_idx_warehouse_logs_created_at_pg ON public.warehouse_logs USING btree (created_at);


--
-- Name: warehouse_logs_idx_warehouse_logs_operation_type_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX warehouse_logs_idx_warehouse_logs_operation_type_pg ON public.warehouse_logs USING btree (operation_type);


--
-- Name: warehouse_logs_idx_warehouse_logs_part_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX warehouse_logs_idx_warehouse_logs_part_id_pg ON public.warehouse_logs USING btree (part_id);


--
-- Name: warehouse_logs_idx_warehouse_logs_user_id_pg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX warehouse_logs_idx_warehouse_logs_user_id_pg ON public.warehouse_logs USING btree (user_id);


--
-- Name: staff_chat_attachments staff_chat_attachments_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_attachments
    ADD CONSTRAINT staff_chat_attachments_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.staff_chat_messages(id) ON DELETE CASCADE;


--
-- Name: staff_chat_messages staff_chat_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_messages
    ADD CONSTRAINT staff_chat_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: staff_chat_reactions staff_chat_reactions_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_reactions
    ADD CONSTRAINT staff_chat_reactions_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.staff_chat_messages(id) ON DELETE CASCADE;


--
-- Name: staff_chat_reactions staff_chat_reactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_reactions
    ADD CONSTRAINT staff_chat_reactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: staff_chat_read_cursors staff_chat_read_cursors_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_read_cursors
    ADD CONSTRAINT staff_chat_read_cursors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


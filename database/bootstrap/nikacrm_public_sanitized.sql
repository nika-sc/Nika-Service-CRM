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
    estimated_cost text DEFAULT '0'::text,
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
-- Name: order_pins; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_pins (
    id bigint NOT NULL,
    order_id bigint NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: order_pins_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_pins_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_pins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_pins_id_seq OWNED BY public.order_pins.id;


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
-- Name: staff_chat_web_push_subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staff_chat_web_push_subscriptions (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    endpoint text NOT NULL,
    p256dh text NOT NULL,
    auth text NOT NULL,
    user_agent text DEFAULT ''::text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: staff_chat_web_push_subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.staff_chat_web_push_subscriptions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: staff_chat_web_push_subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.staff_chat_web_push_subscriptions_id_seq OWNED BY public.staff_chat_web_push_subscriptions.id;


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
-- Name: order_pins id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_pins ALTER COLUMN id SET DEFAULT nextval('public.order_pins_id_seq'::regclass);


--
-- Name: staff_chat_web_push_subscriptions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_web_push_subscriptions ALTER COLUMN id SET DEFAULT nextval('public.staff_chat_web_push_subscriptions_id_seq'::regclass);


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
1	Без повреждений	1	2026-04-07 20:10:55
2	Царапины на корпусе	2	2026-04-07 20:10:55
3	Потёртости	3	2026-04-07 20:10:55
4	Сколы на корпусе	4	2026-04-07 20:10:55
5	Трещина на корпусе	5	2026-04-07 20:10:55
6	Разбито стекло экрана	6	2026-04-07 20:10:55
7	Вмятина на корпусе	7	2026-04-07 20:10:55
8	Следы вскрытия	8	2026-04-07 20:10:55
9	Следы влаги	9	2026-04-07 20:10:55
10	Отсутствует крышка	10	2026-04-07 20:10:55
11	Без зарядного устройства	11	2026-04-07 20:10:55
12	Зарядное устройство	12	2026-04-07 20:10:55
13	Кабель питания	13	2026-04-07 20:10:55
14	Сумка или чехол	14	2026-04-07 20:10:55
15	Мышь	15	2026-04-07 20:10:55
16	Клавиатура	16	2026-04-07 20:10:55
17	Комплект в коробке	17	2026-04-07 20:10:55
18	Без SIM-карты и карты памяти	18	2026-04-07 20:10:55
19	Картридж	19	2026-04-07 20:10:55
20	Пульт	20	2026-04-07 20:10:55
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
1	Acer	2026-04-07 20:10:55	1
2	Apple	2026-04-07 20:10:55	2
3	Asus	2026-04-07 20:10:55	3
4	Brother	2026-04-07 20:10:55	4
5	Canon	2026-04-07 20:10:55	5
6	DeLonghi	2026-04-07 20:10:55	6
7	Dell	2026-04-07 20:10:55	7
8	Epson	2026-04-07 20:10:55	8
9	HP	2026-04-07 20:10:55	9
10	Honor	2026-04-07 20:10:55	10
11	Huawei	2026-04-07 20:10:55	11
12	Kyocera	2026-04-07 20:10:55	12
13	LG	2026-04-07 20:10:55	13
14	Lenovo	2026-04-07 20:10:55	14
15	MSI	2026-04-07 20:10:55	15
16	Microsoft	2026-04-07 20:10:55	16
17	Nokia	2026-04-07 20:10:55	17
18	Pantum	2026-04-07 20:10:55	18
19	Philips	2026-04-07 20:10:55	19
20	Realme	2026-04-07 20:10:55	20
21	Samsung	2026-04-07 20:10:55	21
22	Sony	2026-04-07 20:10:55	22
23	TP-Link	2026-04-07 20:10:55	23
24	Toshiba	2026-04-07 20:10:55	24
25	Xerox	2026-04-07 20:10:55	25
26	Xiaomi	2026-04-07 20:10:55	26
27	ZTE	2026-04-07 20:10:55	27
28	Прочее	2026-04-07 20:10:55	28
\.


--
-- Data for Name: device_types; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.device_types (id, name, created_at, sort_order) FROM stdin;
1	Ноутбук	2026-04-07 20:10:55	1
2	Смартфон	2026-04-07 20:10:55	2
3	Планшет	2026-04-07 20:10:55	3
4	Системный блок	2026-04-07 20:10:55	4
5	Моноблок	2026-04-07 20:10:55	5
6	Монитор	2026-04-07 20:10:55	6
7	Принтер	2026-04-07 20:10:55	7
8	МФУ	2026-04-07 20:10:55	8
9	Телевизор	2026-04-07 20:10:55	9
10	Игровая консоль	2026-04-07 20:10:55	10
11	Умные часы	2026-04-07 20:10:55	11
12	Наушники	2026-04-07 20:10:55	12
13	Роутер	2026-04-07 20:10:55	13
14	Пылесос	2026-04-07 20:10:55	14
15	Кофемашина	2026-04-07 20:10:55	15
16	Прочее	2026-04-07 20:10:55	16
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
1	Nika Service CRM Demo	+7 (900) 000-00-00	Demo address				RUB	Россия	2025-11-27 15:44:30	30	3		587	1	0				3	choice	1	1	1	1	0	0	Demo Director	Director		1	1
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
1	iPhone 11	2026-04-07 20:10:55
2	iPhone 13	2026-04-07 20:10:55
3	iPhone 15	2026-04-07 20:10:55
4	iPad Air	2026-04-07 20:10:55
5	MacBook Air M1	2026-04-07 20:10:55
6	MacBook Pro 14	2026-04-07 20:10:55
7	Apple Watch SE	2026-04-07 20:10:55
8	Galaxy A54	2026-04-07 20:10:55
9	Galaxy S23	2026-04-07 20:10:55
10	Galaxy Tab A8	2026-04-07 20:10:55
11	Redmi Note 12	2026-04-07 20:10:55
12	Redmi 10C	2026-04-07 20:10:55
13	VivoBook 15	2026-04-07 20:10:55
14	ZenBook 14	2026-04-07 20:10:55
15	TUF Gaming F15	2026-04-07 20:10:55
16	ROG Strix G16	2026-04-07 20:10:55
17	Aspire 5	2026-04-07 20:10:55
18	Nitro 5	2026-04-07 20:10:55
19	Swift 3	2026-04-07 20:10:55
20	IdeaPad 3	2026-04-07 20:10:55
21	ThinkPad E14	2026-04-07 20:10:55
22	Legion 5	2026-04-07 20:10:55
23	Pavilion 15	2026-04-07 20:10:55
24	ProBook 450	2026-04-07 20:10:55
25	Inspiron 15	2026-04-07 20:10:55
26	Latitude 5420	2026-04-07 20:10:55
27	Vostro 3500	2026-04-07 20:10:55
28	Modern 14	2026-04-07 20:10:55
29	Katana GF66	2026-04-07 20:10:55
30	Satellite C650	2026-04-07 20:10:55
31	Magic 5 Lite	2026-04-07 20:10:55
32	MatePad 11	2026-04-07 20:10:55
33	Realme C55	2026-04-07 20:10:55
34	Blade A52	2026-04-07 20:10:55
35	Nokia G21	2026-04-07 20:10:55
36	LaserJet M1132	2026-04-07 20:10:55
37	LaserJet Pro M404dn	2026-04-07 20:10:55
38	i-SENSYS MF3010	2026-04-07 20:10:55
39	PIXMA G3411	2026-04-07 20:10:55
40	Epson L3150	2026-04-07 20:10:55
41	Epson L805	2026-04-07 20:10:55
42	Ecosys M2040dn	2026-04-07 20:10:55
43	FS-1040	2026-04-07 20:10:55
44	DCP-1510R	2026-04-07 20:10:55
45	Pantum P2500W	2026-04-07 20:10:55
46	Pantum M6500	2026-04-07 20:10:55
47	Phaser 3020	2026-04-07 20:10:55
48	SCX-3400	2026-04-07 20:10:55
49	PlayStation 4	2026-04-07 20:10:55
50	PlayStation 5	2026-04-07 20:10:55
51	Xbox Series S	2026-04-07 20:10:55
52	Bravia KD-43	2026-04-07 20:10:55
53	OLED55C2	2026-04-07 20:10:55
54	Archer C6	2026-04-07 20:10:55
55	Magnifica S	2026-04-07 20:10:55
56	Series 3200	2026-04-07 20:10:55
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
1	Тестовая категория	\N	2026-04-07 20:10:55	2026-04-07 20:10:55	\N
\.


--
-- Data for Name: parts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parts (id, name, part_number, description, price, stock_quantity, min_quantity, category, supplier, created_at, updated_at, purchase_price, unit, warranty_days, is_deleted, comment, category_id, salary_rule_type, salary_rule_value) FROM stdin;
1	Тестовый товар	TEST-001	\N	1000	10	1	\N	\N	2026-04-07 20:10:55	2026-04-07 20:10:55	500	шт	30	0	\N	1	\N	\N
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
4	Квитанция для клиента	customer	<table border="1">\n<tbody>\n<tr>\n<td>\n<h1>Приемная квитанция</h1>\n<p>Заказ <strong>##ORDER_NUMBER##</strong> от <strong>##CREATED_AT##</strong></p>\n<ol>\n<li>Оборудование принимается без разборки и проверки внутренних повреждений. Все скрытые неисправности считаются возникшими до приема.</li>\n<li>При отказе от ремонта после диагностики Заказчик оплачивает диагностику и чистку в размере <strong>2000##CURRENCY##</strong>.</li>\n<li>Гарантия действует только на выполненные работы и замененные детали, срок гарантии &mdash; 2 месяца.</li>\n<li>Окончательная стоимость ремонта определяется после диагностики и согласования.</li>\n<li>Срок хранения готового заказа &mdash; 7 дней. После 10 дней техника передается на склад, хранение &mdash; 2000##CURRENCY##.</li>\n<li>Срок диагностики: от 1 до 5 дней с даты принятия заявки.</li>\n</ol>\n</td>\n<td>\n<p><strong>##COMPANY_NAME##</strong></p>\n<p>##branch.address##<br>##branch.phone##<br>##COMPANY_REQUISITES##</p>\n</td>\n</tr>\n</tbody>\n</table>\n<table border="1">\n<tbody>\n<tr>\n<td><strong>Клиент</strong></td>\n<td>##CLIENT_NAME##, ##CLIENT_PHONE1##</td>\n<td rowspan="2">&nbsp;</td>\n</tr>\n<tr>\n<td><strong>Устройство</strong></td>\n<td>##701809f9-23dc-4346-aff4-0aef32523aef##, ##b6a8f943-e1b0-46e8-a321-b25fcfaf6976## ##c76b5bc7-7a68-4672-9542-cabaf2962600##</td>\n</tr>\n<tr>\n<td><strong>Внешний вид / комплектация</strong></td>\n<td>##bc1ae9b1-7b8b-4da6-add5-26982865629e##</td>\n<td rowspan="2">&nbsp;</td>\n</tr>\n<tr>\n<td><strong>Неисправность</strong></td>\n<td>##f93f4677-15b5-4e57-97e7-a345cb5b0e21##</td>\n</tr>\n</tbody>\n</table>\n<table border="1">\n<tbody>\n<tr>\n<td colspan="2">\n<p><strong>Предварительная стоимость: ##ESTIMATED_COST## ##CURRENCY##</strong></p>\n<p><strong>Предоплата: ##TOTAL_PAID## (##total.paid.words##)</strong></p>\n</td>\n</tr>\n<tr>\n<td><strong>Мастер</strong>: __________________ ##ENGINEER_NAME##</td>\n<td><strong>Заказчик</strong>: __________________ ##CLIENT_NAME##<br>с условиями оказания услуг ознакомлен и согласен</td>\n</tr>\n<tr>\n<td colspan="2"><strong>Дата</strong>: ##DATE_TODAY## ##TIME_NOW##</td>\n</tr>\n</tbody>\n</table>\n<p>✂ ---------------------------------------------------------------</p>\n<table border="1">\n<tbody>\n<tr>\n<td>\n<h3>Заказ ##ORDER_NUMBER## от ##CREATED_AT##</h3>\n</td>\n<td>##ticket.numberId.barcode##</td>\n</tr>\n</tbody>\n</table>\n<table border="1">\n<tbody>\n<tr>\n<td><strong>Клиент</strong></td>\n<td>##CLIENT_NAME##, ##CLIENT_PHONE1##</td>\n</tr>\n<tr>\n<td><strong>Устройство</strong></td>\n<td>##701809f9-23dc-4346-aff4-0aef32523aef##, ##b6a8f943-e1b0-46e8-a321-b25fcfaf6976## ##c76b5bc7-7a68-4672-9542-cabaf2962600##, ##c5286c7d-44aa-4579-8258-935b003998cf##</td>\n</tr>\n<tr>\n<td><strong>Внешний вид / комплектация</strong></td>\n<td>##bc1ae9b1-7b8b-4da6-add5-26982865629e##</td>\n</tr>\n<tr>\n<td><strong>Неисправность</strong></td>\n<td>##f93f4677-15b5-4e57-97e7-a345cb5b0e21##</td>\n</tr>\n</tbody>\n</table>	2025-11-29 15:41:47	2026-03-02 18:42:31
6	Товарный чек	sales_receipt	<table border="1">\n<tbody>\n<tr>\n<td>\n<h1>Товарный чек</h1>\n<p>Продажа от <strong>##CREATED_AT##</strong></p>\n<p>&nbsp;</p>\n</td>\n<td>\n<p><strong>##COMPANY_NAME##</strong></p>\n<p>##branch.address##<br>##branch.phone##<br>##COMPANY_REQUISITES##</p>\n</td>\n</tr>\n</tbody>\n</table>\n<p>Товары и услуги</p>\n<table border="1">\n<tbody>\n<tr>\n<td><strong>№</strong></td>\n<td><strong>Позиция</strong></td>\n<td><strong>Артикул</strong></td>\n<td><strong>Гарантия, дн.</strong></td>\n<td><strong>Цена, ##CURRENCY##</strong></td>\n<td><strong>Скидка, ##CURRENCY##</strong></td>\n<td><strong>Количество</strong></td>\n<td><strong>Сумма, ##CURRENCY##</strong></td>\n</tr>\n</tbody>\n<tbody>\n<tr data-for="ITEMS">\n<td>##INDEX##</td>\n<td>##ITEM_NAME##</td>\n<td>##ITEM_SKU##</td>\n<td>##ITEM_WARRANTY##</td>\n<td>##ITEM_PRICE##</td>\n<td>##ITEM_DISCOUNT##</td>\n<td>##ITEM_QUANTITY##</td>\n<td>##ITEM_SUM##</td>\n</tr>\n<tr>\n<td colspan="7"><strong>Сумма, ##CURRENCY##</strong></td>\n<td><strong>##TOTAL_ITEMS##</strong></td>\n</tr>\n</tbody>\n</table>\n<p>&nbsp;</p>\n<table border="1">\n<tbody>\n<tr>\n<td>\n<p><strong>Продавец</strong>: __________________ ##EMPLOYEE_NAME##</p>\n<p><br><strong>Дата</strong>: ##DATE_TODAY## ##TIME_NOW##</p>\n</td>\n</tr>\n</tbody>\n</table>	2026-02-22 18:57:22	2026-02-24 21:52:55
7	Акт выполненных работ	work_act	<table border="1">\n<tbody>\n<tr>\n<td>\n<h1>Акт выполненных работ</h1>\n<p>№ заказа <strong>##ORDER_NUMBER##</strong> от <strong>##CREATED_AT##</strong></p>\n<p>Настоящий акт составлен о том, что Исполнителем выполнены нижеперечисленные работы (оказаны услуги), оборудование (товар) передано Заказчику.</p>\n</td>\n<td>\n<p><strong>##COMPANY_NAME##</strong></p>\n<p>##branch.address##<br>##branch.phone##<br>##COMPANY_REQUISITES##</p>\n<p>&nbsp;</p>\n</td>\n</tr>\n</tbody>\n</table>\n<table border="1">\n<tbody>\n<tr>\n<td><strong>Заказчик</strong></td>\n<td>##CLIENT_NAME##, ##CLIENT_PHONE1##</td>\n</tr>\n<tr>\n<td><strong>Исполнитель</strong></td>\n<td>##COMPANY_NAME##</td>\n</tr>\n</tbody>\n</table>\n<p>&nbsp;</p>\n<table border="1">\n<tbody>\n<tr>\n<td><strong>№</strong></td>\n<td><strong>Наименование работ (услуг) / товара</strong></td>\n<td><strong>Артикул</strong></td>\n<td><strong>Гарантия, дн.</strong></td>\n<td><strong>Цена, ##CURRENCY##</strong></td>\n<td><strong>Скидка, ##CURRENCY##</strong></td>\n<td><strong>Кол-во</strong></td>\n<td><strong>Сумма, ##CURRENCY##</strong></td>\n</tr>\n</tbody>\n<tbody>\n<tr data-for="ITEMS">\n<td>##INDEX##</td>\n<td>##ITEM_NAME##</td>\n<td>##ITEM_SKU##</td>\n<td>##ITEM_WARRANTY##</td>\n<td>##ITEM_PRICE##</td>\n<td>##ITEM_DISCOUNT##</td>\n<td>##ITEM_QUANTITY##</td>\n<td>##ITEM_SUM##</td>\n</tr>\n<tr>\n<td colspan="7"><strong>Итого:</strong></td>\n<td><strong>##TOTAL_ITEMS## ##CURRENCY##</strong></td>\n</tr>\n</tbody>\n</table>\n<p><strong>Работы выполнены в полном объёме, в срок и с надлежащим качеством. Заказчик претензий по объёму, срокам и качеству не имеет. Стоимость работ (услуг) и товаров Заказчиком принята.</strong></p>\n<table border="1">\n<tbody>\n<tr>\n<td>\n<p><strong>Исполнитель</strong>: __________________ / ##EMPLOYEE_NAME##</p>\n</td>\n<td>\n<p><strong>Заказчик</strong>: __________________ / ##CLIENT_NAME##</p>\n</td>\n</tr>\n<tr>\n<td colspan="2"><strong>Дата</strong>: ##DATE_TODAY## ##TIME_NOW##</td>\n</tr>\n</tbody>\n</table>	2026-02-22 18:57:22	2026-02-24 21:53:40
2	Техническая информация для мастера	master	<div class="print-section">\r\n    <div class="print-header">\r\n        {% if settings.logo_url %}\r\n        <img src="{{ settings.logo_url }}" alt="Logo" class="print-logo">\r\n        {% endif %}\r\n        <div class="print-title">##ORG_NAME##</div>\r\n    </div>\r\n    \r\n    <h2 class="text-center mb-4">ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ</h2>\r\n    \r\n    <table class="print-info-table">\r\n        <tr>\r\n            <td>Номер заявки:</td>\r\n            <td><strong>##ORDER_ID##</strong></td>\r\n        </tr>\r\n        <tr>\r\n            <td>UUID заявки:</td>\r\n            <td><small>##ORDER_UUID##</small></td>\r\n        </tr>\r\n        <tr>\r\n            <td>Дата создания:</td>\r\n            <td>##ORDER_CREATED_AT##</td>\r\n        </tr>\r\n        <tr>\r\n            <td>Дата обновления:</td>\r\n            <td>##ORDER_UPDATED_AT##</td>\r\n        </tr>\r\n    </table>\r\n    \r\n    <h4 class="mt-4 mb-3">Информация о клиенте:</h4>\r\n    <table class="print-info-table">\r\n        <tr>\r\n            <td>ФИО/Компания:</td>\r\n            <td><strong>##CLIENT_NAME##</strong></td>\r\n        </tr>\r\n        <tr>\r\n            <td>Телефон:</td>\r\n            <td>##CLIENT_PHONE##</td>\r\n        </tr>\r\n        <tr>\r\n            <td>Email:</td>\r\n            <td>##CLIENT_EMAIL##</td>\r\n        </tr>\r\n    </table>\r\n    \r\n    <h4 class="mt-4 mb-3">Информация об устройстве:</h4>\r\n    <table class="print-info-table">\r\n        <tr>\r\n            <td>Тип устройства:</td>\r\n            <td>##DEVICE_TYPE##</td>\r\n        </tr>\r\n        <tr>\r\n            <td>Бренд:</td>\r\n            <td>##DEVICE_BRAND##</td>\r\n        </tr>\r\n        <tr>\r\n            <td>Серийный номер:</td>\r\n            <td>##SERIAL_NUMBER##</td>\r\n        </tr>\r\n        ##IF_PASSWORD##\r\n        <tr>\r\n            <td>Пароль:</td>\r\n            <td><strong>##PASSWORD##</strong></td>\r\n        </tr>\r\n        ##END_IF_PASSWORD##\r\n    </table>\r\n    \r\n    ##IF_APPEARANCE##\r\n    <h4 class="mt-4 mb-3">Внешний вид и комплектация:</h4>\r\n    <div class="mb-3">##APPEARANCE##</div>\r\n    ##END_IF_APPEARANCE##\r\n    \r\n    ##IF_SYMPTOMS##\r\n    <h4 class="mt-4 mb-3">Симптомы и описание неисправности:</h4>\r\n    <div class="mb-3">##SYMPTOMS##</div>\r\n    ##END_IF_SYMPTOMS##\r\n    \r\n    ##IF_COMMENT##\r\n    <h4 class="mt-4 mb-3">Комментарий:</h4>\r\n    <div class="mb-3">##COMMENT##</div>\r\n    ##END_IF_COMMENT##\r\n    \r\n    <div class="print-divider"></div>\r\n    \r\n    <h4 class="mt-4 mb-3">Ответственные лица:</h4>\r\n    <table class="print-info-table">\r\n        <tr>\r\n            <td>Менеджер:</td>\r\n            <td><strong>##MANAGER_NAME##</strong></td>\r\n        </tr>\r\n        <tr>\r\n            <td>Мастер:</td>\r\n            <td><strong>##MASTER_NAME##</strong></td>\r\n        </tr>\r\n        <tr>\r\n            <td>Статус:</td>\r\n            <td><strong>##STATUS_NAME##</strong></td>\r\n        </tr>\r\n    </table>\r\n    \r\n    <h4 class="mt-4 mb-3">Финансовая информация:</h4>\r\n    <table class="print-info-table">\r\n        <tr>\r\n            <td>Предварительная стоимость:</td>\r\n            <td><strong>##ESTIMATED_COST## ##CURRENCY##</strong></td>\r\n        </tr>\r\n        <tr>\r\n            <td>Предоплата:</td>\r\n            <td><strong>##PREPAYMENT## ##CURRENCY##</strong></td>\r\n        </tr>\r\n    </table>\r\n    \r\n    <div class="print-footer mt-4">\r\n        <p><strong>Примечания для мастера:</strong></p>\r\n        <div style="min-height: 100px; border: 1px solid #ddd; padding: 10px; margin-top: 10px;">\r\n            <p>_________________________________________________________________</p>\r\n            <p>_________________________________________________________________</p>\r\n            <p>_________________________________________________________________</p>\r\n        </div>\r\n        \r\n        <div class="mt-4">\r\n            <div style="display: inline-block; margin-right: 100px;">\r\n                <div>Мастер: _________________</div>\r\n                <div class="print-signature-line"></div>\r\n                <div style="margin-top: 5px;">##MASTER_NAME##</div>\r\n            </div>\r\n            <div style="display: inline-block;">\r\n                <div>Дата: _________________</div>\r\n                <div class="print-signature-line"></div>\r\n            </div>\r\n        </div>\r\n    </div>\r\n</div>	2025-11-27 17:23:24	2025-11-27 20:43:24
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
008	staff_chat_web_push	2026-04-10 00:00:00
009	order_pins	2026-04-15 00:00:00
010	redact_smtp_password_logs	2026-07-25 00:00:00
011	demo_visitor_events	2026-07-27 00:00:00
012	demo_visitor_client_instance	2026-07-27 00:00:00
013	invoices_b2b	2026-07-28 00:00:00
014	invoice_catalog_links	2026-07-28 00:00:00
015	order_estimated_cost	2026-08-08 00:00:00
016	receipt_appearance_estimated	2026-08-08 00:00:00
017	order_diagnostics	2026-08-15 00:00:00
018	order_diagnostics_history	2026-08-15 00:00:00
019	order_model_catalog_links	2026-08-16 00:00:00
020	receipt_estimated_literal_newline	2026-08-16 00:00:00
021	diagnostics_templates	2026-08-20 00:00:00
022	diagnostics_templates_is_active_int	2026-08-22 00:00:00
023	diagnostics_templates_seed	2026-08-22 00:00:00
024	order_customer_emails	2026-08-22 00:00:00
025	locale_settings	2026-08-24 00:00:00
\.


--
-- Data for Name: order_pins; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_pins (id, order_id, user_id, created_at) FROM stdin;
\.


--
-- Data for Name: services; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.services (id, name, price, is_default, sort_order, created_at, updated_at, salary_rule_type, salary_rule_value) FROM stdin;
1	Диагностика	0	0	1	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
2	Чистка от пыли с заменой термопасты	2500	0	2	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
3	Установка операционной системы	1500	0	3	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
4	Установка программ	700	0	4	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
5	Замена аккумулятора	1000	0	5	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
6	Замена матрицы ноутбука	3500	0	6	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
7	Замена разъёма питания	2000	0	7	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
8	Ремонт цепи питания	4000	0	8	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
9	Восстановление данных	2500	0	9	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
10	Заправка картриджа	600	0	10	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
11	Ремонт принтера	1500	0	11	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
12	Ремонт игровой консоли	2500	0	12	2026-04-07 20:10:55	2026-04-07 20:10:55	\N	\N
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
-- Data for Name: staff_chat_web_push_subscriptions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.staff_chat_web_push_subscriptions (id, user_id, endpoint, p256dh, auth, user_agent, created_at, updated_at) FROM stdin;
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
1	Диагностика	1	2026-04-07 20:10:55
2	Не включается	2	2026-04-07 20:10:55
3	Не заряжается	3	2026-04-07 20:10:55
4	Быстро разряжается	4	2026-04-07 20:10:55
5	Разбит экран	5	2026-04-07 20:10:55
6	Нет изображения	6	2026-04-07 20:10:55
7	Полосы на экране	7	2026-04-07 20:10:55
8	Не работает подсветка	8	2026-04-07 20:10:55
9	Перегревается	9	2026-04-07 20:10:55
10	Шумит вентилятор	10	2026-04-07 20:10:55
11	Самопроизвольно выключается	11	2026-04-07 20:10:55
12	Не загружается операционная система	12	2026-04-07 20:10:55
13	Синий экран	13	2026-04-07 20:10:55
14	Медленно работает	14	2026-04-07 20:10:55
15	Вирусы и реклама в браузере	15	2026-04-07 20:10:55
16	Не видит жёсткий диск	16	2026-04-07 20:10:55
17	Не работает клавиатура	17	2026-04-07 20:10:55
18	Не работает тачпад	18	2026-04-07 20:10:55
19	Залит жидкостью	19	2026-04-07 20:10:55
20	Нет звука	20	2026-04-07 20:10:55
21	Не работает микрофон	21	2026-04-07 20:10:55
22	Не работает камера	22	2026-04-07 20:10:55
23	Не видит Wi-Fi	23	2026-04-07 20:10:55
24	Не работает USB-порт	24	2026-04-07 20:10:55
25	Не читает SIM-карту	25	2026-04-07 20:10:55
26	Не работает кнопка включения	26	2026-04-07 20:10:55
27	Не работает динамик	27	2026-04-07 20:10:55
28	Требуется чистка от пыли	28	2026-04-07 20:10:55
29	Замена термопасты	29	2026-04-07 20:10:55
30	Замена аккумулятора	30	2026-04-07 20:10:55
31	Замена матрицы	31	2026-04-07 20:10:55
32	Установка операционной системы	32	2026-04-07 20:10:55
33	Установка программ	33	2026-04-07 20:10:55
34	Восстановление данных	34	2026-04-07 20:10:55
35	Не печатает	35	2026-04-07 20:10:55
36	Полосы при печати	36	2026-04-07 20:10:55
37	Замятие бумаги	37	2026-04-07 20:10:55
38	Не захватывает бумагу	38	2026-04-07 20:10:55
39	Не сканирует	39	2026-04-07 20:10:55
40	Требуется заправка картриджа	40	2026-04-07 20:10:55
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

SELECT pg_catalog.setval('public.appearance_tags_id_seq', 20, true);


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

SELECT pg_catalog.setval('public.device_brands_id_seq', 28, true);


--
-- Name: device_types_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.device_types_id_seq', 16, true);


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

SELECT pg_catalog.setval('public.order_models_id_seq', 56, true);


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

SELECT pg_catalog.setval('public.part_categories_id_seq', 1, true);


--
-- Name: parts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.parts_id_seq', 1, true);


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

SELECT pg_catalog.setval('public.print_templates_id_seq', 7, true);


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

SELECT pg_catalog.setval('public.services_id_seq', 12, true);


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
-- Name: order_pins_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.order_pins_id_seq', 1, false);


--
-- Name: staff_chat_reactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.staff_chat_reactions_id_seq', 1, false);


--
-- Name: staff_chat_read_cursors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.staff_chat_read_cursors_id_seq', 1, false);


--
-- Name: staff_chat_web_push_subscriptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.staff_chat_web_push_subscriptions_id_seq', 1, false);


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

SELECT pg_catalog.setval('public.symptoms_id_seq', 40, true);


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
-- Name: order_pins order_pins_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_pins
    ADD CONSTRAINT order_pins_pkey PRIMARY KEY (id);


--
-- Name: order_pins uq_order_pins_order_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_pins
    ADD CONSTRAINT uq_order_pins_order_user UNIQUE (order_id, user_id);


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
-- Name: staff_chat_web_push_subscriptions staff_chat_web_push_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_web_push_subscriptions
    ADD CONSTRAINT staff_chat_web_push_subscriptions_pkey PRIMARY KEY (id);


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
-- Name: idx_staff_chat_web_push_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_staff_chat_web_push_user ON public.staff_chat_web_push_subscriptions USING btree (user_id);


--
-- Name: uq_staff_chat_web_push_user_endpoint; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_staff_chat_web_push_user_endpoint ON public.staff_chat_web_push_subscriptions USING btree (user_id, endpoint);


--
-- Name: idx_order_pins_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_pins_order ON public.order_pins USING btree (order_id);


--
-- Name: idx_order_pins_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_pins_user_created ON public.order_pins USING btree (user_id, created_at DESC);


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
-- Name: staff_chat_web_push_subscriptions staff_chat_web_push_subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_chat_web_push_subscriptions
    ADD CONSTRAINT staff_chat_web_push_subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: order_pins order_pins_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_pins
    ADD CONSTRAINT order_pins_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_pins order_pins_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_pins
    ADD CONSTRAINT order_pins_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

-- =====================================================================
-- Post-bootstrap schema: postgres migrations 011-016 (idempotent)
-- =====================================================================
-- pg_dump sets search_path to '' (empty). Unqualified CREATE/ALTER in this
-- tail would fail with "no schema has been selected to create in" on Windows
-- installer / fresh psql -f import. Restore public before idempotent DDL.
SET search_path TO public;

-- Demo-only visitor / presence events (enabled via DEMO_VISITOR_STATS=1)
CREATE TABLE IF NOT EXISTS demo_visitor_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NULL,
    username TEXT NULL,
    ip TEXT NULL,
    user_agent TEXT NULL,
    path TEXT NULL,
    event_type TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_created
    ON demo_visitor_events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_user_created
    ON demo_visitor_events(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_type_created
    ON demo_visitor_events(event_type, created_at DESC);

-- Distinguish browser sessions for demo online stats (same login, different browsers)
ALTER TABLE demo_visitor_events
    ADD COLUMN IF NOT EXISTS client_instance_id TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_client_created
    ON demo_visitor_events(client_instance_id, created_at DESC);

-- 013: B2B invoices (юрлица/ИП)



ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS bank_name TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS bik TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS checking_account TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS corr_account TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS kpp TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS ogrnip TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS legal_address TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS director_title TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS director_name TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS accountant_name TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS signature_url TEXT;

ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS stamp_url TEXT;



ALTER TABLE customers ADD COLUMN IF NOT EXISTS customer_kind TEXT DEFAULT 'person';

ALTER TABLE customers ADD COLUMN IF NOT EXISTS inn TEXT;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS kpp TEXT;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS ogrn TEXT;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS legal_name TEXT;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS legal_address TEXT;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS bank_name TEXT;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS bik TEXT;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS checking_account TEXT;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS corr_account TEXT;

CREATE TABLE IF NOT EXISTS invoice_sequences (
    id BIGSERIAL PRIMARY KEY,
    doc_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    last_number INTEGER NOT NULL DEFAULT 0,
    UNIQUE(doc_type, year)
);

CREATE TABLE IF NOT EXISTS invoices (
    id BIGSERIAL PRIMARY KEY,
    number INTEGER NOT NULL,
    act_number INTEGER,
    waybill_number INTEGER,
    issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date DATE,
    status TEXT NOT NULL DEFAULT 'unpaid',
    order_id BIGINT REFERENCES orders(id),
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    buyer_kind TEXT,
    buyer_name TEXT,
    buyer_inn TEXT,
    buyer_kpp TEXT,
    buyer_ogrn TEXT,
    buyer_address TEXT,
    buyer_bank_name TEXT,
    buyer_bik TEXT,
    buyer_checking_account TEXT,
    buyer_corr_account TEXT,
    seller_snapshot TEXT,
    subtotal_cents INTEGER NOT NULL DEFAULT 0,
    vat_mode TEXT NOT NULL DEFAULT 'none',
    total_cents INTEGER NOT NULL DEFAULT 0,
    comment TEXT,
    paid_at TIMESTAMP,
    paid_by_user_id BIGINT REFERENCES users(id),
    payment_id BIGINT REFERENCES payments(id),
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_order ON invoices(order_id);
CREATE INDEX IF NOT EXISTS idx_invoices_issued ON invoices(issued_at DESC);

CREATE TABLE IF NOT EXISTS invoice_items (
    id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    line_type TEXT NOT NULL DEFAULT 'service',
    title TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL DEFAULT 1,
    unit TEXT NOT NULL DEFAULT 'шт',
    price_cents INTEGER NOT NULL DEFAULT 0,
    sum_cents INTEGER NOT NULL DEFAULT 0,
    vat_label TEXT NOT NULL DEFAULT 'Без НДС',
    source_order_service_id BIGINT,
    source_order_part_id BIGINT,
    position INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id);

ALTER TABLE payments ADD COLUMN IF NOT EXISTS invoice_id BIGINT;
CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id);

INSERT INTO print_templates (name, template_type, html_content)
SELECT $tpl$Счёт на оплату (B2B)$tpl$, 'invoice_bill', $tpl$<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Счёт ##DOC_NUMBER##</title>
<style>
@page{size:A4;margin:12mm}
body{font-family:Arial,sans-serif;font-size:12px;color:#111;margin:0}
table{border-collapse:collapse;width:100%}
.bank td{border:1px solid #333;padding:4px 6px;vertical-align:top}
h1{font-size:16px;margin:16px 0 8px}
.meta{margin:8px 0;line-height:1.4}
.items th,.items td{border:1px solid #333;padding:4px 6px}
.items th{background:#f3f3f3}
.right{text-align:right}.center{text-align:center}
.sign{margin-top:28px;display:flex;justify-content:space-between;gap:24px}
.sign .box{width:45%;position:relative;min-height:70px}
.sign img.sig{max-height:48px;position:absolute;left:80px;top:0}
.sign img.stamp{max-height:90px;position:absolute;left:120px;top:-10px;opacity:.85}
.logo{max-height:56px;margin-bottom:8px}
.muted{color:#555}
</style></head><body>
##LOGO_HTML##
<table class="bank">
<tr>
<td width="55%"><div class="muted">Банк получателя</div><b>##SELLER_BANK_NAME##</b><br>БИК ##SELLER_BIK##<br>К/с ##SELLER_CORR_ACCOUNT##</td>
<td width="45%"><div class="muted">Сч. №</div><b>##SELLER_CHECKING_ACCOUNT##</b><br><div class="muted">Получатель</div>##SELLER_NAME##<br>ИНН ##SELLER_INN##</td>
</tr>
</table>
<h1>Счет на оплату № ##DOC_NUMBER## от ##DOC_DATE##</h1>
<div class="meta"><b>Поставщик:</b> ##SELLER_FULL##</div>
<div class="meta"><b>Покупатель:</b> ##BUYER_FULL##</div>
##DUE_HTML##
<table class="items">
<thead><tr>
<th>№</th><th>Товары (работы, услуги)</th><th>Кол-во</th><th>Ед.</th><th>НДС</th><th>Цена</th><th>Сумма</th>
</tr></thead>
<tbody>
<tr data-for="ITEMS">
<td class="center">##N##</td><td>##TITLE##</td><td class="right">##QTY##</td><td class="center">##UNIT##</td>
<td class="center">##VAT##</td><td class="right">##PRICE##</td><td class="right">##SUM##</td>
</tr>
</tbody>
</table>
<p class="right"><b>Итого к оплате: ##TOTAL##</b></p>
<p>Всего наименований ##ITEMS_COUNT## на сумму ##TOTAL## руб.<br><b>##TOTAL_WORDS##</b></p>
<div class="sign">
<div class="box">Руководитель _________________<br>##SELLER_DIRECTOR##
##SIGNATURE_HTML####STAMP_HTML##
</div>
<div class="box">Бухгалтер _________________<br>##SELLER_ACCOUNTANT##</div>
</div>
</body></html>
$tpl$
WHERE NOT EXISTS (SELECT 1 FROM print_templates WHERE template_type = 'invoice_bill');

INSERT INTO print_templates (name, template_type, html_content)
SELECT $tpl$Акт выполненных работ (B2B)$tpl$, 'invoice_act', $tpl$<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Акт ##DOC_NUMBER##</title>
<style>
@page{size:A4;margin:12mm}
body{font-family:Arial,sans-serif;font-size:12px;color:#111}
table{border-collapse:collapse;width:100%}
h1{font-size:16px;margin:12px 0}
.items th,.items td{border:1px solid #333;padding:4px 6px}
.items th{background:#f3f3f3}
.right{text-align:right}.center{text-align:center}
.meta{margin:6px 0;line-height:1.4}
.sign{margin-top:28px;display:flex;justify-content:space-between}
.sign .box{width:45%;position:relative;min-height:70px}
.sign img.sig{max-height:48px;position:absolute;left:90px;top:0}
.sign img.stamp{max-height:90px;position:absolute;left:130px;top:-10px;opacity:.85}
.logo{max-height:56px}
</style></head><body>
##LOGO_HTML##
<h1>Акт № ##DOC_NUMBER## от ##DOC_DATE##</h1>
<div class="meta"><b>Исполнитель:</b> ##SELLER_FULL##</div>
<div class="meta"><b>Заказчик:</b> ##BUYER_FULL##</div>
<table class="items">
<thead><tr><th>№</th><th>Услуга</th><th>Кол-во</th><th>Ед.</th><th>НДС</th><th>Цена</th><th>Сумма</th></tr></thead>
<tbody>
<tr data-for="ITEMS">
<td class="center">##N##</td><td>##TITLE##</td><td class="right">##QTY##</td><td class="center">##UNIT##</td>
<td class="center">##VAT##</td><td class="right">##PRICE##</td><td class="right">##SUM##</td>
</tr>
</tbody>
</table>
<p class="right"><b>Итого к оплате: ##TOTAL##</b></p>
<p>Всего оказано услуг на сумму ##TOTAL## руб.<br><b>##TOTAL_WORDS##</b></p>
<p>Вышеперечисленные услуги оказаны в полном объеме и в установленный срок. Заказчик не имеет претензий по качеству, срокам и объемам оказанных услуг.</p>
<div class="sign">
<div class="box">Исполнитель _________________<br>##SELLER_DIRECTOR##
##SIGNATURE_HTML####STAMP_HTML##
</div>
<div class="box">Заказчик _________________</div>
</div>
</body></html>
$tpl$
WHERE NOT EXISTS (SELECT 1 FROM print_templates WHERE template_type = 'invoice_act');

INSERT INTO print_templates (name, template_type, html_content)
SELECT $tpl$Товарная накладная (B2B)$tpl$, 'invoice_waybill', $tpl$<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Накладная ##DOC_NUMBER##</title>
<style>
@page{size:A4;margin:10mm}
body{font-family:Arial,sans-serif;font-size:11px;color:#111}
table{border-collapse:collapse;width:100%}
h1{font-size:15px;text-align:center;margin:10px 0}
.meta td{padding:2px 4px;vertical-align:top}
.items th,.items td{border:1px solid #333;padding:3px 4px}
.items th{background:#f3f3f3;font-size:10px}
.right{text-align:right}.center{text-align:center}
.sign{margin-top:20px}
.sign img.sig{max-height:40px;vertical-align:middle}
.sign img.stamp{max-height:80px;vertical-align:middle;opacity:.85}
.logo{max-height:48px}
</style></head><body>
##LOGO_HTML##
<table class="meta" style="width:100%;margin-bottom:8px">
<tr><td width="50%"><b>Номер документа</b> ##DOC_NUMBER##</td><td><b>Дата</b> ##DOC_DATE##</td></tr>
</table>
<h1>ТОВАРНАЯ НАКЛАДНАЯ</h1>
<table class="meta">
<tr><td width="160">Грузополучатель</td><td>##BUYER_FULL##</td></tr>
<tr><td>Поставщик</td><td>##SELLER_FULL##</td></tr>
<tr><td>Плательщик</td><td>##BUYER_FULL##</td></tr>
<tr><td>Основание</td><td>##BASIS##</td></tr>
</table>
<table class="items" style="margin-top:10px">
<thead><tr>
<th>№</th><th>Товар</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма без НДС</th><th>НДС</th><th>Сумма с НДС</th>
</tr></thead>
<tbody>
<tr data-for="ITEMS">
<td class="center">##N##</td><td>##TITLE##</td><td class="center">##UNIT##</td><td class="right">##QTY##</td>
<td class="right">##PRICE##</td><td class="right">##SUM##</td><td class="center">##VAT##</td><td class="right">##SUM##</td>
</tr>
</tbody>
</table>
<p class="right"><b>Всего отпущено на сумму ##TOTAL_WORDS##</b> (##TOTAL##)</p>
<div class="sign">
<p>Отпуск груза разрешил _________________ ##SELLER_DIRECTOR## ##SIGNATURE_HTML## ##STAMP_HTML##</p>
<p>Главный (старший) бухгалтер _________________ ##SELLER_ACCOUNTANT##</p>
<p>Груз получил грузополучатель _________________</p>
</div>
</body></html>
$tpl$
WHERE NOT EXISTS (SELECT 1 FROM print_templates WHERE template_type = 'invoice_waybill');

INSERT INTO permissions (name, description)
VALUES
 ('view_invoices', 'Просмотр раздела Счета'),
 ('manage_invoices', 'Создание и редактирование счетов'),
 ('mark_invoice_paid', 'Отметка счетов оплаченными')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT r.role, p.id
FROM (VALUES ('admin'), ('manager')) AS r(role)
CROSS JOIN permissions p
WHERE p.name IN ('view_invoices', 'manage_invoices', 'mark_invoice_paid')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role, permission_id)
SELECT 'viewer', p.id FROM permissions p
WHERE p.name = 'view_invoices'
ON CONFLICT DO NOTHING;

-- 014: привязка позиций счёта к каталогу + shop_sale при оплате без заявки
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS catalog_part_id BIGINT;
ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS catalog_service_id BIGINT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS shop_sale_id BIGINT;
CREATE INDEX IF NOT EXISTS idx_invoices_shop_sale_id ON invoices(shop_sale_id);


-- Post-bootstrap schema: postgres migrations 015-016 (idempotent)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS estimated_cost TEXT DEFAULT '0';

UPDATE print_templates
SET html_content = regexp_replace(
        html_content,
        '<tr>\s*<td><strong>Внешний вид</strong></td>\s*<td>##bc1ae9b1-7b8b-4da6-add5-26982865629e##</td>\s*<td rowspan="3">&nbsp;</td>\s*</tr>\s*<tr>\s*<td><strong>Комплектация</strong></td>\s*<td>##dfd7aa33-fd89-462a-bbbc-39c1550415da##</td>\s*</tr>',
        '<tr><td><strong>Внешний вид / комплектация</strong></td><td>##bc1ae9b1-7b8b-4da6-add5-26982865629e##</td><td rowspan="2">&nbsp;</td></tr>',
        'g'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE template_type = 'customer'
  AND html_content ~ 'Комплектация</strong>'
  AND html_content !~ 'Внешний вид / комплектация';

UPDATE print_templates
SET html_content = regexp_replace(
        html_content,
        '(<p><strong>)Предоплата:\s*##TOTAL_PAID##',
        E'<p><strong>Предварительная стоимость: ##ESTIMATED_COST## ##CURRENCY##</strong></p>\n\\1Предоплата: ##TOTAL_PAID##',
        'g'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE template_type = 'customer'
  AND html_content ~ 'Предоплата:\s*##TOTAL_PAID##'
  AND html_content !~ 'Предварительная стоимость:\s*##ESTIMATED_COST##';

-- Post-bootstrap schema: postgres migration 017 (idempotent)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS diagnostics TEXT;

CREATE TABLE IF NOT EXISTS order_client_files (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    created_by INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_order_client_files_order_id ON order_client_files(order_id);

-- Post-bootstrap schema: postgres migration 018 (idempotent)
CREATE TABLE IF NOT EXISTS order_diagnostics_history (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_by INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_order_diagnostics_history_order_id
    ON order_diagnostics_history(order_id);

-- Post-bootstrap schema: postgres migration 019 (idempotent)
ALTER TABLE order_models ADD COLUMN IF NOT EXISTS device_type_id BIGINT;
ALTER TABLE order_models ADD COLUMN IF NOT EXISTS device_brand_id BIGINT;
CREATE INDEX IF NOT EXISTS idx_order_models_type_brand
    ON order_models(device_type_id, device_brand_id);

-- Post-bootstrap schema: postgres migration 020 (idempotent)
UPDATE print_templates
SET html_content = replace(html_content, E'\\n', E'\n'),
    updated_at = CURRENT_TIMESTAMP
WHERE position(E'\\n' in html_content) > 0;

-- Post-bootstrap schema: postgres migration 021 (idempotent)
CREATE TABLE IF NOT EXISTS diagnostics_templates (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    device_type_id BIGINT REFERENCES device_types(id) ON DELETE SET NULL,
    device_brand_id BIGINT REFERENCES device_brands(id) ON DELETE SET NULL,
    model_id BIGINT REFERENCES order_models(id) ON DELETE SET NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BIGINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_diagnostics_templates_device
    ON diagnostics_templates(device_type_id, device_brand_id, model_id);
CREATE INDEX IF NOT EXISTS idx_diagnostics_templates_sort
    ON diagnostics_templates(sort_order, id);

-- Post-bootstrap schema: postgres migration 022 (idempotent)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'diagnostics_templates'
          AND column_name = 'is_active'
          AND data_type = 'boolean'
    ) THEN
        ALTER TABLE diagnostics_templates
            ALTER COLUMN is_active DROP DEFAULT;
        ALTER TABLE diagnostics_templates
            ALTER COLUMN is_active TYPE BIGINT
            USING CASE WHEN is_active THEN 1 ELSE 0 END;
        ALTER TABLE diagnostics_templates
            ALTER COLUMN is_active SET DEFAULT 1,
            ALTER COLUMN is_active SET NOT NULL;
    END IF;
END $$;

-- Post-bootstrap schema: postgres migration 023 (idempotent)
INSERT INTO diagnostics_templates (
    name, body, device_type_id, device_brand_id, model_id, sort_order, is_active
)
SELECT v.name, v.body, NULL, NULL, NULL, v.sort_order, 1
FROM (
    VALUES
    (
        'PS5 — чистка с заменой жидкого металла',
        'Чистка системы охлаждения, замена жидкого металла на кристалле, чистка от пыли, продувка, сборка, тестирование. Заключение мастера: перегрева нет, работоспособность восстановлена.',
        10
    ),
    (
        'Игровая приставка — чистка от пыли',
        'Разборка, чистка радиаторов и вентилятора от пыли, продувка, сборка, тестирование запуска. Заключение мастера: перегрева нет, приставка работает штатно.',
        20
    ),
    (
        'Ноутбук — чистка системы охлаждения',
        'Разборка, чистка радиаторов и вентилятора от пыли, замена термоинтерфейса, сборка, стресс-тест. Заключение мастера: температуры в норме, шумы снижены.',
        30
    ),
    (
        'Системный блок — чистка от пыли',
        'Чистка корпуса, радиаторов и вентиляторов от пыли, проверка термопасты, продувка, тестирование. Заключение мастера: охлаждение восстановлено, посторонних шумов нет.',
        40
    ),
    (
        'Моноблок — чистка системы охлаждения',
        'Чистка системы охлаждения, замена термоинтерфейса, сборка, тестирование. Заключение мастера: температуры в норме, работоспособность восстановлена.',
        50
    ),
    (
        'Видеокарта — чистка и замена термоинтерфейса',
        'Разборка, чистка от пыли, замена термопасты и термопрокладок, тест в нагрузке. Заключение мастера: артефактов нет, температуры в норме.',
        60
    ),
    (
        'МФУ / принтер — ремонт и чистка тракта',
        'Диагностика, чистка тракта подачи и узла печати, проверка роликов и датчиков, тестовая печать. Заключение мастера: печать стабильная, замятий нет.',
        70
    ),
    (
        'Смартфон — не включается',
        'Диагностика питания, проверка разъёма зарядки и кнопки включения, тест после работ. Заключение мастера: устройство включается, зарядка и основные функции в норме.',
        80
    ),
    (
        'Смартфон — после попадания влаги',
        'Разборка, осмотр платы, чистка от окислов, сушка, сборка, тестирование. Заключение мастера: следов замыкания нет, устройство работает штатно.',
        90
    ),
    (
        'Планшет — диагностика и ремонт',
        'Проверка зарядки, экрана, кнопок и беспроводных модулей, тест после работ. Заключение мастера: функции восстановлены, зарядка стабильная.',
        100
    ),
    (
        'Телевизор — нет изображения',
        'Диагностика подсветки, платы питания и главной платы, тест изображения и звука. Заключение мастера: изображение стабильное, звук в норме.',
        110
    ),
    (
        'Монитор — нет изображения / нет подсветки',
        'Диагностика блока питания и подсветки, проверка матрицы, тест после ремонта. Заключение мастера: изображение есть, подсветка равномерная.',
        120
    ),
    (
        'Роутер — нет интернета / обрывы',
        'Диагностика питания и портов, сброс и настройка, проверка Wi-Fi и WAN. Заключение мастера: сеть поднимается, обрывов нет.',
        130
    ),
    (
        'Наушники / TWS — зарядка и звук',
        'Диагностика зарядки кейса и наушников, чистка контактов, проверка микрофона и звука. Заключение мастера: зарядка и звук в норме.',
        140
    ),
    (
        'Электросамокат / гироскутер — диагностика',
        'Проверка контроллера, батареи, зарядки и датчиков, тест хода. Заключение мастера: техника набирает ход, зарядка в норме.',
        150
    ),
    (
        'Кофемашина — чистка и ремонт',
        'Диагностика, декальцинация / чистка гидросистемы, проверка помпы и нагрева. Заключение мастера: набор воды и нагрев в норме.',
        160
    ),
    (
        'Фотоаппарат / камера — диагностика',
        'Проверка включения, объектива, затвора и карты памяти, тест съёмки. Заключение мастера: съёмка и запись работают штатно.',
        170
    )
) AS v(name, body, sort_order)
WHERE NOT EXISTS (
    SELECT 1 FROM diagnostics_templates t WHERE t.name = v.name
);

-- Post-bootstrap schema: postgres migration 024 (idempotent)
CREATE TABLE IF NOT EXISTS order_customer_emails (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    customer_id BIGINT REFERENCES customers(id) ON DELETE SET NULL,
    recipient_email TEXT NOT NULL,
    template_type TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    status_name TEXT,
    success BIGINT NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_order_customer_emails_order
    ON order_customer_emails(order_id, created_at DESC);

-- Post-bootstrap schema: postgres migration 025 (idempotent)
ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS phone_prefix TEXT;
ALTER TABLE general_settings ADD COLUMN IF NOT EXISTS currency_symbol TEXT;
UPDATE general_settings
SET phone_prefix = '7'
WHERE phone_prefix IS NULL OR btrim(phone_prefix) = '';
UPDATE general_settings
SET currency_symbol = '₽'
WHERE currency_symbol IS NULL OR btrim(currency_symbol) = '';


--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.2

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: files; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.files (
    file_id integer NOT NULL,
    user_id integer NOT NULL,
    original_filename character varying(255) NOT NULL,
    stored_filename_uuid uuid NOT NULL,
    storage_path character varying(512) NOT NULL,
    mime_type character varying(100) NOT NULL,
    file_size_bytes bigint NOT NULL,
    encryption_algorithm character varying(50) NOT NULL,
    encryption_iv character varying(32) NOT NULL,
    encryption_auth_tag character varying(32),
    uploaded_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_accessed_at timestamp with time zone,
    deleted_at timestamp with time zone
);


ALTER TABLE public.files OWNER TO postgres;

--
-- Name: files_file_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.files_file_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.files_file_id_seq OWNER TO postgres;

--
-- Name: files_file_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.files_file_id_seq OWNED BY public.files.file_id;


--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.refresh_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone
);


ALTER TABLE public.refresh_tokens OWNER TO postgres;

--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.refresh_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.refresh_tokens_id_seq OWNER TO postgres;

--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.refresh_tokens_id_seq OWNED BY public.refresh_tokens.id;


--
-- Name: two_factor_temp_codes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.two_factor_temp_codes (
    id integer NOT NULL,
    user_id integer,
    pending_email character varying(255),
    pending_username character varying(50),
    pending_password_hash character varying(255),
    code character varying(6) NOT NULL,
    purpose character varying(50) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone
);


ALTER TABLE public.two_factor_temp_codes OWNER TO postgres;

--
-- Name: two_factor_temp_codes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.two_factor_temp_codes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.two_factor_temp_codes_id_seq OWNER TO postgres;

--
-- Name: two_factor_temp_codes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.two_factor_temp_codes_id_seq OWNED BY public.two_factor_temp_codes.id;


--
-- Name: user_backup_codes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_backup_codes (
    backup_code_id integer NOT NULL,
    user_id integer NOT NULL,
    code_hash character varying(255) NOT NULL,
    is_used boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    used_at timestamp with time zone
);


ALTER TABLE public.user_backup_codes OWNER TO postgres;

--
-- Name: user_backup_codes_backup_code_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_backup_codes_backup_code_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_backup_codes_backup_code_id_seq OWNER TO postgres;

--
-- Name: user_backup_codes_backup_code_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_backup_codes_backup_code_id_seq OWNED BY public.user_backup_codes.backup_code_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_user_id_seq OWNER TO postgres;

--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: files file_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.files ALTER COLUMN file_id SET DEFAULT nextval('public.files_file_id_seq'::regclass);


--
-- Name: refresh_tokens id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.refresh_tokens ALTER COLUMN id SET DEFAULT nextval('public.refresh_tokens_id_seq'::regclass);


--
-- Name: two_factor_temp_codes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.two_factor_temp_codes ALTER COLUMN id SET DEFAULT nextval('public.two_factor_temp_codes_id_seq'::regclass);


--
-- Name: user_backup_codes backup_code_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_backup_codes ALTER COLUMN backup_code_id SET DEFAULT nextval('public.user_backup_codes_backup_code_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Data for Name: files; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.files (file_id, user_id, original_filename, stored_filename_uuid, storage_path, mime_type, file_size_bytes, encryption_algorithm, encryption_iv, encryption_auth_tag, uploaded_at, last_accessed_at, deleted_at) FROM stdin;
\.


--
-- Data for Name: refresh_tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.refresh_tokens (id, user_id, token, expires_at, created_at) FROM stdin;
2	1	Sa42-P8kTPpSxTcq9j8srMhneHTF3MjGrRFmxBjqgVnynqMZYfmvRi2Ra-sogJZC35qTSYEKDWmYIm58Uc9AAQ	2025-06-08 13:42:09.043462+07	2025-06-01 13:42:09.044183+07
\.


--
-- Data for Name: two_factor_temp_codes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.two_factor_temp_codes (id, user_id, pending_email, pending_username, pending_password_hash, code, purpose, expires_at, created_at) FROM stdin;
1	\N	ttykah1337@gamil.com	string	$2b$12$7ZjjbWFNNUtMVefs/9VrNeIWy.qcxtL5AOSOkCXvYGpcgfFsEl19q	149280	registration_verify	2025-06-01 12:56:28.322555+07	2025-06-01 12:41:28.442182+07
\.


--
-- Data for Name: user_backup_codes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_backup_codes (backup_code_id, user_id, code_hash, is_used, created_at, used_at) FROM stdin;
1	1	$2b$12$geDUd7ectKgfQCaGWO62C.pgj99SWh9.82fKE9k0rI2WOL6LWsWnW	f	2025-06-01 12:43:05.01538+07	\N
2	1	$2b$12$EORH0mriva/IG.gsHszByef7EaQfrPBR0MFkAgQS2/z3EgwoUxgCi	f	2025-06-01 12:43:05.015384+07	\N
3	1	$2b$12$H8/BH3E/wkqgFd0m0LrKbuZfinbhWJLUrdcm3Zt3Qfymn5IEpsivq	f	2025-06-01 12:43:05.015384+07	\N
4	1	$2b$12$B4RoiccfSF2LiTrCJr8tR.s2MoPJVEw.rbBoxZ.K9mxFOQ1kbf.aO	f	2025-06-01 12:43:05.015385+07	\N
5	1	$2b$12$ta6cv4BzCGfA9SopHfxLXel40ArdXt.EGtJQBd2Y8YBQIbs.Opblu	f	2025-06-01 12:43:05.015386+07	\N
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (user_id, username, email, password_hash, created_at, updated_at) FROM stdin;
1	string	ttykah1337@gmail.com	$2b$12$3Gvv71V9qcP0P49DXwnT4u2MehI58C80i1LM7bq3UjuwqOFdaiY8q	2025-06-01 12:43:03.902646+07	2025-06-01 12:43:03.902651+07
\.


--
-- Name: files_file_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.files_file_id_seq', 1, false);


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.refresh_tokens_id_seq', 2, true);


--
-- Name: two_factor_temp_codes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.two_factor_temp_codes_id_seq', 7, true);


--
-- Name: user_backup_codes_backup_code_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_backup_codes_backup_code_id_seq', 5, true);


--
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_user_id_seq', 1, true);


--
-- Name: files files_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_pkey PRIMARY KEY (file_id);


--
-- Name: files files_stored_filename_uuid_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_stored_filename_uuid_key UNIQUE (stored_filename_uuid);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: two_factor_temp_codes two_factor_temp_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.two_factor_temp_codes
    ADD CONSTRAINT two_factor_temp_codes_pkey PRIMARY KEY (id);


--
-- Name: user_backup_codes user_backup_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_backup_codes
    ADD CONSTRAINT user_backup_codes_pkey PRIMARY KEY (backup_code_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_files_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_files_user_id ON public.files USING btree (user_id);


--
-- Name: idx_user_backup_codes_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_backup_codes_user_id ON public.user_backup_codes USING btree (user_id);


--
-- Name: ix_refresh_tokens_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_refresh_tokens_id ON public.refresh_tokens USING btree (id);


--
-- Name: ix_refresh_tokens_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_refresh_tokens_token ON public.refresh_tokens USING btree (token);


--
-- Name: ix_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_refresh_tokens_user_id ON public.refresh_tokens USING btree (user_id);


--
-- Name: ix_two_factor_temp_codes_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_two_factor_temp_codes_id ON public.two_factor_temp_codes USING btree (id);


--
-- Name: ix_two_factor_temp_codes_pending_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_two_factor_temp_codes_pending_email ON public.two_factor_temp_codes USING btree (pending_email);


--
-- Name: ix_two_factor_temp_codes_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_two_factor_temp_codes_user_id ON public.two_factor_temp_codes USING btree (user_id);


--
-- Name: files files_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: refresh_tokens refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: two_factor_temp_codes two_factor_temp_codes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.two_factor_temp_codes
    ADD CONSTRAINT two_factor_temp_codes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: user_backup_codes user_backup_codes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_backup_codes
    ADD CONSTRAINT user_backup_codes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


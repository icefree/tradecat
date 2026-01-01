--
-- PostgreSQL database dump
--

\restrict x54qImlHyLxftfmFHeagxv6dIMPpw2E07hLUDHfL0e3gXxutltPw0cSCX3GQ2sF

-- Dumped from database version 16.11 (Ubuntu 16.11-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.11 (Ubuntu 16.11-0ubuntu0.24.04.1)

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
-- Name: timescaledb; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS timescaledb WITH SCHEMA public;


--
-- Name: EXTENSION timescaledb; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION timescaledb IS 'Enables scalable inserts and complex queries for time-series data (Community Edition)';


--
-- Name: agg; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA agg;


--
-- Name: indicators; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA indicators;


--
-- Name: raw; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA raw;


--
-- Name: reference; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA reference;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: kline_1m; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.kline_1m (
    exchange text NOT NULL,
    symbol text NOT NULL,
    open_time timestamp with time zone NOT NULL,
    close_time timestamp with time zone,
    open numeric(38,12) NOT NULL,
    high numeric(38,12) NOT NULL,
    low numeric(38,12) NOT NULL,
    close numeric(38,12) NOT NULL,
    volume numeric(38,12) NOT NULL,
    quote_volume numeric(38,12),
    trades bigint,
    taker_buy_volume numeric(38,12),
    taker_buy_quote_volume numeric(38,12),
    is_closed boolean DEFAULT false NOT NULL,
    source text DEFAULT 'binance_ws'::text NOT NULL,
    ingested_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: kline_15m_mv; Type: MATERIALIZED VIEW; Schema: agg; Owner: -
--

CREATE MATERIALIZED VIEW agg.kline_15m_mv AS
 SELECT exchange,
    symbol,
    public.time_bucket('00:15:00'::interval, open_time) AS open_time,
    public.first(open, open_time) AS open,
    max(high) AS high,
    min(low) AS low,
    public.last(close, open_time) AS close,
    sum(volume) AS volume,
    sum(quote_volume) AS quote_volume,
    sum(trades) AS trades
   FROM raw.kline_1m
  WHERE (is_closed = true)
  GROUP BY exchange, symbol, (public.time_bucket('00:15:00'::interval, open_time))
  WITH NO DATA;


--
-- Name: kline_1d_mv; Type: MATERIALIZED VIEW; Schema: agg; Owner: -
--

CREATE MATERIALIZED VIEW agg.kline_1d_mv AS
 SELECT exchange,
    symbol,
    public.time_bucket('1 day'::interval, open_time) AS open_time,
    public.first(open, open_time) AS open,
    max(high) AS high,
    min(low) AS low,
    public.last(close, open_time) AS close,
    sum(volume) AS volume,
    sum(quote_volume) AS quote_volume,
    sum(trades) AS trades
   FROM raw.kline_1m
  WHERE (is_closed = true)
  GROUP BY exchange, symbol, (public.time_bucket('1 day'::interval, open_time))
  WITH NO DATA;


--
-- Name: kline_1h_mv; Type: MATERIALIZED VIEW; Schema: agg; Owner: -
--

CREATE MATERIALIZED VIEW agg.kline_1h_mv AS
 SELECT exchange,
    symbol,
    public.time_bucket('01:00:00'::interval, open_time) AS open_time,
    public.first(open, open_time) AS open,
    max(high) AS high,
    min(low) AS low,
    public.last(close, open_time) AS close,
    sum(volume) AS volume,
    sum(quote_volume) AS quote_volume,
    sum(trades) AS trades
   FROM raw.kline_1m
  WHERE (is_closed = true)
  GROUP BY exchange, symbol, (public.time_bucket('01:00:00'::interval, open_time))
  WITH NO DATA;


--
-- Name: kline_1w_mv; Type: MATERIALIZED VIEW; Schema: agg; Owner: -
--

CREATE MATERIALIZED VIEW agg.kline_1w_mv AS
 SELECT exchange,
    symbol,
    public.time_bucket('7 days'::interval, open_time) AS open_time,
    public.first(open, open_time) AS open,
    max(high) AS high,
    min(low) AS low,
    public.last(close, open_time) AS close,
    sum(volume) AS volume,
    sum(quote_volume) AS quote_volume,
    sum(trades) AS trades
   FROM raw.kline_1m
  WHERE (is_closed = true)
  GROUP BY exchange, symbol, (public.time_bucket('7 days'::interval, open_time))
  WITH NO DATA;


--
-- Name: kline_4h_mv; Type: MATERIALIZED VIEW; Schema: agg; Owner: -
--

CREATE MATERIALIZED VIEW agg.kline_4h_mv AS
 SELECT exchange,
    symbol,
    public.time_bucket('04:00:00'::interval, open_time) AS open_time,
    public.first(open, open_time) AS open,
    max(high) AS high,
    min(low) AS low,
    public.last(close, open_time) AS close,
    sum(volume) AS volume,
    sum(quote_volume) AS quote_volume,
    sum(trades) AS trades
   FROM raw.kline_1m
  WHERE (is_closed = true)
  GROUP BY exchange, symbol, (public.time_bucket('04:00:00'::interval, open_time))
  WITH NO DATA;


--
-- Name: kline_5m_mv; Type: MATERIALIZED VIEW; Schema: agg; Owner: -
--

CREATE MATERIALIZED VIEW agg.kline_5m_mv AS
 SELECT exchange,
    symbol,
    public.time_bucket('00:05:00'::interval, open_time) AS open_time,
    public.first(open, open_time) AS open,
    max(high) AS high,
    min(low) AS low,
    public.last(close, open_time) AS close,
    sum(volume) AS volume,
    sum(quote_volume) AS quote_volume,
    sum(trades) AS trades
   FROM raw.kline_1m
  WHERE (is_closed = true)
  GROUP BY exchange, symbol, (public.time_bucket('00:05:00'::interval, open_time))
  WITH NO DATA;


--
-- Name: futures_metadata; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.futures_metadata (
    exchange text DEFAULT 'binanceusdm'::text NOT NULL,
    symbol text NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    "sumOpenInterest" numeric,
    "sumOpenInterestValue" numeric,
    "CMCCirculatingSupply" numeric,
    "longShortRatio" numeric,
    "longAccount" numeric,
    "shortAccount" numeric,
    "topLongShortRatio" numeric,
    "topLongAccount" numeric,
    "topShortAccount" numeric,
    "buySellRatio" numeric,
    "buyVol" numeric,
    "sellVol" numeric,
    "markPrice" numeric,
    "indexPrice" numeric,
    "estimatedSettlePrice" numeric,
    "lastFundingRate" numeric,
    "interestRate" numeric,
    "nextFundingTime" bigint,
    "time" bigint,
    source text DEFAULT 'binance_rest'::text NOT NULL,
    is_closed boolean DEFAULT true NOT NULL,
    ingested_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: meta_15m_mv; Type: MATERIALIZED VIEW; Schema: agg; Owner: -
--

CREATE MATERIALIZED VIEW agg.meta_15m_mv AS
 SELECT exchange,
    symbol,
    public.time_bucket('00:15:00'::interval, "timestamp") AS "timestamp",
    avg("sumOpenInterest") AS "avgSumOpenInterest",
    avg("sumOpenInterestValue") AS "avgSumOpenInterestValue",
    avg("longShortRatio") AS "avgLongShortRatio",
    avg("topLongShortRatio") AS "avgTopLongShortRatio",
    avg("buySellRatio") AS "avgBuySellRatio",
    avg("lastFundingRate") AS "avgLastFundingRate",
    public.last("sumOpenInterest", "timestamp") AS "lastSumOpenInterest",
    public.last("markPrice", "timestamp") AS "lastMarkPrice"
   FROM raw.futures_metadata
  WHERE (is_closed = true)
  GROUP BY exchange, symbol, (public.time_bucket('00:15:00'::interval, "timestamp"))
  WITH NO DATA;


--
-- Name: meta_1d_mv; Type: MATERIALIZED VIEW; Schema: agg; Owner: -
--

CREATE MATERIALIZED VIEW agg.meta_1d_mv AS
 SELECT exchange,
    symbol,
    public.time_bucket('1 day'::interval, "timestamp") AS "timestamp",
    avg("sumOpenInterest") AS "avgSumOpenInterest",
    avg("sumOpenInterestValue") AS "avgSumOpenInterestValue",
    avg("longShortRatio") AS "avgLongShortRatio",
    avg("topLongShortRatio") AS "avgTopLongShortRatio",
    avg("buySellRatio") AS "avgBuySellRatio",
    avg("lastFundingRate") AS "avgLastFundingRate",
    max("sumOpenInterest") AS "maxSumOpenInterest",
    min("sumOpenInterest") AS "minSumOpenInterest",
    public.last("sumOpenInterest", "timestamp") AS "lastSumOpenInterest",
    public.last("markPrice", "timestamp") AS "lastMarkPrice"
   FROM raw.futures_metadata
  WHERE (is_closed = true)
  GROUP BY exchange, symbol, (public.time_bucket('1 day'::interval, "timestamp"))
  WITH NO DATA;


--
-- Name: meta_1h_mv; Type: MATERIALIZED VIEW; Schema: agg; Owner: -
--

CREATE MATERIALIZED VIEW agg.meta_1h_mv AS
 SELECT exchange,
    symbol,
    public.time_bucket('01:00:00'::interval, "timestamp") AS "timestamp",
    avg("sumOpenInterest") AS "avgSumOpenInterest",
    avg("sumOpenInterestValue") AS "avgSumOpenInterestValue",
    avg("longShortRatio") AS "avgLongShortRatio",
    avg("topLongShortRatio") AS "avgTopLongShortRatio",
    avg("buySellRatio") AS "avgBuySellRatio",
    avg("lastFundingRate") AS "avgLastFundingRate",
    public.last("sumOpenInterest", "timestamp") AS "lastSumOpenInterest",
    public.last("markPrice", "timestamp") AS "lastMarkPrice"
   FROM raw.futures_metadata
  WHERE (is_closed = true)
  GROUP BY exchange, symbol, (public.time_bucket('01:00:00'::interval, "timestamp"))
  WITH NO DATA;


--
-- Name: meta_4h_mv; Type: MATERIALIZED VIEW; Schema: agg; Owner: -
--

CREATE MATERIALIZED VIEW agg.meta_4h_mv AS
 SELECT exchange,
    symbol,
    public.time_bucket('04:00:00'::interval, "timestamp") AS "timestamp",
    avg("sumOpenInterest") AS "avgSumOpenInterest",
    avg("sumOpenInterestValue") AS "avgSumOpenInterestValue",
    avg("longShortRatio") AS "avgLongShortRatio",
    avg("topLongShortRatio") AS "avgTopLongShortRatio",
    avg("buySellRatio") AS "avgBuySellRatio",
    avg("lastFundingRate") AS "avgLastFundingRate",
    max("sumOpenInterest") AS "maxSumOpenInterest",
    min("sumOpenInterest") AS "minSumOpenInterest",
    public.last("sumOpenInterest", "timestamp") AS "lastSumOpenInterest",
    public.last("markPrice", "timestamp") AS "lastMarkPrice"
   FROM raw.futures_metadata
  WHERE (is_closed = true)
  GROUP BY exchange, symbol, (public.time_bucket('04:00:00'::interval, "timestamp"))
  WITH NO DATA;


--
-- Name: indicator_data; Type: TABLE; Schema: indicators; Owner: -
--

CREATE TABLE indicators.indicator_data (
    exchange text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    indicator text NOT NULL,
    ts bigint NOT NULL,
    data_json jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: equity_metadata; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.equity_metadata (
    exchange text NOT NULL,
    symbol text NOT NULL,
    ts timestamp with time zone NOT NULL,
    bid numeric,
    ask numeric,
    last_price numeric,
    volume numeric,
    meta_json jsonb
);


--
-- Name: forex_metadata; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.forex_metadata (
    exchange text NOT NULL,
    symbol text NOT NULL,
    ts timestamp with time zone NOT NULL,
    bid numeric,
    ask numeric,
    mid numeric,
    meta_json jsonb
);


--
-- Name: exchanges; Type: TABLE; Schema: reference; Owner: -
--

CREATE TABLE reference.exchanges (
    exchange_id integer NOT NULL,
    exchange_code text NOT NULL,
    exchange_name text,
    market text NOT NULL,
    country text,
    timezone text,
    is_active boolean DEFAULT true,
    meta_json jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: exchanges_exchange_id_seq; Type: SEQUENCE; Schema: reference; Owner: -
--

CREATE SEQUENCE reference.exchanges_exchange_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exchanges_exchange_id_seq; Type: SEQUENCE OWNED BY; Schema: reference; Owner: -
--

ALTER SEQUENCE reference.exchanges_exchange_id_seq OWNED BY reference.exchanges.exchange_id;


--
-- Name: instruments; Type: TABLE; Schema: reference; Owner: -
--

CREATE TABLE reference.instruments (
    instrument_id bigint NOT NULL,
    market text NOT NULL,
    exchange text NOT NULL,
    symbol text NOT NULL,
    base_currency text,
    quote_currency text,
    instrument_type text NOT NULL,
    contract_size numeric,
    tick_size numeric,
    min_qty numeric,
    is_active boolean DEFAULT true,
    meta_json jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: instruments_instrument_id_seq; Type: SEQUENCE; Schema: reference; Owner: -
--

CREATE SEQUENCE reference.instruments_instrument_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instruments_instrument_id_seq; Type: SEQUENCE OWNED BY; Schema: reference; Owner: -
--

ALTER SEQUENCE reference.instruments_instrument_id_seq OWNED BY reference.instruments.instrument_id;


--
-- Name: trading_hours; Type: TABLE; Schema: reference; Owner: -
--

CREATE TABLE reference.trading_hours (
    id integer NOT NULL,
    exchange text NOT NULL,
    day_of_week smallint NOT NULL,
    open_time time without time zone,
    close_time time without time zone,
    is_trading_day boolean DEFAULT true,
    meta_json jsonb
);


--
-- Name: trading_hours_id_seq; Type: SEQUENCE; Schema: reference; Owner: -
--

CREATE SEQUENCE reference.trading_hours_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: trading_hours_id_seq; Type: SEQUENCE OWNED BY; Schema: reference; Owner: -
--

ALTER SEQUENCE reference.trading_hours_id_seq OWNED BY reference.trading_hours.id;


--
-- Name: exchanges exchange_id; Type: DEFAULT; Schema: reference; Owner: -
--

ALTER TABLE ONLY reference.exchanges ALTER COLUMN exchange_id SET DEFAULT nextval('reference.exchanges_exchange_id_seq'::regclass);


--
-- Name: instruments instrument_id; Type: DEFAULT; Schema: reference; Owner: -
--

ALTER TABLE ONLY reference.instruments ALTER COLUMN instrument_id SET DEFAULT nextval('reference.instruments_instrument_id_seq'::regclass);


--
-- Name: trading_hours id; Type: DEFAULT; Schema: reference; Owner: -
--

ALTER TABLE ONLY reference.trading_hours ALTER COLUMN id SET DEFAULT nextval('reference.trading_hours_id_seq'::regclass);


--
-- Name: indicator_data indicator_data_pkey; Type: CONSTRAINT; Schema: indicators; Owner: -
--

ALTER TABLE ONLY indicators.indicator_data
    ADD CONSTRAINT indicator_data_pkey PRIMARY KEY (exchange, symbol, timeframe, indicator, ts);


--
-- Name: equity_metadata equity_metadata_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.equity_metadata
    ADD CONSTRAINT equity_metadata_pkey PRIMARY KEY (exchange, symbol, ts);


--
-- Name: forex_metadata forex_metadata_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.forex_metadata
    ADD CONSTRAINT forex_metadata_pkey PRIMARY KEY (exchange, symbol, ts);


--
-- Name: futures_metadata futures_metadata_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.futures_metadata
    ADD CONSTRAINT futures_metadata_pkey PRIMARY KEY (exchange, symbol, "timestamp");


--
-- Name: kline_1m kline_1m_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.kline_1m
    ADD CONSTRAINT kline_1m_pkey PRIMARY KEY (exchange, symbol, open_time);


--
-- Name: exchanges exchanges_exchange_code_key; Type: CONSTRAINT; Schema: reference; Owner: -
--

ALTER TABLE ONLY reference.exchanges
    ADD CONSTRAINT exchanges_exchange_code_key UNIQUE (exchange_code);


--
-- Name: exchanges exchanges_pkey; Type: CONSTRAINT; Schema: reference; Owner: -
--

ALTER TABLE ONLY reference.exchanges
    ADD CONSTRAINT exchanges_pkey PRIMARY KEY (exchange_id);


--
-- Name: instruments instruments_market_exchange_symbol_key; Type: CONSTRAINT; Schema: reference; Owner: -
--

ALTER TABLE ONLY reference.instruments
    ADD CONSTRAINT instruments_market_exchange_symbol_key UNIQUE (market, exchange, symbol);


--
-- Name: instruments instruments_pkey; Type: CONSTRAINT; Schema: reference; Owner: -
--

ALTER TABLE ONLY reference.instruments
    ADD CONSTRAINT instruments_pkey PRIMARY KEY (instrument_id);


--
-- Name: trading_hours trading_hours_pkey; Type: CONSTRAINT; Schema: reference; Owner: -
--

ALTER TABLE ONLY reference.trading_hours
    ADD CONSTRAINT trading_hours_pkey PRIMARY KEY (id);


--
-- Name: idx_kline_15m_pk; Type: INDEX; Schema: agg; Owner: -
--

CREATE UNIQUE INDEX idx_kline_15m_pk ON agg.kline_15m_mv USING btree (exchange, symbol, open_time);


--
-- Name: idx_kline_1d_pk; Type: INDEX; Schema: agg; Owner: -
--

CREATE UNIQUE INDEX idx_kline_1d_pk ON agg.kline_1d_mv USING btree (exchange, symbol, open_time);


--
-- Name: idx_kline_1h_pk; Type: INDEX; Schema: agg; Owner: -
--

CREATE UNIQUE INDEX idx_kline_1h_pk ON agg.kline_1h_mv USING btree (exchange, symbol, open_time);


--
-- Name: idx_kline_1w_pk; Type: INDEX; Schema: agg; Owner: -
--

CREATE UNIQUE INDEX idx_kline_1w_pk ON agg.kline_1w_mv USING btree (exchange, symbol, open_time);


--
-- Name: idx_kline_4h_pk; Type: INDEX; Schema: agg; Owner: -
--

CREATE UNIQUE INDEX idx_kline_4h_pk ON agg.kline_4h_mv USING btree (exchange, symbol, open_time);


--
-- Name: idx_kline_5m_pk; Type: INDEX; Schema: agg; Owner: -
--

CREATE UNIQUE INDEX idx_kline_5m_pk ON agg.kline_5m_mv USING btree (exchange, symbol, open_time);


--
-- Name: idx_meta_15m_pk; Type: INDEX; Schema: agg; Owner: -
--

CREATE UNIQUE INDEX idx_meta_15m_pk ON agg.meta_15m_mv USING btree (exchange, symbol, "timestamp");


--
-- Name: idx_meta_1d_pk; Type: INDEX; Schema: agg; Owner: -
--

CREATE UNIQUE INDEX idx_meta_1d_pk ON agg.meta_1d_mv USING btree (exchange, symbol, "timestamp");


--
-- Name: idx_meta_1h_pk; Type: INDEX; Schema: agg; Owner: -
--

CREATE UNIQUE INDEX idx_meta_1h_pk ON agg.meta_1h_mv USING btree (exchange, symbol, "timestamp");


--
-- Name: idx_meta_4h_pk; Type: INDEX; Schema: agg; Owner: -
--

CREATE UNIQUE INDEX idx_meta_4h_pk ON agg.meta_4h_mv USING btree (exchange, symbol, "timestamp");


--
-- Name: idx_ind_data_gin; Type: INDEX; Schema: indicators; Owner: -
--

CREATE INDEX idx_ind_data_gin ON indicators.indicator_data USING gin (data_json);


--
-- Name: idx_ind_indicator; Type: INDEX; Schema: indicators; Owner: -
--

CREATE INDEX idx_ind_indicator ON indicators.indicator_data USING btree (indicator);


--
-- Name: idx_ind_macd; Type: INDEX; Schema: indicators; Owner: -
--

CREATE INDEX idx_ind_macd ON indicators.indicator_data USING btree ((((data_json ->> 'macd'::text))::numeric)) WHERE (indicator = 'MACD'::text);


--
-- Name: idx_ind_rsi; Type: INDEX; Schema: indicators; Owner: -
--

CREATE INDEX idx_ind_rsi ON indicators.indicator_data USING btree ((((data_json ->> 'rsi'::text))::numeric)) WHERE (indicator = 'RSI'::text);


--
-- Name: idx_ind_symbol; Type: INDEX; Schema: indicators; Owner: -
--

CREATE INDEX idx_ind_symbol ON indicators.indicator_data USING btree (symbol);


--
-- Name: idx_ind_symbol_tf; Type: INDEX; Schema: indicators; Owner: -
--

CREATE INDEX idx_ind_symbol_tf ON indicators.indicator_data USING btree (symbol, timeframe);


--
-- Name: idx_ind_timeframe; Type: INDEX; Schema: indicators; Owner: -
--

CREATE INDEX idx_ind_timeframe ON indicators.indicator_data USING btree (timeframe);


--
-- Name: idx_ind_ts; Type: INDEX; Schema: indicators; Owner: -
--

CREATE INDEX idx_ind_ts ON indicators.indicator_data USING btree (ts DESC);


--
-- Name: futures_metadata_timestamp_idx; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX futures_metadata_timestamp_idx ON raw.futures_metadata USING btree ("timestamp" DESC);


--
-- Name: idx_kline_open_time; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX idx_kline_open_time ON raw.kline_1m USING btree (open_time DESC);


--
-- Name: idx_kline_symbol; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX idx_kline_symbol ON raw.kline_1m USING btree (symbol);


--
-- Name: idx_meta_symbol; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX idx_meta_symbol ON raw.futures_metadata USING btree (symbol);


--
-- Name: idx_meta_timestamp; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX idx_meta_timestamp ON raw.futures_metadata USING btree ("timestamp" DESC);


--
-- Name: kline_1m_open_time_idx; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX kline_1m_open_time_idx ON raw.kline_1m USING btree (open_time DESC);


--
-- Name: idx_instruments_exchange; Type: INDEX; Schema: reference; Owner: -
--

CREATE INDEX idx_instruments_exchange ON reference.instruments USING btree (exchange);


--
-- Name: idx_instruments_market; Type: INDEX; Schema: reference; Owner: -
--

CREATE INDEX idx_instruments_market ON reference.instruments USING btree (market);


--
-- Name: idx_instruments_symbol; Type: INDEX; Schema: reference; Owner: -
--

CREATE INDEX idx_instruments_symbol ON reference.instruments USING btree (symbol);


--
-- Name: futures_metadata ts_insert_blocker; Type: TRIGGER; Schema: raw; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON raw.futures_metadata FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- Name: kline_1m ts_insert_blocker; Type: TRIGGER; Schema: raw; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON raw.kline_1m FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- PostgreSQL database dump complete
--

\unrestrict x54qImlHyLxftfmFHeagxv6dIMPpw2E07hLUDHfL0e3gXxutltPw0cSCX3GQ2sF


--
-- PostgreSQL database dump
--

\restrict wuJEciMNCDXwwNmm4Z7EguKn9cLBbaDRtfZ4bV76VLFVkPlM7hd9Bs7byHYSIOk

-- Dumped from database version 16.10 (Ubuntu 16.10-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.10 (Ubuntu 16.10-0ubuntu0.24.04.1)

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
-- Name: upsert_candle_12h(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_12h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_12h AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_12h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text) OWNER TO opentd;

--
-- Name: upsert_candle_12h(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_12h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_12h AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_12h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_15m(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_15m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_15m AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_15m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_1M(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data."upsert_candle_1M"(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data."candles_1M" AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        is_closed, source, ingested_at, updated_at,
        taker_buy_volume, taker_buy_quote_volume
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_is_closed, p_source, NOW(), NOW(),
        p_taker_buy_volume, p_taker_buy_quote_volume
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data."upsert_candle_1M"(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text) OWNER TO opentd;

--
-- Name: upsert_candle_1M(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data."upsert_candle_1M"(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data."candles_1M" AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        is_closed, source, ingested_at, updated_at,
        taker_buy_volume, taker_buy_quote_volume
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_is_closed, p_source, NOW(), NOW(),
        p_taker_buy_volume, p_taker_buy_quote_volume
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data."upsert_candle_1M"(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_1d(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_1d(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_1d AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_1d(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_1h(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_1h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_1h AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_1h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_1m(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_1m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_1M AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_1m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text) OWNER TO opentd;

--
-- Name: upsert_candle_1m(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_1m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_1m AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_1m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_1w(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_1w(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_1w AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_1w(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text) OWNER TO opentd;

--
-- Name: upsert_candle_1w(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_1w(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_1w AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_1w(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_2h(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_2h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_2h AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_2h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text) OWNER TO opentd;

--
-- Name: upsert_candle_2h(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_2h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_2h AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_2h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_30m(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_30m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_30m AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_30m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text) OWNER TO opentd;

--
-- Name: upsert_candle_30m(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_30m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_30m AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_30m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_3m(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_3m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_3m AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_3m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text) OWNER TO opentd;

--
-- Name: upsert_candle_3m(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_3m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_3m AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_3m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_4h(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_4h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_4h AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_4h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_5m(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_5m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_5m AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_5m(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

--
-- Name: upsert_candle_6h(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_6h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_6h AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_6h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text) OWNER TO opentd;

--
-- Name: upsert_candle_6h(text, text, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, bigint, boolean, text, numeric, numeric); Type: FUNCTION; Schema: market_data; Owner: opentd
--

CREATE FUNCTION market_data.upsert_candle_6h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric DEFAULT NULL::numeric, p_trade_count bigint DEFAULT NULL::bigint, p_is_closed boolean DEFAULT false, p_source text DEFAULT 'ccxt'::text, p_taker_buy_volume numeric DEFAULT NULL::numeric, p_taker_buy_quote_volume numeric DEFAULT NULL::numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO market_data.candles_6h AS t (
        exchange, symbol, bucket_ts,
        open, high, low, close,
        volume, quote_volume, trade_count,
        taker_buy_volume, taker_buy_quote_volume,
        is_closed, source, ingested_at, updated_at
    ) VALUES (
        p_exchange, p_symbol, p_bucket_ts,
        p_open, p_high, p_low, p_close,
        p_volume, p_quote_volume, p_trade_count,
        p_taker_buy_volume, p_taker_buy_quote_volume,
        p_is_closed, p_source, NOW(), NOW()
    )
    ON CONFLICT (exchange, symbol, bucket_ts)
    DO UPDATE SET
        open        = CASE WHEN t.is_closed AND NOT EXCLUDED.is_closed THEN t.open ELSE EXCLUDED.open END,
        high        = GREATEST(t.high, EXCLUDED.high),
        low         = LEAST(t.low, EXCLUDED.low),
        close       = EXCLUDED.close,
        volume      = EXCLUDED.volume,
        quote_volume= COALESCE(EXCLUDED.quote_volume, t.quote_volume),
        trade_count = COALESCE(EXCLUDED.trade_count, t.trade_count),
        taker_buy_volume = COALESCE(EXCLUDED.taker_buy_volume, t.taker_buy_volume),
        taker_buy_quote_volume = COALESCE(EXCLUDED.taker_buy_quote_volume, t.taker_buy_quote_volume),
        is_closed   = t.is_closed OR EXCLUDED.is_closed,
        source      = EXCLUDED.source,
        updated_at  = NOW();
END;
$$;


ALTER FUNCTION market_data.upsert_candle_6h(p_exchange text, p_symbol text, p_bucket_ts timestamp with time zone, p_open numeric, p_high numeric, p_low numeric, p_close numeric, p_volume numeric, p_quote_volume numeric, p_trade_count bigint, p_is_closed boolean, p_source text, p_taker_buy_volume numeric, p_taker_buy_quote_volume numeric) OWNER TO opentd;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: candles_1m; Type: TABLE; Schema: market_data; Owner: opentd
--

CREATE TABLE market_data.candles_1m (
    exchange text NOT NULL,
    symbol text NOT NULL,
    bucket_ts timestamp with time zone NOT NULL,
    open numeric(38,12) NOT NULL,
    high numeric(38,12) NOT NULL,
    low numeric(38,12) NOT NULL,
    close numeric(38,12) NOT NULL,
    volume numeric(38,12) NOT NULL,
    quote_volume numeric(38,12),
    trade_count bigint,
    is_closed boolean DEFAULT false NOT NULL,
    source text DEFAULT 'binance_ws'::text NOT NULL,
    ingested_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    taker_buy_volume numeric(38,12),
    taker_buy_quote_volume numeric(38,12),
    CONSTRAINT candles_1m_bucket_ts_check CHECK ((bucket_ts = date_trunc('minute'::text, bucket_ts)))
);


ALTER TABLE market_data.candles_1m OWNER TO opentd;

--
-- Name: candles_12h; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_12h AS
 SELECT _materialized_hypertable_11.exchange,
    _materialized_hypertable_11.symbol,
    _materialized_hypertable_11.bucket_ts,
    _materialized_hypertable_11.open,
    _materialized_hypertable_11.high,
    _materialized_hypertable_11.low,
    _materialized_hypertable_11.close,
    _materialized_hypertable_11.volume,
    _materialized_hypertable_11.quote_volume,
    _materialized_hypertable_11.trade_count,
    _materialized_hypertable_11.is_closed,
    _materialized_hypertable_11.source,
    _materialized_hypertable_11.ingested_at,
    _materialized_hypertable_11.updated_at,
    _materialized_hypertable_11.taker_buy_volume,
    _materialized_hypertable_11.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_11
  WHERE (_materialized_hypertable_11.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(11)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('12:00:00'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(11)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('12:00:00'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_12h OWNER TO opentd;

--
-- Name: candles_15m; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_15m AS
 SELECT _materialized_hypertable_4.exchange,
    _materialized_hypertable_4.symbol,
    _materialized_hypertable_4.bucket_ts,
    _materialized_hypertable_4.open,
    _materialized_hypertable_4.high,
    _materialized_hypertable_4.low,
    _materialized_hypertable_4.close,
    _materialized_hypertable_4.volume,
    _materialized_hypertable_4.quote_volume,
    _materialized_hypertable_4.trade_count,
    _materialized_hypertable_4.is_closed,
    _materialized_hypertable_4.source,
    _materialized_hypertable_4.ingested_at,
    _materialized_hypertable_4.updated_at,
    _materialized_hypertable_4.taker_buy_volume,
    _materialized_hypertable_4.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_4
  WHERE (_materialized_hypertable_4.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(4)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('00:15:00'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(4)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('00:15:00'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_15m OWNER TO opentd;

--
-- Name: candles_1M; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data."candles_1M" AS
 SELECT _materialized_hypertable_16.exchange,
    _materialized_hypertable_16.symbol,
    _materialized_hypertable_16.bucket_ts,
    _materialized_hypertable_16.open,
    _materialized_hypertable_16.high,
    _materialized_hypertable_16.low,
    _materialized_hypertable_16.close,
    _materialized_hypertable_16.volume,
    _materialized_hypertable_16.quote_volume,
    _materialized_hypertable_16.trade_count,
    _materialized_hypertable_16.is_closed,
    _materialized_hypertable_16.source,
    _materialized_hypertable_16.ingested_at,
    _materialized_hypertable_16.updated_at,
    _materialized_hypertable_16.taker_buy_volume,
    _materialized_hypertable_16.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_16
  WHERE (_materialized_hypertable_16.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(16)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('1 mon'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(16)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('1 mon'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data."candles_1M" OWNER TO opentd;

--
-- Name: candles_1d; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_1d AS
 SELECT _materialized_hypertable_12.exchange,
    _materialized_hypertable_12.symbol,
    _materialized_hypertable_12.bucket_ts,
    _materialized_hypertable_12.open,
    _materialized_hypertable_12.high,
    _materialized_hypertable_12.low,
    _materialized_hypertable_12.close,
    _materialized_hypertable_12.volume,
    _materialized_hypertable_12.quote_volume,
    _materialized_hypertable_12.trade_count,
    _materialized_hypertable_12.is_closed,
    _materialized_hypertable_12.source,
    _materialized_hypertable_12.ingested_at,
    _materialized_hypertable_12.updated_at,
    _materialized_hypertable_12.taker_buy_volume,
    _materialized_hypertable_12.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_12
  WHERE (_materialized_hypertable_12.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(12)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('1 day'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(12)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('1 day'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_1d OWNER TO opentd;

--
-- Name: candles_1h; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_1h AS
 SELECT _materialized_hypertable_6.exchange,
    _materialized_hypertable_6.symbol,
    _materialized_hypertable_6.bucket_ts,
    _materialized_hypertable_6.open,
    _materialized_hypertable_6.high,
    _materialized_hypertable_6.low,
    _materialized_hypertable_6.close,
    _materialized_hypertable_6.volume,
    _materialized_hypertable_6.quote_volume,
    _materialized_hypertable_6.trade_count,
    _materialized_hypertable_6.is_closed,
    _materialized_hypertable_6.source,
    _materialized_hypertable_6.ingested_at,
    _materialized_hypertable_6.updated_at,
    _materialized_hypertable_6.taker_buy_volume,
    _materialized_hypertable_6.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_6
  WHERE (_materialized_hypertable_6.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(6)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('01:00:00'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(6)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('01:00:00'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_1h OWNER TO opentd;

--
-- Name: candles_1w; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_1w AS
 SELECT _materialized_hypertable_14.exchange,
    _materialized_hypertable_14.symbol,
    _materialized_hypertable_14.bucket_ts,
    _materialized_hypertable_14.open,
    _materialized_hypertable_14.high,
    _materialized_hypertable_14.low,
    _materialized_hypertable_14.close,
    _materialized_hypertable_14.volume,
    _materialized_hypertable_14.quote_volume,
    _materialized_hypertable_14.trade_count,
    _materialized_hypertable_14.is_closed,
    _materialized_hypertable_14.source,
    _materialized_hypertable_14.ingested_at,
    _materialized_hypertable_14.updated_at,
    _materialized_hypertable_14.taker_buy_volume,
    _materialized_hypertable_14.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_14
  WHERE (_materialized_hypertable_14.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(14)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('7 days'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(14)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('7 days'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_1w OWNER TO opentd;

--
-- Name: candles_2h; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_2h AS
 SELECT _materialized_hypertable_7.exchange,
    _materialized_hypertable_7.symbol,
    _materialized_hypertable_7.bucket_ts,
    _materialized_hypertable_7.open,
    _materialized_hypertable_7.high,
    _materialized_hypertable_7.low,
    _materialized_hypertable_7.close,
    _materialized_hypertable_7.volume,
    _materialized_hypertable_7.quote_volume,
    _materialized_hypertable_7.trade_count,
    _materialized_hypertable_7.is_closed,
    _materialized_hypertable_7.source,
    _materialized_hypertable_7.ingested_at,
    _materialized_hypertable_7.updated_at,
    _materialized_hypertable_7.taker_buy_volume,
    _materialized_hypertable_7.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_7
  WHERE (_materialized_hypertable_7.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(7)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('02:00:00'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(7)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('02:00:00'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_2h OWNER TO opentd;

--
-- Name: candles_30m; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_30m AS
 SELECT _materialized_hypertable_5.exchange,
    _materialized_hypertable_5.symbol,
    _materialized_hypertable_5.bucket_ts,
    _materialized_hypertable_5.open,
    _materialized_hypertable_5.high,
    _materialized_hypertable_5.low,
    _materialized_hypertable_5.close,
    _materialized_hypertable_5.volume,
    _materialized_hypertable_5.quote_volume,
    _materialized_hypertable_5.trade_count,
    _materialized_hypertable_5.is_closed,
    _materialized_hypertable_5.source,
    _materialized_hypertable_5.ingested_at,
    _materialized_hypertable_5.updated_at,
    _materialized_hypertable_5.taker_buy_volume,
    _materialized_hypertable_5.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_5
  WHERE (_materialized_hypertable_5.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(5)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('00:30:00'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(5)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('00:30:00'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_30m OWNER TO opentd;

--
-- Name: candles_3d; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_3d AS
 SELECT _materialized_hypertable_13.exchange,
    _materialized_hypertable_13.symbol,
    _materialized_hypertable_13.bucket_ts,
    _materialized_hypertable_13.open,
    _materialized_hypertable_13.high,
    _materialized_hypertable_13.low,
    _materialized_hypertable_13.close,
    _materialized_hypertable_13.volume,
    _materialized_hypertable_13.quote_volume,
    _materialized_hypertable_13.trade_count,
    _materialized_hypertable_13.is_closed,
    _materialized_hypertable_13.source,
    _materialized_hypertable_13.ingested_at,
    _materialized_hypertable_13.updated_at,
    _materialized_hypertable_13.taker_buy_volume,
    _materialized_hypertable_13.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_13
  WHERE (_materialized_hypertable_13.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(13)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('3 days'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(13)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('3 days'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_3d OWNER TO opentd;

--
-- Name: candles_3m; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_3m AS
 SELECT _materialized_hypertable_2.exchange,
    _materialized_hypertable_2.symbol,
    _materialized_hypertable_2.bucket_ts,
    _materialized_hypertable_2.open,
    _materialized_hypertable_2.high,
    _materialized_hypertable_2.low,
    _materialized_hypertable_2.close,
    _materialized_hypertable_2.volume,
    _materialized_hypertable_2.quote_volume,
    _materialized_hypertable_2.trade_count,
    _materialized_hypertable_2.is_closed,
    _materialized_hypertable_2.source,
    _materialized_hypertable_2.ingested_at,
    _materialized_hypertable_2.updated_at,
    _materialized_hypertable_2.taker_buy_volume,
    _materialized_hypertable_2.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_2
  WHERE (_materialized_hypertable_2.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(2)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('00:03:00'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(2)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('00:03:00'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_3m OWNER TO opentd;

--
-- Name: candles_4h; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_4h AS
 SELECT _materialized_hypertable_8.exchange,
    _materialized_hypertable_8.symbol,
    _materialized_hypertable_8.bucket_ts,
    _materialized_hypertable_8.open,
    _materialized_hypertable_8.high,
    _materialized_hypertable_8.low,
    _materialized_hypertable_8.close,
    _materialized_hypertable_8.volume,
    _materialized_hypertable_8.quote_volume,
    _materialized_hypertable_8.trade_count,
    _materialized_hypertable_8.is_closed,
    _materialized_hypertable_8.source,
    _materialized_hypertable_8.ingested_at,
    _materialized_hypertable_8.updated_at,
    _materialized_hypertable_8.taker_buy_volume,
    _materialized_hypertable_8.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_8
  WHERE (_materialized_hypertable_8.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(8)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('04:00:00'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(8)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('04:00:00'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_4h OWNER TO opentd;

--
-- Name: candles_5m; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_5m AS
 SELECT _materialized_hypertable_3.exchange,
    _materialized_hypertable_3.symbol,
    _materialized_hypertable_3.bucket_ts,
    _materialized_hypertable_3.open,
    _materialized_hypertable_3.high,
    _materialized_hypertable_3.low,
    _materialized_hypertable_3.close,
    _materialized_hypertable_3.volume,
    _materialized_hypertable_3.quote_volume,
    _materialized_hypertable_3.trade_count,
    _materialized_hypertable_3.is_closed,
    _materialized_hypertable_3.source,
    _materialized_hypertable_3.ingested_at,
    _materialized_hypertable_3.updated_at,
    _materialized_hypertable_3.taker_buy_volume,
    _materialized_hypertable_3.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_3
  WHERE (_materialized_hypertable_3.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(3)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('00:05:00'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(3)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('00:05:00'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_5m OWNER TO opentd;

--
-- Name: candles_6h; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_6h AS
 SELECT _materialized_hypertable_9.exchange,
    _materialized_hypertable_9.symbol,
    _materialized_hypertable_9.bucket_ts,
    _materialized_hypertable_9.open,
    _materialized_hypertable_9.high,
    _materialized_hypertable_9.low,
    _materialized_hypertable_9.close,
    _materialized_hypertable_9.volume,
    _materialized_hypertable_9.quote_volume,
    _materialized_hypertable_9.trade_count,
    _materialized_hypertable_9.is_closed,
    _materialized_hypertable_9.source,
    _materialized_hypertable_9.ingested_at,
    _materialized_hypertable_9.updated_at,
    _materialized_hypertable_9.taker_buy_volume,
    _materialized_hypertable_9.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_9
  WHERE (_materialized_hypertable_9.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(9)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('06:00:00'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(9)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('06:00:00'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_6h OWNER TO opentd;

--
-- Name: candles_8h; Type: VIEW; Schema: market_data; Owner: opentd
--

CREATE VIEW market_data.candles_8h AS
 SELECT _materialized_hypertable_10.exchange,
    _materialized_hypertable_10.symbol,
    _materialized_hypertable_10.bucket_ts,
    _materialized_hypertable_10.open,
    _materialized_hypertable_10.high,
    _materialized_hypertable_10.low,
    _materialized_hypertable_10.close,
    _materialized_hypertable_10.volume,
    _materialized_hypertable_10.quote_volume,
    _materialized_hypertable_10.trade_count,
    _materialized_hypertable_10.is_closed,
    _materialized_hypertable_10.source,
    _materialized_hypertable_10.ingested_at,
    _materialized_hypertable_10.updated_at,
    _materialized_hypertable_10.taker_buy_volume,
    _materialized_hypertable_10.taker_buy_quote_volume
   FROM _timescaledb_internal._materialized_hypertable_10
  WHERE (_materialized_hypertable_10.bucket_ts < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(10)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT candles_1m.exchange,
    candles_1m.symbol,
    public.time_bucket('08:00:00'::interval, candles_1m.bucket_ts) AS bucket_ts,
    public.first(candles_1m.open, candles_1m.bucket_ts) AS open,
    max(candles_1m.high) AS high,
    min(candles_1m.low) AS low,
    public.last(candles_1m.close, candles_1m.bucket_ts) AS close,
    sum(candles_1m.volume) AS volume,
    sum(candles_1m.quote_volume) AS quote_volume,
    sum(candles_1m.trade_count) AS trade_count,
    bool_and(candles_1m.is_closed) AS is_closed,
    'cagg'::text AS source,
    max(candles_1m.ingested_at) AS ingested_at,
    max(candles_1m.updated_at) AS updated_at,
    sum(candles_1m.taker_buy_volume) AS taker_buy_volume,
    sum(candles_1m.taker_buy_quote_volume) AS taker_buy_quote_volume
   FROM market_data.candles_1m
  WHERE (candles_1m.bucket_ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(10)), '-infinity'::timestamp with time zone))
  GROUP BY candles_1m.exchange, candles_1m.symbol, (public.time_bucket('08:00:00'::interval, candles_1m.bucket_ts));


ALTER VIEW market_data.candles_8h OWNER TO opentd;

--
-- Name: ingest_offsets; Type: TABLE; Schema: market_data; Owner: opentd
--

CREATE TABLE market_data.ingest_offsets (
    exchange text NOT NULL,
    symbol text NOT NULL,
    "interval" text NOT NULL,
    last_closed_ts timestamp with time zone,
    last_partial_ts timestamp with time zone,
    last_reconciled_at timestamp with time zone,
    CONSTRAINT ingest_offsets_interval_check CHECK (("interval" = ANY (ARRAY['1m'::text, '3m'::text, '5m'::text, '15m'::text, '30m'::text, '1h'::text, '2h'::text, '4h'::text, '6h'::text, '12h'::text, '1d'::text, '1w'::text, '1M'::text])))
);


ALTER TABLE market_data.ingest_offsets OWNER TO opentd;

--
-- Name: missing_intervals; Type: TABLE; Schema: market_data; Owner: opentd
--

CREATE TABLE market_data.missing_intervals (
    id bigint NOT NULL,
    exchange text NOT NULL,
    symbol text NOT NULL,
    "interval" text NOT NULL,
    gap_start timestamp with time zone NOT NULL,
    gap_end timestamp with time zone NOT NULL,
    detected_at timestamp with time zone DEFAULT now() NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    retry_count integer DEFAULT 0 NOT NULL,
    last_error text
);


ALTER TABLE market_data.missing_intervals OWNER TO opentd;

--
-- Name: missing_intervals_id_seq; Type: SEQUENCE; Schema: market_data; Owner: opentd
--

CREATE SEQUENCE market_data.missing_intervals_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE market_data.missing_intervals_id_seq OWNER TO opentd;

--
-- Name: missing_intervals_id_seq; Type: SEQUENCE OWNED BY; Schema: market_data; Owner: opentd
--

ALTER SEQUENCE market_data.missing_intervals_id_seq OWNED BY market_data.missing_intervals.id;


--
-- Name: missing_intervals id; Type: DEFAULT; Schema: market_data; Owner: opentd
--

ALTER TABLE ONLY market_data.missing_intervals ALTER COLUMN id SET DEFAULT nextval('market_data.missing_intervals_id_seq'::regclass);


--
-- Name: candles_1m candles_1m_pkey; Type: CONSTRAINT; Schema: market_data; Owner: opentd
--

ALTER TABLE ONLY market_data.candles_1m
    ADD CONSTRAINT candles_1m_pkey PRIMARY KEY (exchange, symbol, bucket_ts);


--
-- Name: ingest_offsets ingest_offsets_pkey; Type: CONSTRAINT; Schema: market_data; Owner: opentd
--

ALTER TABLE ONLY market_data.ingest_offsets
    ADD CONSTRAINT ingest_offsets_pkey PRIMARY KEY (exchange, symbol, "interval");


--
-- Name: missing_intervals missing_intervals_pkey; Type: CONSTRAINT; Schema: market_data; Owner: opentd
--

ALTER TABLE ONLY market_data.missing_intervals
    ADD CONSTRAINT missing_intervals_pkey PRIMARY KEY (id);


--
-- Name: candles_1m_bucket_ts_idx; Type: INDEX; Schema: market_data; Owner: opentd
--

CREATE INDEX candles_1m_bucket_ts_idx ON market_data.candles_1m USING btree (bucket_ts DESC);


--
-- Name: candles_1m ts_cagg_invalidation_trigger; Type: TRIGGER; Schema: market_data; Owner: opentd
--

CREATE TRIGGER ts_cagg_invalidation_trigger AFTER INSERT OR DELETE OR UPDATE ON market_data.candles_1m FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.continuous_agg_invalidation_trigger('1');


--
-- Name: candles_1m ts_insert_blocker; Type: TRIGGER; Schema: market_data; Owner: opentd
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON market_data.candles_1m FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- PostgreSQL database dump complete
--

\unrestrict wuJEciMNCDXwwNmm4Z7EguKn9cLBbaDRtfZ4bV76VLFVkPlM7hd9Bs7byHYSIOk


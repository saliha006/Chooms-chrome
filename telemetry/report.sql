-- Trial report from the Aiven `events` table (PRD 7.3, F8). Real runs only: mock runs have a 'mock-' run_id.
-- Run in the Aiven console's query editor or: psql "$AIVEN_PG_URI" -f telemetry/report.sql

-- 1. Per run: bricks sorted, pauses for a human, and the share of bricks that needed none.
SELECT run_id,
       count(*) FILTER (WHERE state = 'LOG') AS sorted,
       count(*) FILTER (WHERE state = 'PAUSE_HUMAN') AS help_pauses,
       round(100.0 * count(*) FILTER (WHERE state = 'LOG')
             / nullif(count(DISTINCT brick_id) FILTER (WHERE state <> 'LOCATE'), 0), 1) AS success_pct,
       min(ts) AS started
FROM events
WHERE run_id NOT LIKE 'mock-%'
GROUP BY run_id
ORDER BY started DESC;

-- 2. Why the cell asked for help, by reason code (common/reasons.py).
SELECT outcome AS reason, count(*) AS pauses
FROM events
WHERE state = 'PAUSE_HUMAN' AND run_id NOT LIKE 'mock-%'
GROUP BY outcome
ORDER BY pauses DESC;

-- 3. Time per stage and device: where a brick's cycle time goes, and which chip ran the inspection.
SELECT state, coalesce(device, '-') AS device, count(*) AS n,
       round(avg(latency_ms)::numeric, 1) AS mean_ms,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms)::numeric, 1) AS p50_ms,
       round(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)::numeric, 1) AS p95_ms
FROM events
WHERE latency_ms IS NOT NULL AND run_id NOT LIKE 'mock-%'
GROUP BY state, device
ORDER BY state, device;

-- 4. Verdicts and how they were reached (each LOG row's note is ReasonTrace's one-line summary).
SELECT label, count(*) AS bricks,
       count(*) FILTER (WHERE note LIKE '%look again%') AS needed_a_second_look
FROM events
WHERE state = 'LOG' AND run_id NOT LIKE 'mock-%'
GROUP BY label
ORDER BY label;

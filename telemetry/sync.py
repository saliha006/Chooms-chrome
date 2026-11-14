"""Ship the JSONL event log to Aiven (F15): PostgreSQL for the record, Kafka for the live stream.

The control loop only ever appends to runs/events.jsonl (telemetry.log). This runs beside it on its own thread
and never blocks it: every few seconds it reads the lines it hasn't sent yet, inserts them into PostgreSQL in one
batch and, if Kafka is configured, produces each to `sortsense.events`. Offline, rows wait in the file; the
offset is saved only after a batch lands, and duplicates are skipped, so a retry never double-counts.

    python -m telemetry.sync            # send whatever is waiting, once (e.g. after a run without network)
"""

import json
import logging
import os
import threading
from pathlib import Path

from dotenv import load_dotenv

EVENTS = Path("runs/events.jsonl")
TOPIC = "sortsense.events"
INTERVAL_S = 2.0
COLUMNS = ("run_id", "brick_id", "ts", "state", "label", "score", "device", "stage", "latency_ms", "outcome", "note")

# PRD 7.3 `events`. The unique key makes a re-sent row a no-op (ts carries microseconds, so it never collides).
SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    run_id text NOT NULL,
    brick_id integer NOT NULL,
    ts timestamptz NOT NULL,
    state text NOT NULL,
    label text,
    score double precision,
    device text,
    stage text,
    latency_ms double precision,
    outcome text,
    note text,
    UNIQUE (run_id, brick_id, ts, state)
)"""
INSERT = (f"INSERT INTO events ({', '.join(COLUMNS)}) "
          f"VALUES (%s, %s, to_timestamp(%s), {', '.join(['%s'] * (len(COLUMNS) - 3))}) ON CONFLICT DO NOTHING")

_log = logging.getLogger("telemetry.sync")


def kafka_config() -> dict | None:
    env = os.environ.get
    if not env("AIVEN_KAFKA_BOOTSTRAP"):
        return None
    return {"bootstrap.servers": env("AIVEN_KAFKA_BOOTSTRAP"), "security.protocol": "SSL",
            "ssl.ca.location": env("AIVEN_KAFKA_CA"), "ssl.certificate.location": env("AIVEN_KAFKA_CERT"),
            "ssl.key.location": env("AIVEN_KAFKA_KEY")}


def make_producer():
    config = kafka_config()
    if config is None:
        return None
    from confluent_kafka import Producer

    return Producer(config)


class Syncer:
    """Sends new lines of `events` to PostgreSQL (and Kafka). `connect` and `producer` are seams for tests."""

    def __init__(self, pg_uri: str, events: Path = EVENTS, connect=None, producer=None):
        self.pg_uri = pg_uri
        self.events = events
        self.offset_file = events.with_suffix(".offset")
        self._connect = connect
        self.producer = producer
        self._schema_ready = False

    def pending(self) -> tuple[list[dict], int]:
        """Unsent rows and the byte offset after them. A half-written last line is left for next time."""
        if not self.events.exists():
            return [], 0
        start = int(self.offset_file.read_text()) if self.offset_file.exists() else 0
        with self.events.open("rb") as f:
            f.seek(start)
            data = f.read()
        complete = data[:data.rfind(b"\n") + 1]
        rows = [json.loads(line) for line in complete.decode("utf-8").splitlines() if line.strip()]
        return rows, start + len(complete)

    def send_once(self) -> int:
        rows, end = self.pending()
        if not rows:
            return 0
        connect = self._connect or self._psycopg_connect
        with connect(self.pg_uri) as conn:
            if not self._schema_ready:
                conn.execute(SCHEMA)
                self._schema_ready = True
            with conn.cursor() as cur:
                cur.executemany(INSERT, [tuple(row.get(c) for c in COLUMNS) for row in rows])
        if self.producer is not None:
            for row in rows:
                self.producer.produce(TOPIC, key=str(row.get("run_id")), value=json.dumps(row))
            self.producer.flush(10)
        self.offset_file.write_text(str(end))  # only after the batch has landed
        return len(rows)

    @staticmethod
    def _psycopg_connect(uri: str):
        import psycopg

        return psycopg.connect(uri, connect_timeout=10)


def start(stop: threading.Event, events: Path = EVENTS) -> threading.Thread | None:
    """Background sync while the cell runs. None (and the JSONL file alone) when Aiven isn't configured."""
    load_dotenv()
    if not os.environ.get("AIVEN_PG_URI"):
        _log.info("AIVEN_PG_URI not set: events stay in %s", events)
        return None
    syncer = Syncer(os.environ["AIVEN_PG_URI"], events, producer=make_producer())

    def loop() -> None:
        failing = False
        while not stop.wait(INTERVAL_S):
            try:
                syncer.send_once()
                if failing:
                    _log.info("Aiven reachable again; caught up")
                failing = False
            except Exception as exc:  # network, auth or server: all mean "keep the rows, try again later"
                if not failing:
                    _log.warning("Aiven sync paused (%s); rows stay in %s", type(exc).__name__, events)
                failing = True
        try:
            syncer.send_once()  # last rows of the run
        except Exception as exc:
            _log.warning("final Aiven sync failed (%s); run python -m telemetry.sync later", type(exc).__name__)

    thread = threading.Thread(target=loop, name="aiven-sync", daemon=True)
    thread.start()
    return thread


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    load_dotenv()
    if not os.environ.get("AIVEN_PG_URI"):
        raise SystemExit("AIVEN_PG_URI not set in .env")
    sent = Syncer(os.environ["AIVEN_PG_URI"], producer=make_producer()).send_once()
    print(f"sent {sent} rows")


if __name__ == "__main__":
    main()

import json
import threading

import pytest

from telemetry import sync
from telemetry.sync import COLUMNS, Syncer


class FakeDB:
    """Stands in for a psycopg connection: records every batch, or fails like a dropped network."""

    def __init__(self, fail=False):
        self.fail = fail
        self.batches: list[list[tuple]] = []
        self.statements: list[str] = []

    def __call__(self, uri):
        if self.fail:
            raise OSError("network down")
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, *args):
        self.statements.append(sql)

    def cursor(self):
        return self

    def executemany(self, sql, rows):
        self.batches.append(list(rows))


class FakeProducer:
    def __init__(self):
        self.sent = []

    def produce(self, topic, key, value):
        self.sent.append((topic, key, json.loads(value)))

    def flush(self, timeout):
        return 0


def row(n, state="PICK"):
    return {"run_id": "r1", "brick_id": n, "ts": 1000.0 + n, "state": state, "label": None, "score": None,
            "device": None, "stage": state.lower(), "latency_ms": 1.5, "outcome": "ok", "note": None}


def write(path, rows, partial=""):
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
        f.write(partial)


def test_sends_new_rows_once_in_column_order(tmp_path):
    events = tmp_path / "events.jsonl"
    write(events, [row(1), row(2)])
    db = FakeDB()
    syncer = Syncer("uri", events, connect=db)
    assert syncer.send_once() == 2
    assert db.batches == [[tuple(row(n)[c] for c in COLUMNS) for n in (1, 2)]]
    assert any("CREATE TABLE IF NOT EXISTS events" in s for s in db.statements)
    assert syncer.send_once() == 0  # nothing new


def test_only_rows_written_since_last_send(tmp_path):
    events = tmp_path / "events.jsonl"
    write(events, [row(1)])
    db = FakeDB()
    syncer = Syncer("uri", events, connect=db)
    syncer.send_once()
    write(events, [row(2), row(3)])
    assert syncer.send_once() == 2
    assert [r[1] for r in db.batches[-1]] == [2, 3]


def test_a_half_written_line_waits_for_next_time(tmp_path):
    events = tmp_path / "events.jsonl"
    write(events, [row(1)], partial='{"run_id": "r1", "bri')
    syncer = Syncer("uri", events, connect=FakeDB())
    assert syncer.send_once() == 1
    with events.open("a", encoding="utf-8") as f:
        f.write('ck_id": 2, "ts": 1002.0, "state": "PICK"}\n')
    assert syncer.send_once() == 1


def test_offline_keeps_the_rows_for_later(tmp_path):
    events = tmp_path / "events.jsonl"
    write(events, [row(1), row(2)])
    with pytest.raises(OSError):
        Syncer("uri", events, connect=FakeDB(fail=True)).send_once()
    assert not events.with_suffix(".offset").exists()  # nothing marked as sent
    assert Syncer("uri", events, connect=FakeDB()).send_once() == 2  # back online: all of it goes


def test_kafka_gets_every_row_keyed_by_run(tmp_path):
    events = tmp_path / "events.jsonl"
    write(events, [row(1), row(2, "PLACE")])
    producer = FakeProducer()
    Syncer("uri", events, connect=FakeDB(), producer=producer).send_once()
    assert [(t, k, v["state"]) for t, k, v in producer.sent] == [("sortsense.events", "r1", "PICK"),
                                                                 ("sortsense.events", "r1", "PLACE")]


def test_without_aiven_settings_nothing_starts(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "load_dotenv", lambda: None)
    monkeypatch.delenv("AIVEN_PG_URI", raising=False)
    assert sync.start(threading.Event(), tmp_path / "events.jsonl") is None


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class DriftDB(FakeDB):
    """FakeDB that answers the drift query with given perfect-brick scores (or fails it)."""

    def __init__(self, scores=(), query_fails=False):
        super().__init__()
        self.scores, self.query_fails = scores, query_fails

    def execute(self, sql, *args):
        super().execute(sql, *args)
        if sql is sync.PERFECT_FIRST_LOOKS:
            if self.query_fails:
                raise RuntimeError("bad query")
            return Rows([(s,) for s in self.scores])

    def transaction(self):
        return self


def test_drift_alarm_fires_once_from_the_database(tmp_path):
    events = tmp_path / "events.jsonl"
    alerts = []
    watch = sync.DriftWatch("r1", good_mean=0.10, t_low=0.20, on_alert=alerts.append)
    syncer = Syncer("uri", events, connect=DriftDB(scores=[0.17] * 6), drift=watch)
    write(events, [row(1)])
    syncer.send_once()
    write(events, [row(2)])
    syncer.send_once()
    assert len(alerts) == 1 and alerts[0].alert  # 70% of the way to t_low, said once


def test_no_alarm_while_perfect_bricks_sit_near_the_baseline(tmp_path):
    events = tmp_path / "events.jsonl"
    alerts = []
    watch = sync.DriftWatch("r1", good_mean=0.10, t_low=0.20, on_alert=alerts.append)
    write(events, [row(1)])
    Syncer("uri", events, connect=DriftDB(scores=[0.11] * 6), drift=watch).send_once()
    assert alerts == []


def test_a_failed_drift_query_still_sends_the_events(tmp_path):
    events = tmp_path / "events.jsonl"
    db = DriftDB(query_fails=True)
    watch = sync.DriftWatch("r1", 0.10, 0.20, on_alert=lambda d: None)
    write(events, [row(1), row(2)])
    assert Syncer("uri", events, connect=db, drift=watch).send_once() == 2
    assert Syncer("uri", events, connect=db, drift=watch).send_once() == 0  # offset saved: nothing re-sent


def test_drift_alarm_off_without_good_mean(tmp_path):
    thresholds = tmp_path / "thresholds.yaml"
    thresholds.write_text("t_low: 0.2\nt_high: 0.6\n")  # stand-in thresholds: no real-brick evaluation yet
    assert sync.drift_watch("r1", thresholds, on_alert=lambda d: None) is None
    thresholds.write_text("t_low: 0.2\nt_high: 0.6\ngood_mean: 0.1\n")
    assert sync.drift_watch("r1", thresholds, on_alert=lambda d: None).t_low == 0.2

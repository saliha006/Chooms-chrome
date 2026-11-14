"""Is Aiven reachable from this machine? Run before relying on the stream (and at the venue, on the Intel laptop).

    python -m telemetry.check_aiven

Reads the AIVEN_* settings from .env and prints only yes/no, versions and timings: never a host, user,
password or key. A part with no settings is reported as "not configured", not as a failure.
"""

import os
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

TIMEOUT_S = 10


def check_postgres(uri: str) -> str:
    import psycopg

    start = time.perf_counter()
    with psycopg.connect(uri, connect_timeout=TIMEOUT_S) as conn:
        connect_ms = (time.perf_counter() - start) * 1000
        version = conn.execute("SHOW server_version").fetchone()[0]
        token = uuid.uuid4().hex
        # A temporary table proves we can write without leaving anything behind.
        conn.execute("CREATE TEMP TABLE sortsense_check (token text)")
        conn.execute("INSERT INTO sortsense_check VALUES (%s)", (token,))
        echoed = conn.execute("SELECT token FROM sortsense_check").fetchone()[0]
    if echoed != token:
        raise RuntimeError("wrote one value, read back another")
    return f"PostgreSQL {version}, connected in {connect_ms:.0f} ms, write + read back OK"


def check_kafka(bootstrap: str, ca: str, cert: str, key: str) -> str:
    from confluent_kafka.admin import AdminClient

    missing = [path for path in (ca, cert, key) if not Path(path).is_file()]
    if missing:
        raise FileNotFoundError(f"missing certificate file(s): {', '.join(missing)}")
    admin = AdminClient({
        "bootstrap.servers": bootstrap, "security.protocol": "SSL",
        "ssl.ca.location": ca, "ssl.certificate.location": cert, "ssl.key.location": key,
    })
    start = time.perf_counter()
    metadata = admin.list_topics(timeout=TIMEOUT_S)
    return (f"Kafka reached in {(time.perf_counter() - start) * 1000:.0f} ms, "
            f"{len(metadata.brokers)} broker(s), topics: {', '.join(sorted(metadata.topics)) or 'none yet'}")


def main() -> None:
    load_dotenv()
    env = os.environ.get
    checks = {
        "PostgreSQL": (lambda: check_postgres(env("AIVEN_PG_URI"))) if env("AIVEN_PG_URI") else None,
        "Kafka": (lambda: check_kafka(env("AIVEN_KAFKA_BOOTSTRAP"), env("AIVEN_KAFKA_CA"), env("AIVEN_KAFKA_CERT"),
                                      env("AIVEN_KAFKA_KEY")))
        if env("AIVEN_KAFKA_BOOTSTRAP") else None,
    }
    failed = False
    for name, check in checks.items():
        if check is None:
            print(f"{name}: not configured")
            continue
        try:
            print(f"{name}: {check()}")
        except Exception as exc:  # report every failure kind the same way: type and message, no secrets in either
            failed = True
            print(f"{name}: FAILED ({type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

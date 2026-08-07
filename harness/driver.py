"""Thin wrapper around the official neo4j Python driver."""
import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, TransientError


def get_driver(platform, max_retries=5, retry_wait_s=3):
    last_exc = None

    for attempt in range(1, max_retries + 1):
        try:
            driver = GraphDatabase.driver(
    platform.uri,
    auth=(platform.user, platform.password),
)

            driver.verify_connectivity()
            return driver

        except (ServiceUnavailable, TransientError) as e:
            last_exc = e
            print(
                f"[{platform.key}] connect attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {retry_wait_s}s..."
            )
            time.sleep(retry_wait_s)

    raise RuntimeError(
        f"[{platform.key}] could not connect after {max_retries} attempts"
    ) from last_exc


def run_cypher(driver, cypher, params=None, database=None):
    with driver.session(database=database) as session:
        return list(session.run(cypher, params or {}))
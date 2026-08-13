from __future__ import annotations

import logging

from spend_lens_common.config import raw_data_dir
from spend_lens_common.storage import write_records

from .client import connect
from .collect import collect_query_history, collect_warehouse_metering_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    conn = connect()
    output_dir = raw_data_dir()
    try:
        query_history = collect_query_history(conn)
        warehouse_metering = collect_warehouse_metering_history(conn)
    finally:
        conn.close()

    for records, table in (
        (query_history, "query_history"),
        (warehouse_metering, "warehouse_metering_history"),
    ):
        path = write_records(records, source="snowflake", table=table, output_dir=output_dir)
        logger.info("snowflake: wrote %s (%d records) -> %s", table, len(records), path)


if __name__ == "__main__":
    run()

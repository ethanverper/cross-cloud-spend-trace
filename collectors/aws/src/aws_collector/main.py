from __future__ import annotations

import logging

from spend_lens_common.config import raw_data_dir
from spend_lens_common.storage import write_records

from .client import cost_explorer_client
from .collect import (
    collect_cost_and_usage,
    collect_cost_forecast,
    collect_service_dimension_values,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    client = cost_explorer_client()
    output_dir = raw_data_dir()

    cost_and_usage = collect_cost_and_usage(client)
    forecast = collect_cost_forecast(client)
    dimension_values = collect_service_dimension_values(client)

    for records, table in (
        (cost_and_usage, "cost_and_usage"),
        (forecast, "cost_forecast"),
        (dimension_values, "service_dimension_values"),
    ):
        path = write_records(records, source="aws", table=table, output_dir=output_dir)
        logger.info("aws: wrote %s (%d records) -> %s", table, len(records), path)


if __name__ == "__main__":
    run()

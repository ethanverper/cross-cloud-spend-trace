from __future__ import annotations

import logging

from spend_lens_common.config import raw_data_dir
from spend_lens_common.storage import write_records

from .client import DatabricksClient
from .collect import cluster_ids_from_job_runs, collect_cluster_events, collect_job_runs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    client = DatabricksClient()
    output_dir = raw_data_dir()

    job_runs = collect_job_runs(client)
    cluster_ids = cluster_ids_from_job_runs(job_runs)
    cluster_events = collect_cluster_events(client, cluster_ids) if cluster_ids else []

    for records, table in (
        (job_runs, "job_runs"),
        (cluster_events, "cluster_events"),
    ):
        path = write_records(records, source="databricks", table=table, output_dir=output_dir)
        logger.info("databricks: wrote %s (%d records) -> %s", table, len(records), path)


if __name__ == "__main__":
    run()

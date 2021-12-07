"""This module destroys the expired automatic snapshots

SPDX-License-Identifier: Apache-2.0
"""
import datetime

import structlog

from .utils import setup_cli


log = structlog.get_logger()


def process_snapshots(os_client, dry_run, all_projects):
    """Delete every expired snapshot"""
    all_projects = True if all_projects else None
    for snapshot in os_client.block_storage.snapshots(
        all_projects=all_projects, status="available"
    ):
        log.debug("Looking at snapshot", snapshot=snapshot.id)
        if "expire_at" not in snapshot.metadata:
            continue
        expire_at = datetime.datetime.combine(
            date=datetime.date.fromisoformat(snapshot.metadata["expire_at"]),
            time=datetime.time.min,
            tzinfo=datetime.timezone.utc,
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        if now > expire_at:
            log.debug(
                "Deleting snapshot",
                snapshot=snapshot.id,
                expire_at=expire_at.isoformat(),
            )
            if not dry_run:
                os_client.block_storage.delete_snapshot(snapshot)
                log.info(
                    "Deleted snapshot",
                    snapshot=snapshot.id,
                    expire_at=expire_at.isoformat(),
                )
        else:
            log.debug(
                "Keeping snapshot, still valid",
                snapshot=snapshot.id,
                expire_at=expire_at.isoformat(),
            )


def cli():
    """Entrypoint for CLI usage"""
    os_client, dry_run, all_projects = setup_cli()

    process_snapshots(os_client, dry_run, all_projects)


if __name__ == "__main__":  # pragma: no cover
    cli()

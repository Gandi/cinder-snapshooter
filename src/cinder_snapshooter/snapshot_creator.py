"""This module makes the automatic snapshots

SPDX-License-Identifier: Apache-2.0
"""
import datetime

import structlog

from dateutil.relativedelta import relativedelta

from .utils import setup_cli, str2bool


log = structlog.get_logger()


def create_snapshot_if_needed(
    volume,
    os_client,
    all_projects,
    dry_run,
):
    """Create a snapshot if there isn't one for this volume today
    The snapshot will expire in 7 day unless it is the first of the month where it
    will expire in 3 months
    """
    volume_snapshots = os_client.block_storage.snapshots(
        all_projects=all_projects,
        status="available",
        volume_id=volume.id,
    )
    is_monthly = True
    now = datetime.datetime.now(datetime.timezone.utc)
    for snapshot in volume_snapshots:
        log.debug(
            "Looking at snapshot",
            snapshot=snapshot.id,
            metadata=snapshot.metadata,
            volume=volume.id,
        )
        created_at = datetime.datetime.fromisoformat(snapshot.created_at)
        if "expire_at" not in snapshot.metadata:
            continue  # Not an automatic snapshot
        if not created_at.year == now.year:
            continue
        if not created_at.month == now.month:
            continue
        # The snapshot was created this month
        is_monthly = False
        if created_at.day == now.day:
            log.debug(
                "Already a snapshot today for this volume",
                volume=volume.id,
                snapshot=snapshot.id,
            )
            return

    if is_monthly:
        expiry_date = now + relativedelta(months=+3)
    else:
        expiry_date = now + relativedelta(days=+7)

    log.debug("Creating snapshot", volume=volume.id, monthly=is_monthly)
    if not dry_run:
        snapshot = os_client.block_storage.create_snapshot(
            volume_id=volume.id,
            description="Automatic daily snapshot",
            is_forced=True,  # create snapshot even if volume is attached
            metadata={"expire_at": expiry_date.date().isoformat()},
        )
        log.info(
            "Created snapshot",
            volume=volume.id,
            snapshot=snapshot.id,
            expire_at=expiry_date.date().isoformat(),
            monthly=is_monthly,
        )


def process_volumes(os_client, dry_run, all_projects):
    """Process all volumes searching for the ones with automatic snapshots"""
    all_projects = True if all_projects else None
    for volume in os_client.block_storage.volumes(
        all_projects=all_projects,
    ):
        if volume.status not in ["available", "in-use"]:
            continue
        log.debug("Processing volume", volume=volume.id)
        if str2bool(volume.metadata.get("automatic_snapshots", "false")):
            create_snapshot_if_needed(
                volume,
                os_client,
                all_projects,
                dry_run,
            )


def cli():
    """Entrypoint for CLI usage"""
    os_client, dry_run, all_projects = setup_cli()

    process_volumes(os_client, dry_run, all_projects)


if __name__ == "__main__":  # pragma: no cover
    cli()

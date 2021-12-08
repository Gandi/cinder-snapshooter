"""This module makes the automatic snapshots

Copyright 2021 Gandi SAS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
import datetime
import os
import sys

import structlog

from dateutil.relativedelta import relativedelta

from .utils import str2bool


log = structlog.get_logger()
cmd_help = "Creates automatic snapshots"


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
            return 0

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
        return 1
    return 0


def process_volumes(os_client, dry_run, all_projects):
    """Process all volumes searching for the ones with automatic snapshots"""
    all_projects = True if all_projects else None
    snapshot_created = 0
    errors = 0
    for volume in os_client.block_storage.volumes(
        all_projects=all_projects,
    ):
        if volume.status not in ["available", "in-use"]:
            continue
        log.debug("Processing volume", volume=volume.id)
        if str2bool(volume.metadata.get("automatic_snapshots", "false")):
            try:
                snapshot_created += create_snapshot_if_needed(
                    volume,
                    os_client,
                    all_projects,
                    dry_run,
                )
            except Exception:
                log.exception("Unable to create snapshot", volume=volume.id)
                errors += 1
    log.info("All volumes processed", snapshot_created=snapshot_created, errors=errors)
    return errors == 0


def register_args(parser):
    """Registers subcommand specific arguments to parse using argparse"""
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Do not create any snapshot, only pretend to",
    )
    parser.add_argument(
        "-a",
        "--all-projects",
        help="Run on all projects",
        action="store_true",
        default="ALL_PROJECTS" in os.environ,
    )


def cli(args):
    """Entrypoint for CLI subcommand"""

    if process_volumes(args.os_client, args.dry_run, args.all_projects):
        return
    sys.exit(1)  # Something went wrong during execution exit with 1

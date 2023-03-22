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
import sys

import structlog

from dateutil.relativedelta import relativedelta
from openstack.block_storage.v3.volume import Volume
from openstack.connection import Connection
from openstack.exceptions import HttpException

from .exceptions import SnapshotInError
from .utils import create_snapshot, delete_snapshot, run_on_all_projects, str2bool


log = structlog.get_logger()
cmd_help = "Creates automatic snapshots"


def create_snapshot_if_needed(
    volume: Volume,
    os_client: Connection,
    wait_completion_timeout: int,
    dry_run: bool,
):
    """Create a snapshot if there isn't one for this volume today
    The snapshot will expire in 7 day unless it is the first of the month where it
    will expire in 3 months
    """
    volume_snapshots = os_client.block_storage.snapshots(
        status="available",
        volume_id=volume.id,
    )
    is_monthly = True
    now = datetime.datetime.now(datetime.timezone.utc)
    created_snapshots = []
    for snapshot in volume_snapshots:
        log.debug(
            "Looking at snapshot",
            snapshot=snapshot.id,
            metadata=snapshot.metadata,
            volume=volume.id,
            project=os_client.current_project_id,
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
                project=os_client.current_project_id,
            )
            return created_snapshots

    if is_monthly:
        expiry_date = now + relativedelta(months=+3)
    else:
        expiry_date = now + relativedelta(days=+7)

    log.debug("Creating snapshot", volume=volume.id, monthly=is_monthly)
    if not dry_run:
        created_snapshots.append(
            create_snapshot(os_client, volume, expiry_date, wait_completion_timeout)
        )

    return created_snapshots


def process_volumes(os_client, wait_completion_timeout, dry_run):
    """Process all volumes searching for the ones with automatic snapshots"""
    snapshot_created = 0
    errors = 0
    in_error = []
    for volume in os_client.block_storage.volumes():
        if volume.status not in ["available", "in-use"]:
            continue
        log.debug("Processing volume", volume=volume.id)
        if str2bool(volume.metadata.get("automatic_snapshots", "false")):
            try:
                snapshot_created += len(
                    create_snapshot_if_needed(
                        volume,
                        os_client,
                        wait_completion_timeout,
                        dry_run,
                    )
                )
            except SnapshotInError as err:
                log.error(
                    "Created snapshot in error",
                    volume=err.snapshot.volume_id,
                    snapshot=err.snapshot.id,
                    project=os_client.current_project_id,
                )
                errors += 1
                in_error.append(err.snapshot)
            except HttpException as err:
                log.error(
                    "Failed to create snapshot",
                    error=err.details,
                    request_id=err.request_id,
                    project=os_client.current_project_id,
                    volume=volume.id,
                )
                errors += 1
            except Exception:
                log.exception(
                    "Unable to create snapshot",
                    volume=volume.id,
                    project=os_client.current_project_id,
                )
                errors += 1

    # Delete failed snapshots right away.
    # We can re-run the tool to try to create them again
    for s in in_error:
        try:
            delete_snapshot(os_client, s, wait_completion_timeout)
        except Exception:
            log.exception(
                "Failed to delete snapshot in error",
                snapshot=s.id,
                project=os_client.current_project_id,
            )

    log.info(
        "All volumes processed for project",
        project=os_client.current_project_id,
        snapshot_created=snapshot_created,
        errors=errors,
    )
    return errors == 0


def register_args(parser):
    """Registers subcommand specific arguments to parse using argparse"""
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Do not create any snapshot, only pretend to",
    )


def cli(args):
    """Entrypoint for CLI subcommand"""
    if not all(
        run_on_all_projects(
            args.os_client,
            process_volumes,
            args.pool_size,
            args.wait_completion_timeout,
            args.dry_run,
        )
    ):
        sys.exit(1)  # Something went wrong during execution exit with 1

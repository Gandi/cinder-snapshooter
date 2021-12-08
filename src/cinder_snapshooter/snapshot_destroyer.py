"""This module destroys the expired automatic snapshots

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


log = structlog.get_logger()
cmd_help = "Destroys expired snapshots"


def process_snapshots(os_client, dry_run, all_projects):
    """Delete every expired snapshot"""
    all_projects = True if all_projects else None
    destroyed_snapshot = 0
    errors = 0
    for snapshot in os_client.block_storage.snapshots(
        all_projects=all_projects, status="available"
    ):
        try:
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
                    destroyed_snapshot += 1
            else:
                log.debug(
                    "Keeping snapshot, still valid",
                    snapshot=snapshot.id,
                    expire_at=expire_at.isoformat(),
                )
        except Exception:
            log.exception("Failed destroying snapshot", snapshot=snapshot.id)
            errors += 1
    log.info(
        "Processed all snapshots", destroyed_snapshot=destroyed_snapshot, errors=errors
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
    parser.add_argument(
        "-a",
        "--all-projects",
        help="Run on all projects",
        action="store_true",
        default="ALL_PROJECTS" in os.environ,
    )


def cli(args):
    """Entrypoint for CLI subcommand"""

    if process_snapshots(args.os_client, args.dry_run, args.all_projects):
        return
    sys.exit(1)  # Something went wrong during execution exit with 1

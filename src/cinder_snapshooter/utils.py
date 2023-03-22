"""Features used by all parts of the package

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
import logging

import eventlet
import keystoneauth1.exceptions
import structlog
from typing import Optional

from openstack.connection import Connection
from openstack.exceptions import ResourceNotFound
from openstack.block_storage.v3.snapshot import Snapshot
from tenacity import (
    Retrying,
    stop_after_attempt,
    stop_after_delay,
    wait_random,
)

from .exceptions import SnapshotStillPresent


log = structlog.get_logger()

DEFAULT_DELETE_RETRIES = 3


def delete_snapshot(
    os_client: Connection,
    snapshot: Snapshot,
    timeout: int,
    retries: Optional[int] = DEFAULT_DELETE_RETRIES,
):
    for attempt in Retrying(
        wait=wait_random(min=1, max=3),
        stop=stop_after_attempt(retries),
        reraise=True,
    ):
        with attempt:
            os_client.block_storage.delete_snapshot(snapshot)

    for attempt in Retrying(
        wait=wait_random(min=1, max=3),
        stop=stop_after_delay(timeout),
        reraise=True,
    ):
        with attempt:
            try:
                os_client.block_storage.get_snapshot(snapshot.id)
            except ResourceNotFound:
                log.info(
                    "Deleted snapshot",
                    snapshot=snapshot.id,
                    project=os_client.current_project_id,
                )
                return True
            raise SnapshotStillPresent(snapshot)


def run_on_all_projects(os_client, process_function, pool_size, *args, **kwargs):
    pool = eventlet.GreenPool(size=pool_size)
    greenlets = []
    for trust_id, project_id in available_projects(os_client):
        log.debug("Processing project", project=project_id, trust=trust_id)
        if trust_id is None:
            os_project_client = os_client.connect_as(project_id=project_id)
        else:
            os_project_client = os_client.connect_as(
                trust_id=trust_id,
            )
        greenlets.append(
            {
                "project_id": project_id,
                "trust_id": trust_id,
                "result": pool.spawn(
                    process_function, os_project_client, *args, **kwargs
                ),
            }
        )

    return_value = []
    for g in greenlets:
        try:
            return_value.append(g["result"].wait())
        except keystoneauth1.exceptions.HTTPClientError as e:
            if e.http_status == 403:
                log.error(
                    "No effective rights on project",
                    project=g["project_id"],
                    req=e.request_id,
                    trust=g["trust_id"],
                )
            else:
                raise

    return return_value


def available_projects(os_client):
    """List all projects we can operate on"""

    for trust in os_client.identity.trusts(trustee_user_id=os_client.current_user_id):
        yield trust.id, trust.project_id
    for project in os_client.identity.user_projects(
        os_client.current_user_id, enabled=True
    ):
        yield None, project.id


def setup_logging(args):
    """Setup logging framework"""
    if args.verbose >= 1:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    time_stamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S")
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        time_stamper,
    ]

    if args.devel:
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()
        shared_processors.append(structlog.processors.format_exc_info)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    logging.getLogger("keystoneauth").setLevel(logging.INFO)
    logging.getLogger("stevedore").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    if args.verbose >= 2:
        logging.getLogger("stevedore").setLevel(logging.DEBUG)
        logging.getLogger("openstack.config").setLevel(logging.DEBUG)
        logging.getLogger("openstack.fnmatch").setLevel(logging.DEBUG)
    if args.verbose >= 3:
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("keystoneauth").setLevel(logging.DEBUG)
    if args.verbose >= 4:
        logging.getLogger("openstack.iterate_timeout").setLevel(logging.DEBUG)


def str2bool(value: str) -> bool:
    """Convert a string to a boolean using the content of the string"""
    return value.lower() in ["true", "yes", "y", "1"]

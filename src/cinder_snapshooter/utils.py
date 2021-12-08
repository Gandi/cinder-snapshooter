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
import argparse
import logging
import os

import openstack
import structlog


def register_args(parser: argparse.ArgumentParser):
    """Registers arguments to parse using argparse"""
    parser.add_argument(
        "--os-cloud",
        dest="os_cloud",
        default=os.environ.get("OS_CLOUD"),
        help="The cloud to connect to",
    )
    parser.add_argument(
        "-a",
        "--all-projects",
        help="Run on all projects",
        action="store_true",
        default="ALL_PROJECTS" in os.environ,
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Do not create any snapshot, only pretend to",
    )

    logging_group = parser.add_argument_group(
        "logging",
        "logging specific options",
    )
    logging_group.add_argument(
        "--devel", help="print logs in human readable format", action="store_true"
    )
    logging_group.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase output verbosity",
    )


def setup_cli():
    """Setup CLI argument parsing and logging"""
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()

    setup_logging(args)

    os_client = openstack.connect(cloud=args.os_cloud)

    return os_client, args.dry_run, args.all_projects


def setup_logging(args):
    """Setup logging framework"""
    if args.devel:
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

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
    return value.lower() in ["true", "yes"]

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

import structlog


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
    return value.lower() in ["true", "yes"]

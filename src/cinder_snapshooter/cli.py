import eventlet


eventlet.monkey_patch()

import argparse
import os

import openstack

from . import snapshot_creator, snapshot_destroyer
from .utils import setup_logging


SUBCOMMANDS = {"creator": snapshot_creator, "destroyer": snapshot_destroyer}


def register_common_args(parser):
    parser.add_argument(
        "--os-cloud",
        dest="os_cloud",
        default=os.environ.get("OS_CLOUD"),
        help="The cloud to connect to",
    )
    parser.add_argument(
        "--pool-size",
        dest="pool_size",
        default=os.environ.get("POOL_SIZE", 20),
        type=int,
        help="The number of snapshots to be processed concurrently",
    )
    parser.add_argument(
        "--wait-completion-timeout",
        dest="wait_completion_timeout",
        default=os.environ.get("WAIT_COMPLETION_TIMEOUT", 30),
        type=int,
        help="The time in seconds to wait for snapshot creation/deletion completion",
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


def parse_args(args=None):
    parser = argparse.ArgumentParser("cinder-snapshooter")
    register_common_args(parser)
    sub_parser = parser.add_subparsers(required=True)

    for name, module in SUBCOMMANDS.items():
        subcommand_parser = sub_parser.add_parser(name, help=module.cmd_help)
        module.register_args(subcommand_parser)
        subcommand_parser.set_defaults(func=module.cli)

    return parser.parse_args(args)


def cli():
    args = parse_args()
    setup_logging(args)
    args.os_client = openstack.connect(cloud=args.os_cloud)

    args.func(args)

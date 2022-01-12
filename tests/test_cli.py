import argparse

import openstack
import pytest

import cinder_snapshooter.cli
import cinder_snapshooter.snapshot_creator
import cinder_snapshooter.snapshot_destroyer


@pytest.mark.parametrize(
    "args,result",
    [
        (
            ["--os-cloud", "hello", "--devel", "creator"],
            argparse.Namespace(
                os_cloud="hello",
                devel=True,
                dry_run=False,
                verbose=0,
                func=cinder_snapshooter.snapshot_creator.cli,
            ),
        ),
        (
            ["--os-cloud", "hello", "--devel", "-vvv", "destroyer"],
            argparse.Namespace(
                os_cloud="hello",
                devel=True,
                dry_run=False,
                verbose=3,
                func=cinder_snapshooter.snapshot_destroyer.cli,
            ),
        ),
    ],
)
def test_parse_args(args, result):
    assert cinder_snapshooter.cli.parse_args(args) == result


def test_cli(mocker, faker):
    mocker.patch("cinder_snapshooter.cli.parse_args")
    mocker.patch("cinder_snapshooter.cli.setup_logging")
    mocker.patch("openstack.connect")
    args = argparse.Namespace(os_cloud=faker.word(), func=mocker.MagicMock())
    os_client = mocker.MagicMock()
    openstack.connect.return_value = os_client
    cinder_snapshooter.cli.parse_args.return_value = args

    cinder_snapshooter.cli.cli()

    openstack.connect.assert_called_once_with(cloud=args.os_cloud)
    assert args.os_client == os_client
    args.func.assert_called_once_with(args)
    cinder_snapshooter.cli.setup_logging.assert_called_once_with(args)

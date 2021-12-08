"""
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
import datetime
import sys

import pytest

import cinder_snapshooter.snapshot_destroyer

from fixtures import FakeSnapshot


@pytest.mark.parametrize("success", [True, False])
def test_cli(mocker, faker, success):
    mocker.patch("cinder_snapshooter.snapshot_destroyer.process_snapshots")
    mocker.patch("sys.exit")
    cinder_snapshooter.snapshot_destroyer.process_snapshots.return_value = success
    fake_args = argparse.Namespace(
        dry_run=faker.boolean(),
        all_projects=faker.boolean(),
        os_client=mocker.MagicMock(),
    )
    cinder_snapshooter.snapshot_destroyer.cli(fake_args)
    cinder_snapshooter.snapshot_destroyer.process_snapshots.assert_called_once_with(
        fake_args.os_client,
        fake_args.dry_run,
        fake_args.all_projects,
    )
    if not success:
        sys.exit.assert_called_once_with(1)


@pytest.mark.parametrize("dry_run", [True, False], ids=["dry-run", "real-run"])
@pytest.mark.parametrize(
    "all_projects", [True, False], ids=["all-projects", "single-project"]
)
@pytest.mark.parametrize("success", [True, False])
def test_process_snapshots(
    mocker, faker, log, time_machine, dry_run, all_projects, success
):
    os_client = mocker.MagicMock()
    manual_snapshots = [
        FakeSnapshot(
            id=faker.uuid4(),
            status="available",
            created_at=faker.date_time_this_century(
                tzinfo=datetime.timezone.utc
            ).isoformat(),
            volume_id=faker.uuid4(),
            metadata={},
        )
        for i in range(10)
    ]

    now = faker.date_time_this_century(tzinfo=datetime.timezone.utc)
    time_machine.move_to(now)
    expired_snapshot = [
        FakeSnapshot(
            id=faker.uuid4(),
            status="available",
            created_at=faker.date_time_this_century(
                tzinfo=datetime.timezone.utc
            ).isoformat(),
            volume_id=faker.uuid4(),
            metadata={"expire_at": faker.date(end_datetime=now)},
        )
        for i in range(10)
    ]
    nok_snapshot = []
    if not success:
        nok_snapshot = [
            FakeSnapshot(
                id=faker.uuid4(),
                status="available",
                created_at=faker.date_time_this_century(
                    tzinfo=datetime.timezone.utc
                ).isoformat(),
                volume_id=faker.uuid4(),
                metadata={"expire_at": faker.date(end_datetime=now)},
            )
            for i in range(10)
        ]
    not_expired_snapshot = [
        FakeSnapshot(
            id=faker.uuid4(),
            status="available",
            created_at=faker.date_time_this_century(
                tzinfo=datetime.timezone.utc
            ).isoformat(),
            volume_id=faker.uuid4(),
            metadata={
                "expire_at": faker.date_this_century(
                    before_today=False, after_today=True
                ).isoformat()
            },
        )
    ]
    snapshots = (
        manual_snapshots + not_expired_snapshot + expired_snapshot + nok_snapshot
    )
    os_client.block_storage.snapshots.return_value = snapshots

    def delete_snapshot(isnapshot):
        if isnapshot in nok_snapshot:
            raise Exception()
        return 1

    os_client.block_storage.delete_snapshot.side_effect = delete_snapshot

    assert (
        cinder_snapshooter.snapshot_destroyer.process_snapshots(
            os_client, dry_run, all_projects
        )
        == success
        or dry_run
    )
    if not all_projects:
        all_projects = None

    os_client.block_storage.snapshots.assert_called_once_with(
        all_projects=all_projects, status="available"
    )
    if dry_run:
        os_client.block_storage.delete_snapshot.assert_not_called()
        return

    assert os_client.block_storage.delete_snapshot.call_count == len(
        expired_snapshot
    ) + len(nok_snapshot)
    for snapshot in expired_snapshot + nok_snapshot:
        os_client.block_storage.delete_snapshot.assert_any_call(snapshot)
    assert log.has(
        "Processed all snapshots",
        destroyed_snapshot=len(expired_snapshot),
        errors=len(nok_snapshot),
    )

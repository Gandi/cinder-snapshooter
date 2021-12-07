import datetime

import pytest

import cinder_snapshooter.snapshot_destroyer
from fixtures import FakeSnapshot


def test_cli(mocker, faker):
    mocker.patch("cinder_snapshooter.snapshot_destroyer.setup_cli")
    mocker.patch("cinder_snapshooter.snapshot_destroyer.process_snapshots")
    fake_return = (mocker.MagicMock(), faker.boolean, faker.boolean)
    cinder_snapshooter.snapshot_destroyer.setup_cli.return_value = fake_return
    cinder_snapshooter.snapshot_destroyer.cli()
    cinder_snapshooter.snapshot_destroyer.setup_cli.assert_called_once_with()
    cinder_snapshooter.snapshot_destroyer.process_snapshots.assert_called_once_with(
        *fake_return
    )


@pytest.mark.parametrize("dry_run", [True, False], ids=["dry-run", "real-run"])
@pytest.mark.parametrize(
    "all_projects", [True, False], ids=["all-projects", "single-project"]
)
def test_process_snapshots(mocker, faker, time_machine, dry_run, all_projects):
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
    snapshots = manual_snapshots + not_expired_snapshot + expired_snapshot
    os_client.block_storage.snapshots.return_value = snapshots

    cinder_snapshooter.snapshot_destroyer.process_snapshots(
        os_client, dry_run, all_projects
    )
    if not all_projects:
        all_projects = None

    os_client.block_storage.snapshots.assert_called_once_with(
        all_projects=all_projects, status="available"
    )
    if dry_run:
        os_client.block_storage.delete_snapshot.assert_not_called()
        return

    assert os_client.block_storage.delete_snapshot.call_count == len(expired_snapshot)
    for snapshot in expired_snapshot:
        os_client.block_storage.delete_snapshot.assert_any_call(snapshot)

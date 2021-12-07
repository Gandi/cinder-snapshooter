import pytest

import cinder_snapshooter.utils


@pytest.mark.parametrize(
    "value, result",
    [
        ("true", True),
        ("TRUE", True),
        ("True", True),
        ("yes", True),
        ("wrong", False),
        ("FALSE", False),
        ("no", False),
        ("random string", False),
    ],
)
def test_str2bool(value, result):
    assert cinder_snapshooter.utils.str2bool(value) == result

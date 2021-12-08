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

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
from dataclasses import dataclass


@dataclass
class FakeVolume:
    id: str
    status: str
    metadata: dict


@dataclass
class FakeSnapshot:
    id: str
    status: str
    metadata: dict
    volume_id: str
    created_at: str


@dataclass
class FakeProject:
    id: str
    name: str


@dataclass
class FakeTrust:
    id: str
    project_id: str

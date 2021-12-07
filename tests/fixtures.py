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

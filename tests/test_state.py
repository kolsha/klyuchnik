from __future__ import annotations

from pathlib import Path

from klyuchnik.state import JsonPinStateStore, PinStateStore


async def test_load_returns_none_when_file_missing(tmp_path: Path) -> None:
    store: PinStateStore = JsonPinStateStore(tmp_path / "state.json")
    assert await store.load(-1001) is None


async def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    store = JsonPinStateStore(tmp_path / "state.json")
    await store.save(-1001, 42)
    assert await store.load(-1001) == 42


async def test_save_overwrites(tmp_path: Path) -> None:
    store = JsonPinStateStore(tmp_path / "state.json")
    await store.save(-1001, 1)
    await store.save(-1001, 2)
    assert await store.load(-1001) == 2


async def test_clear_removes_value(tmp_path: Path) -> None:
    store = JsonPinStateStore(tmp_path / "state.json")
    await store.save(-1001, 99)
    await store.clear(-1001)
    assert await store.load(-1001) is None


async def test_state_is_per_chat(tmp_path: Path) -> None:
    store = JsonPinStateStore(tmp_path / "state.json")
    await store.save(1, 10)
    await store.save(2, 20)
    assert await store.load(1) == 10
    assert await store.load(2) == 20


async def test_load_ignores_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("not json", encoding="utf-8")
    store = JsonPinStateStore(path)
    assert await store.load(-1001) is None


async def test_persists_to_disk_between_instances(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    s1 = JsonPinStateStore(path)
    await s1.save(-1001, 7)

    s2 = JsonPinStateStore(path)
    assert await s2.load(-1001) == 7

"""Tests for wanwatcher.state: persistence, migrations, history."""

import json
import os

from wanwatcher.state import HISTORY_LIMIT, State, StateStore


def make_store(tmp_path, legacy_update_file=None):
    return StateStore(
        str(tmp_path / "ipinfo.db"),
        legacy_update_file=legacy_update_file,
    )


class TestLoadSaveRoundtrip:
    def test_first_run_returns_empty_state(self, tmp_path):
        store = make_store(tmp_path)
        state = store.load()
        assert state.is_empty()
        assert state.history == []

    def test_roundtrip_preserves_fields(self, tmp_path):
        store = make_store(tmp_path)
        state = State(
            ipv4="8.8.8.8",
            ipv6="2606:4700:4700::1111",
            update_notified_version="2.1.0",
        )
        store.save(state)

        loaded = store.load()
        assert loaded.ipv4 == "8.8.8.8"
        assert loaded.ipv6 == "2606:4700:4700::1111"
        assert loaded.update_notified_version == "2.1.0"
        assert loaded.last_updated is not None

    def test_save_stamps_last_updated(self, tmp_path):
        store = make_store(tmp_path)
        state = State(ipv4="8.8.8.8")
        assert state.last_updated is None
        store.save(state)
        assert state.last_updated is not None

    def test_save_creates_missing_directory(self, tmp_path):
        store = StateStore(str(tmp_path / "nested" / "dir" / "ipinfo.db"))
        store.save(State(ipv4="8.8.8.8"))
        assert store.load().ipv4 == "8.8.8.8"


class TestAtomicity:
    def test_file_is_valid_json_after_save(self, tmp_path):
        store = make_store(tmp_path)
        store.save(State(ipv4="8.8.8.8"))
        with open(store.path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["ipv4"] == "8.8.8.8"

    def test_no_temp_files_left_behind(self, tmp_path):
        store = make_store(tmp_path)
        store.save(State(ipv4="8.8.8.8"))
        store.save(State(ipv4="9.9.9.9"))
        leftovers = [name for name in os.listdir(tmp_path) if name != "ipinfo.db"]
        assert leftovers == []


class TestMigrations:
    def test_plain_text_file_migrates_to_ipv4(self, tmp_path):
        path = tmp_path / "ipinfo.db"
        path.write_text("8.8.8.8\n", encoding="utf-8")
        state = StateStore(str(path)).load()
        assert state.ipv4 == "8.8.8.8"
        assert state.ipv6 is None

    def test_bare_json_string_migrates_to_ipv4(self, tmp_path):
        path = tmp_path / "ipinfo.db"
        path.write_text('"8.8.8.8"', encoding="utf-8")
        state = StateStore(str(path)).load()
        assert state.ipv4 == "8.8.8.8"

    def test_v1_dict_format_is_read(self, tmp_path):
        path = tmp_path / "ipinfo.db"
        payload = {
            "ipv4": "8.8.8.8",
            "ipv6": "2606:4700:4700::1111",
            "last_updated": "2026-01-01T00:00:00+00:00",
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        state = StateStore(str(path)).load()
        assert state.ipv4 == "8.8.8.8"
        assert state.ipv6 == "2606:4700:4700::1111"
        assert state.history == []

    def test_unexpected_json_structure_starts_fresh(self, tmp_path):
        path = tmp_path / "ipinfo.db"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        state = StateStore(str(path)).load()
        assert state.is_empty()

    def test_corrupted_non_json_content_treated_as_plain_text(self, tmp_path):
        # Arbitrary garbage is indistinguishable from the v0 plain-text
        # format, so it is absorbed as an ipv4 string without crashing.
        path = tmp_path / "ipinfo.db"
        path.write_text("{not valid json", encoding="utf-8")
        state = StateStore(str(path)).load()
        assert state.ipv4 == "{not valid json"

    def test_empty_file_returns_empty_state(self, tmp_path):
        path = tmp_path / "ipinfo.db"
        path.write_text("", encoding="utf-8")
        state = StateStore(str(path)).load()
        assert state.is_empty()


class TestLegacyUpdateFile:
    def test_legacy_marker_absorbed_and_deleted_on_first_run(self, tmp_path):
        legacy = tmp_path / "update_notified.txt"
        legacy.write_text("1.4.1\n", encoding="utf-8")
        store = make_store(tmp_path, legacy_update_file=str(legacy))

        state = store.load()
        assert state.update_notified_version == "1.4.1"
        assert not legacy.exists()

    def test_legacy_marker_absorbed_during_plain_text_migration(self, tmp_path):
        path = tmp_path / "ipinfo.db"
        path.write_text("8.8.8.8", encoding="utf-8")
        legacy = tmp_path / "update_notified.txt"
        legacy.write_text("1.4.1", encoding="utf-8")
        store = StateStore(str(path), legacy_update_file=str(legacy))

        state = store.load()
        assert state.ipv4 == "8.8.8.8"
        assert state.update_notified_version == "1.4.1"
        assert not legacy.exists()

    def test_state_value_wins_over_legacy_file(self, tmp_path):
        path = tmp_path / "ipinfo.db"
        path.write_text(
            json.dumps({"ipv4": "8.8.8.8", "update_notified_version": "2.0.0"}),
            encoding="utf-8",
        )
        legacy = tmp_path / "update_notified.txt"
        legacy.write_text("1.4.1", encoding="utf-8")
        store = StateStore(str(path), legacy_update_file=str(legacy))

        state = store.load()
        assert state.update_notified_version == "2.0.0"
        assert legacy.exists()  # untouched when the state already has a value

    def test_missing_legacy_file_is_fine(self, tmp_path):
        store = make_store(
            tmp_path, legacy_update_file=str(tmp_path / "does_not_exist.txt")
        )
        state = store.load()
        assert state.update_notified_version is None


class TestRecordChange:
    def test_appends_history_entry_and_stamps_last_change(self, tmp_path):
        store = make_store(tmp_path)
        state = State(ipv4="9.9.9.9", ipv6=None)
        store.record_change(state, old_ipv4="8.8.8.8", old_ipv6=None)

        assert state.last_change is not None
        assert len(state.history) == 1
        entry = state.history[0]
        assert entry["old_ipv4"] == "8.8.8.8"
        assert entry["new_ipv4"] == "9.9.9.9"
        assert entry["old_ipv6"] is None
        assert entry["new_ipv6"] is None
        assert entry["at"] == state.last_change

    def test_history_is_trimmed_to_limit(self, tmp_path):
        store = make_store(tmp_path)
        state = State(ipv4="9.9.9.9")
        for index in range(HISTORY_LIMIT + 5):
            state.ipv4 = f"9.9.9.{index}"
            store.record_change(state, old_ipv4="8.8.8.8", old_ipv6=None)

        assert len(state.history) == HISTORY_LIMIT
        # The oldest entries were dropped; the latest is kept.
        assert state.history[-1]["new_ipv4"] == f"9.9.9.{HISTORY_LIMIT + 4}"

    def test_history_survives_roundtrip(self, tmp_path):
        store = make_store(tmp_path)
        state = State(ipv4="9.9.9.9")
        store.record_change(state, old_ipv4="8.8.8.8", old_ipv6=None)
        store.save(state)

        loaded = store.load()
        assert len(loaded.history) == 1
        assert loaded.last_change == state.last_change

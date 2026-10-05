"""GREEN contract tests for ``config.py`` pure helpers (finish-neutral).

These tests pin the STABLE behavioral contract of the configuration module's
pure, side-effect-light helpers. They touch no engine / paint / spec math and
start no Flask server -- they only import ``config`` (cheap) and exercise its
documented public surface.

This file complements (does NOT duplicate) the other tests_v2 files:
  * The path-traversal guards already covered in tests_v2 live in
    ``server_routes/*`` (``_raw_path_is_traversal`` / ``_resolve_within_roots``,
    pinned by test_server_contract.py and test_route_and_manifest_contracts.py).
    Those are a DIFFERENT implementation from ``config.is_safe_path``; no other
    tests_v2 file imports ``config`` at all, so the entire surface below is new.

Contracts pinned here:
  * config.is_safe_path(base_dir, target): accepts in-root / nested filenames,
    rejects ``..`` traversal that escapes the root and absolute paths outside it
    (anti-traversal), and returns a bool (never raises) on bad input.
  * config.normalize_path(path): returns an absolute, normalised path; raises
    TypeError on a non-str argument (documented contract).
  * config.validate_config(data): returns a list of error strings ([] == valid),
    treats missing keys as non-errors, flags wrong-typed keys, and returns a
    (non-raising) error list -- not an exception -- for a non-dict argument.
  * config.repair_config(data): returns a dict that always passes
    validate_config, fills schema defaults, preserves unknown keys, and tolerates
    non-dict / None input.
  * config.CFG.as_dict() vs as_public_dict(): the public dict is a subset that
    STRIPS the filesystem ``root`` key (path-leak hardening) while keeping the
    safe version/build/port/host/debug fields.
  * Module constants: DEFAULT_PORT is the documented value and in TCP range;
    CONFIG_MODULE_VERSION is a non-empty string; __all__ exposes the helpers.
"""
from __future__ import annotations

import os
import tempfile

import pytest

import config


# --------------------------------------------------------------------------- #
# is_safe_path -- anti-traversal contract
# --------------------------------------------------------------------------- #
class TestIsSafePath:
    def test_accepts_plain_in_root_filename(self):
        with tempfile.TemporaryDirectory() as d:
            assert config.is_safe_path(d, "asset.png") is True

    def test_accepts_nested_in_root_path(self):
        with tempfile.TemporaryDirectory() as d:
            assert config.is_safe_path(d, os.path.join("sub", "dir", "a.png")) is True

    def test_accepts_empty_target_resolving_to_root_itself(self):
        # "" joins to base_dir, which is trivially inside base_dir.
        with tempfile.TemporaryDirectory() as d:
            assert config.is_safe_path(d, "") is True

    def test_rejects_dotdot_traversal_escaping_root(self):
        with tempfile.TemporaryDirectory() as d:
            escape = os.path.join("..", "..", "etc", "passwd")
            assert config.is_safe_path(d, escape) is False

    def test_rejects_absolute_path_outside_root(self):
        with tempfile.TemporaryDirectory() as d:
            # Filesystem root is never inside a tempdir under it.
            outside = os.path.abspath(os.sep)
            assert config.is_safe_path(d, outside) is False

    def test_returns_bool_and_never_raises(self):
        # Contract: on any error the function returns False rather than raising.
        with tempfile.TemporaryDirectory() as d:
            assert isinstance(config.is_safe_path(d, "ok.txt"), bool)
            assert isinstance(config.is_safe_path(d, os.path.join("..", "x")), bool)


# --------------------------------------------------------------------------- #
# normalize_path
# --------------------------------------------------------------------------- #
class TestNormalizePath:
    def test_returns_absolute_path(self):
        assert os.path.isabs(config.normalize_path("foo/bar"))

    def test_collapses_relative_segments(self):
        result = config.normalize_path(os.path.join("a", "b", "..", "c"))
        # The collapsed leaf must be 'c', not '..'.
        assert os.path.basename(result) == "c"
        assert ".." not in result.split(os.sep)

    def test_raises_typeerror_on_non_str(self):
        with pytest.raises(TypeError):
            config.normalize_path(123)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# validate_config
# --------------------------------------------------------------------------- #
class TestValidateConfig:
    def test_valid_dict_has_no_errors(self):
        assert config.validate_config({"iracing_id": "1", "car_paths": {}}) == []

    def test_missing_keys_are_not_errors(self):
        # Missing keys fall back to defaults; an empty dict is valid.
        assert config.validate_config({}) == []

    def test_wrong_typed_key_is_reported(self):
        errs = config.validate_config({"live_link_enabled": "yes"})
        assert isinstance(errs, list)
        assert len(errs) == 1
        assert "live_link_enabled" in errs[0]

    def test_non_dict_returns_error_list_not_raise(self):
        errs = config.validate_config([1, 2, 3])
        assert isinstance(errs, list)
        assert len(errs) == 1
        assert "dict" in errs[0]

    def test_none_or_str_active_car_is_valid(self):
        # active_car accepts (str, None) per the schema.
        assert config.validate_config({"active_car": None}) == []
        assert config.validate_config({"active_car": "ferrari"}) == []


# --------------------------------------------------------------------------- #
# repair_config
# --------------------------------------------------------------------------- #
class TestRepairConfig:
    def test_repaired_empty_dict_is_valid(self):
        assert config.validate_config(config.repair_config({})) == []

    def test_repaired_none_is_valid_dict(self):
        repaired = config.repair_config(None)
        assert isinstance(repaired, dict)
        assert config.validate_config(repaired) == []

    def test_fills_schema_defaults(self):
        repaired = config.repair_config({})
        assert repaired.get("iracing_id") == "23371"
        assert repaired.get("car_paths") == {}
        assert repaired.get("live_link_enabled") is False

    def test_fixes_wrong_typed_key_to_default(self):
        repaired = config.repair_config({"live_link_enabled": "yes"})
        assert config.validate_config(repaired) == []
        assert repaired.get("live_link_enabled") is False

    def test_preserves_unknown_keys(self):
        repaired = config.repair_config({"extra_unknown": 99})
        assert repaired.get("extra_unknown") == 99

    def test_returns_new_dict_not_same_object(self):
        src = {"iracing_id": "1"}
        repaired = config.repair_config(src)
        assert repaired is not src


# --------------------------------------------------------------------------- #
# CFG.as_dict vs CFG.as_public_dict -- path-leak hardening
# --------------------------------------------------------------------------- #
class TestPublicDictStripsPaths:
    def test_as_dict_includes_root_path(self):
        assert "root" in config.CFG.as_dict()

    def test_public_dict_strips_root_path(self):
        assert "root" not in config.CFG.as_public_dict()

    def test_public_dict_is_subset_of_full_dict(self):
        full = config.CFG.as_dict()
        public = config.CFG.as_public_dict()
        assert set(public).issubset(set(full))

    def test_public_dict_keeps_safe_fields(self):
        public = config.CFG.as_public_dict()
        assert {"version", "build", "port", "host", "debug"}.issubset(set(public))

    def test_public_dict_values_match_full_dict(self):
        full = config.CFG.as_dict()
        public = config.CFG.as_public_dict()
        for k, v in public.items():
            assert full[k] == v


# --------------------------------------------------------------------------- #
# Module-level constants & exports
# --------------------------------------------------------------------------- #
class TestModuleConstants:
    def test_default_port_value(self):
        assert config.DEFAULT_PORT == 59876

    def test_default_port_in_tcp_range(self):
        assert 1024 <= config.DEFAULT_PORT <= 65535

    def test_config_module_version_is_nonempty_str(self):
        assert isinstance(config.CONFIG_MODULE_VERSION, str)
        assert config.CONFIG_MODULE_VERSION

    def test_all_exports_expose_helpers(self):
        expected = {"is_safe_path", "normalize_path", "validate_config",
                    "repair_config", "CFG"}
        assert expected.issubset(set(config.__all__))

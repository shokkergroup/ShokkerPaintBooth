from __future__ import annotations

import pytest

from _forge_dlm_surface_identity_alias import SurfaceIdentityAliasError


def test_surface_alias_rejects_duplicate_physical_identity() -> None:
    aliases = {"rear_deck_lid": "hood", "tub": "hood"}
    with pytest.raises(SurfaceIdentityAliasError, match="aliases_not_one_to_one"):
        if len(set(aliases.values())) != len(aliases):
            raise SurfaceIdentityAliasError("aliases_not_one_to_one")

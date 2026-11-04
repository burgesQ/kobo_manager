from pathlib import Path

import pytest

from kobocore.state import Phase, PhaseError, PipelineState


def test_out_of_order_phase_is_refused(tmp_path: Path) -> None:
    state = PipelineState("N428TEST", root=tmp_path)
    with pytest.raises(PhaseError):
        state.require(Phase.FLASHED)


def test_mark_persists_and_dry_run_does_not(tmp_path: Path) -> None:
    PipelineState("N428TEST", root=tmp_path).mark(Phase.BACKED_UP, dry_run=True)
    assert not PipelineState("N428TEST", root=tmp_path).has(Phase.BACKED_UP)
    PipelineState("N428TEST", root=tmp_path).mark(Phase.BACKED_UP)
    reloaded = PipelineState("N428TEST", root=tmp_path)
    assert reloaded.has(Phase.BACKED_UP)
    reloaded.require(Phase.VERIFIED)

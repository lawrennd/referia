"""CIP-0013 Phase C: compute prep / registry smoke coverage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from referia.assess.compute import Compute
from referia.config.interface import Interface


def _iface(payload=None):
    return Interface(
        payload or {"input": {"type": "local", "index": "i", "data": [{"i": 0}]}},
        user_file="test.yml",
        directory=".",
    )


class TestPrepAll:
    def test_prep_all_registers_pre_compute_post(self):
        # Construct Compute without compute entries (parent init can stall on
        # unresolved function names), then call prep_all with a patched prep.
        compute = Compute(_iface())
        data = MagicMock()
        iface = {
            "precompute": {"function": "render_liquid", "args": {"template": "x"}},
            "compute": [{"function": "render_liquid", "args": {"template": "y"}}],
            "postcompute": {"function": "render_liquid", "args": {"template": "z"}},
        }
        with patch.object(
            compute, "prep", side_effect=lambda c, d: {"function": MagicMock(), "args": {}}
        ) as prep:
            compute.prep_all(iface, data)
        assert prep.call_count == 3
        assert len(compute._computes["precompute"]) == 1
        assert len(compute._computes["compute"]) == 1
        assert len(compute._computes["postcompute"]) == 1


class TestPreprocess:
    def test_preprocess_runs_ops_and_filter(self):
        compute = Compute(_iface())
        iface = {
            "compute": {
                "preprocessor": {"function": "noop", "field": "out"},
                "filter": {"function": "keep_all"},
            },
        }
        frame = MagicMock()
        frame.index = pd.Index([0, 1])
        frame.__setitem__ = MagicMock()
        frame.filter_row = MagicMock()

        def fake_prep(compute_spec, data=None):
            if compute_spec.get("function") == "noop":
                return {"function": MagicMock(return_value="done"), "args": {}}
            return {
                "function": MagicMock(
                    return_value=pd.Series([True, False], index=frame.index)
                ),
                "args": {},
            }

        with patch("lynguine.assess.compute.Compute.preprocess", return_value=None):
            with patch.object(compute, "prep", side_effect=fake_prep):
                compute.preprocess(frame, iface)
        frame.filter_row.assert_called_once()
        frame.__setitem__.assert_called()


class TestRegistrySmoke:
    def test_compute_functions_list_has_referia_entries(self):
        compute = Compute(_iface())
        names = {e["name"] for e in compute._compute_functions_list()}
        assert names
        assert any(
            "liquid" in n or "word_count" in n or "mppca" in n or "topic" in n
            for n in names
        )

    def test_llm_functions_list_method_exists(self):
        compute = Compute(_iface())
        assert callable(compute._llm_functions_list)

    def test_run_stores_interface(self):
        compute = Compute(_iface())
        data = MagicMock()
        iface = {"compute": []}
        with patch("lynguine.assess.compute.Compute.run", return_value=None) as parent_run:
            compute.run(data, iface)
        assert compute.interface is iface
        assert compute._data is data
        parent_run.assert_called_once()

    def test_run_onchange_delegates(self):
        compute = Compute(_iface())
        with patch("lynguine.assess.compute.Compute.run_onchange", return_value=None) as parent:
            compute.run_onchange(MagicMock(), 0, "col")
        parent.assert_called_once()

"""Convergence-guard tests (Prompt 6b / Stage D).

The guard exists because a loose escalate threshold oscillates: each redraft surfaces a new
structural wrinkle and the loop never ends. These tests pin the three things that make it
terminate — a rising tau, a hard K_MAX, and a bounded deepen path — and the two ways a
non-converging trajectory is surfaced rather than hidden.
"""

from checks import convergence as conv_checks
from ir.schema import Concept, ConceptMap, ConvergenceLog, DocumentIR, Section
from research import convergence
from research.planner import (
    ScriptedStructureJudge,
    build_contested_block,
    run_convergence_loop,
    write_convergence,
)


def cmap(*specs, contested=False):
    """cmap(("term", ["C1","C2"]), ...) -> a ConceptMap with those concepts."""
    concepts = []
    for i, spec in enumerate(specs, start=1):
        term, claims = spec[0], spec[1]
        extra = spec[2] if len(spec) > 2 else {}
        concepts.append(Concept(concept_id=f"c{i}-{term}", canonical_term=term,
                                claim_ids=list(claims), salience=1.0 - i * 0.1, **extra))
    return ConceptMap(concepts=concepts, contested=contested)


# --- tau schedule + escalation (the termination argument) --------------------

def test_tau_rises_then_becomes_unreachable():
    assert convergence.tau(0) == 4.0
    assert convergence.tau(1) == 6.0
    assert convergence.tau(2) == 9.0
    assert convergence.tau(convergence.K_MAX) == float("inf")


def test_escalate_requires_both_threshold_and_headroom():
    assert convergence.escalate(10.0, cycle=0) is True
    assert convergence.escalate(1.0, cycle=0) is False          # below tau -> deepen instead
    assert convergence.escalate(10_000.0, cycle=convergence.K_MAX) is False   # cap wins


def test_rho_is_none_without_a_previous_cycle():
    assert convergence.rho(4.0, None) is None
    assert convergence.rho(2.0, 4.0) == 0.5


# --- struct_distance ----------------------------------------------------------

def test_identical_maps_are_distance_zero():
    a = cmap(("chunking", ["C1", "C2"]), ("reranking", ["C3"]))
    assert convergence.struct_distance(a, a) == 0.0


def test_rename_alone_is_free():
    """alias_rename weighs 0: univocity owns naming, the guard owns structure."""
    a = cmap(("chunking", ["C1", "C2"]))
    b = cmap(("chunk splitting", ["C1", "C2"]))
    assert convergence.struct_distance(a, b) == 0.0


def test_concept_split_costs_more_than_a_claim_moving():
    base = cmap(("chunking", ["C1", "C2", "C3"]))
    split = cmap(("chunking", ["C1", "C2"]), ("windowing", ["C3"]))
    moved = cmap(("chunking", ["C1", "C2"]), ("reranking", ["C3"]))
    assert convergence.struct_distance(base, split) >= convergence.EDIT_WEIGHTS["concept_split_merge"]
    assert convergence.struct_distance(base, split) > 0
    assert convergence.struct_distance(moved, moved) == 0


def test_new_claim_entering_the_map_is_a_leaf_edit():
    a = cmap(("chunking", ["C1"]))
    b = cmap(("chunking", ["C1", "C2"]))
    assert convergence.struct_distance(a, b) == EXPECTED_LEAF_ADD


EXPECTED_LEAF_ADD = convergence.EDIT_WEIGHTS["leaf_add_remove"]


def test_anchor_change_is_the_heaviest_single_edit():
    a = cmap(("chunking", ["C1"], {"home_anchor": "index granularity"}))
    b = cmap(("chunking", ["C1"], {"home_anchor": "cache line size"}))
    assert convergence.struct_distance(a, b) == convergence.EDIT_WEIGHTS["home_anchor_or_framing"]


def test_reordering_by_salience_is_a_structural_edit():
    a = ConceptMap(concepts=[
        Concept(concept_id="c1", canonical_term="alpha", claim_ids=["C1"], salience=0.9),
        Concept(concept_id="c2", canonical_term="beta", claim_ids=["C2"], salience=0.4)])
    b = ConceptMap(concepts=[
        Concept(concept_id="c1", canonical_term="alpha", claim_ids=["C1"], salience=0.4),
        Concept(concept_id="c2", canonical_term="beta", claim_ids=["C2"], salience=0.9)])
    assert convergence.struct_distance(a, b) == convergence.EDIT_WEIGHTS["section_add_remove_reorder"]


def test_distance_is_symmetric():
    a = cmap(("chunking", ["C1", "C2"]))
    b = cmap(("chunking", ["C1"]), ("windowing", ["C2", "C3"]))
    assert convergence.struct_distance(a, b) == convergence.struct_distance(b, a)


def test_concepts_match_across_cycles_by_claims_not_ids():
    """Curation regenerates ids and may rename; identity has to follow the evidence."""
    a = cmap(("chunking", ["C1", "C2", "C3"]))
    b = cmap(("chunk splitting", ["C1", "C2", "C3"]))
    pairs, only_a, only_b = convergence.match_concepts(a, b)
    assert len(pairs) == 1 and not only_a and not only_b


# --- trajectory classification ------------------------------------------------

def test_stable_trajectory_is_converged():
    maps = [cmap(("chunking", ["C1", "C2"])) for _ in range(3)]
    assert convergence.classify_trajectory(maps) == "converged"


def test_oscillating_between_two_shapes_is_contested():
    by_stage = cmap(("retrieval stage", ["C1", "C2"]), ("generation stage", ["C3", "C4"]))
    by_index = cmap(("flat index", ["C1", "C3"]), ("graph index", ["C2", "C4"]))
    assert convergence.classify_trajectory([by_stage, by_index, by_stage, by_index]) == "contested"


def test_wandering_trajectory_is_chaotic():
    maps = [cmap((f"shape{i}", [f"C{i}a", f"C{i}b"])) for i in range(5)]
    assert convergence.classify_trajectory(maps) == "chaotic"


def test_empty_trajectory_is_coherent():
    assert convergence.classify_trajectory([]) == "coherent"


def test_contested_framings_are_the_cluster_centroids():
    by_stage = cmap(("retrieval stage", ["C1", "C2"]), ("generation stage", ["C3", "C4"]))
    by_index = cmap(("flat index", ["C1", "C3"]), ("graph index", ["C2", "C4"]))
    framings = convergence.contested_framings([by_stage, by_index, by_stage])
    assert len(framings) == 2
    assert all(f["label"].startswith("by ") and f["summary"] for f in framings)


# --- the loop ------------------------------------------------------------------

def _big_change(n):
    """A map far enough from the base to clear tau."""
    return cmap(*[(f"concept{i}", [f"C{n}-{i}"]) for i in range(4)])


def test_loop_with_no_finding_is_coherent():
    run = run_convergence_loop(cmap(("chunking", ["C1"])), ScriptedStructureJudge(script=[]))
    assert run.regime == "coherent"
    assert run.log.terminal_decision == "draft"
    assert run.log.cycles[-1].decision == "stop"


def test_small_finding_deepens_in_place_without_a_new_cycle():
    base = cmap(("chunking", ["C1"]))
    nudged = cmap(("chunking", ["C1", "C2"]))          # distance 1, below tau(0)=4
    judge = ScriptedStructureJudge(script=[({"finding": "add a claim"}, nudged)])
    run = run_convergence_loop(base, judge)
    assert [c.decision for c in run.log.cycles] == ["draft", "deepen", "stop"]
    assert len(run.cycle_maps) == 1                      # deepening does not open a cycle


def test_large_finding_escalates_and_opens_a_cycle():
    base = cmap(("chunking", ["C1"]))
    judge = ScriptedStructureJudge(script=[({"finding": "split the taxonomy"}, _big_change(1))])
    run = run_convergence_loop(base, judge)
    escalations = [c for c in run.log.cycles if c.decision == "escalate"]
    assert len(escalations) == 1 and escalations[0].cycle == 1
    assert escalations[0].c_k and escalations[0].c_k > 0
    assert len(run.cycle_maps) == 2


def test_loop_never_exceeds_k_max_escalations():
    """The termination guarantee: an endlessly-escalating judge still stops at K_MAX."""
    base = cmap(("chunking", ["C1"]))
    judge = ScriptedStructureJudge(
        script=[({"finding": f"restructure {i}"}, _big_change(i)) for i in range(20)])
    run = run_convergence_loop(base, judge)
    escalations = [c for c in run.log.cycles if c.decision == "escalate"]
    assert len(escalations) <= convergence.K_MAX
    assert conv_checks.terminal_state(run.log) == []


def test_deepen_path_is_bounded_by_max_dives():
    """Sub-tau findings never escalate, so without a dive cap the loop would spin forever."""
    base = cmap(("chunking", ["C1"]))
    script = [({"finding": f"nudge {i}"}, cmap(("chunking", ["C1"] + [f"C{i}"]))) for i in range(50)]
    run = run_convergence_loop(base, ScriptedStructureJudge(script=script))
    dives = [c for c in run.log.cycles if c.decision == "deepen"]
    assert len(dives) <= convergence.MAX_DIVES
    assert run.log.cycles[-1].decision == "stop"


def test_contested_regime_emits_a_block_and_marks_the_maps():
    by_stage = cmap(("retrieval stage", ["C1", "C2"]), ("generation stage", ["C3", "C4"]))
    by_index = cmap(("flat index", ["C1", "C3"]), ("graph index", ["C2", "C4"]))
    judge = ScriptedStructureJudge(script=[
        ({"finding": "reframe by index type"}, by_index),
        ({"finding": "reframe by stage"}, by_stage),
        ({"finding": "reframe by index type"}, by_index),
    ])
    run = run_convergence_loop(by_stage, judge)
    assert run.regime == "contested"
    assert run.log.terminal_decision == "render-contested"
    assert run.contested_block is not None
    assert run.contested_block.role.value == "contested"
    assert all(m.contested for m in run.cycle_maps)


def test_build_contested_block_shape():
    by_stage = cmap(("retrieval stage", ["C1", "C2"]))
    by_index = cmap(("flat index", ["C1"]), ("graph index", ["C2"]))
    block = build_contested_block([by_stage, by_index])
    assert block.role.value == "contested" and block.framings
    assert all(f.label and f.summary for f in block.framings)


def test_write_convergence_emits_per_cycle_maps_and_the_log(tmp_path):
    base = cmap(("chunking", ["C1"]))
    judge = ScriptedStructureJudge(script=[({"finding": "split"}, _big_change(1))])
    run = run_convergence_loop(base, judge)
    paths = write_convergence(run, tmp_path)
    assert paths["log"].is_file() and paths["map_v0"].is_file() and paths["map_v1"].is_file()
    assert ConvergenceLog.from_yaml(paths["log"]).terminal_regime == run.regime


# --- the R-CONV-01 lint ---------------------------------------------------------

def _log(**kw):
    base = dict(k_max=3, terminal_regime="converged", terminal_decision="footnote-residual",
                cycles=[{"cycle": 0, "tau": 4.0, "finding": "initial", "decision": "draft"},
                        {"cycle": 0, "tau": 4.0, "finding": "terminal", "decision": "stop"}])
    base.update(kw)
    return ConvergenceLog(**base)


def test_lint_passes_on_a_valid_log():
    assert conv_checks.terminal_state(_log()) == []


def test_lint_flags_escalation_past_k_max():
    cycles = [{"cycle": i, "tau": 4.0, "finding": "f", "decision": "escalate"} for i in range(1, 6)]
    cycles.append({"cycle": 5, "tau": 4.0, "finding": "t", "decision": "stop"})
    out = conv_checks.terminal_state(_log(cycles=cycles))
    assert any("cap is 3" in p for p in out)


def test_lint_flags_invalid_regime():
    assert any("not one of" in p for p in conv_checks.terminal_state(_log(terminal_regime=None)))


def test_lint_flags_regime_decision_mismatch():
    out = conv_checks.terminal_state(_log(terminal_regime="contested", terminal_decision="footnote-residual"))
    assert any("implies decision" in p for p in out)


def test_lint_flags_unterminated_log():
    cycles = [{"cycle": 0, "tau": 4.0, "finding": "f", "decision": "deepen"}]
    assert any("expected 'stop'" in p for p in conv_checks.terminal_state(_log(cycles=cycles)))


def test_lint_requires_a_rendered_block_for_a_contested_regime():
    """Recording 'contested' while rendering nothing would drop the disagreement silently."""
    log = _log(terminal_regime="contested", terminal_decision="render-contested")
    empty_ir = DocumentIR(sections=[Section(block_id="s1", title="t")])
    assert any("no role=contested block" in p for p in conv_checks.terminal_state(log, empty_ir))

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


def test_a_coherent_terminal_from_a_judge_that_never_answered_is_flagged():
    """`scan_for_structural` returns None on an outage — deliberately, since inventing a finding
    would trigger a re-grounding cycle on the strength of a timeout — and None is exactly what ends
    the loop as `coherent`. So "the judge looked and found nothing" and "the judge never answered"
    wrote the identical log, and R-CONV-01 credited the second as the first."""
    clean = _log(terminal_regime="coherent", terminal_decision="draft")
    assert conv_checks.terminal_state(clean) == []

    outage = _log(terminal_regime="coherent", terminal_decision="draft",
                  judge_errors=["CliUnavailable: claude CLI exceeded 420s"])
    problems = conv_checks.terminal_state(outage)
    assert any("did not answer" in p for p in problems)


def test_the_contested_clause_is_reachable_from_the_dispatched_path():
    """The test above calls the check DIRECTLY and hands it an IR. The dispatcher did not: it
    invoked `terminal_state(log)` and the `ir` parameter defaulted to None, so this clause of
    R-CONV-01 was unreachable from every caller that actually runs. A check tested in isolation and
    dead in practice is what testing around the dispatcher buys."""
    from ir.schema import Block, Framing
    from lint import run_convergence_pass

    log = _log(terminal_regime="contested", terminal_decision="render-contested")
    empty_ir = DocumentIR(sections=[Section(block_id="s1", title="t")])
    report = run_convergence_pass(log, empty_ir)
    assert report["blocking"] is True
    assert any("no role=contested block" in f["detail"] for f in report["findings"])

    rendered = DocumentIR(sections=[Section(block_id="s1", title="t", blocks=[
        Block(block_id="con", role="contested",
              framings=[Framing(label="school A", summary="masks are required"),
                        Framing(label="school B", summary="anchors suffice")])])])
    assert run_convergence_pass(log, rendered)["blocking"] is False

    # ...and with no IR at all the clause simply does not apply; it must not fabricate a violation
    assert run_convergence_pass(log)["blocking"] is False


# --- the real structure judge (the third model seam) -------------------------
# ScriptedStructureJudge was the only implementation in the tree, and it replays findings it was
# told in advance — so R-CONV-01 could only ever be exercised against a judge that knew the answer.
# These pin the division of labour R-CONV-02 states verbatim: the model decides WHAT changes, this
# code applies it. Letting a model emit a whole ConceptMap would hand it the deterministic half too,
# and silently make Delta_struct a function of how verbose the model felt.

def _judge(payload):
    from research.claude_structure_judge import ClaudeStructureJudge

    judge = ClaudeStructureJudge.__new__(ClaudeStructureJudge)
    judge.params, judge.scans = {}, []
    judge.cli = type("_Cli", (), {"result_json": staticmethod(lambda _i: payload),
                                  "calls": 0, "spend_usd": 0.0})()
    return judge


def _map():
    from ir.schema import Concept, ConceptMap

    return ConceptMap(concepts=[
        Concept(concept_id="c1", canonical_term="leader tracing", aliases=["callout association"],
                claim_ids=["C1"], source_ids=["s1"]),
        Concept(concept_id="c2", canonical_term="anchor seeding", claim_ids=["C2"], source_ids=["s2"]),
    ])


def test_a_merge_is_applied_deterministically_not_by_the_model():
    """The model names `merge c1 c2`; the fold itself — union the evidence, keep the survivor's
    identity, preserve ordering — is arithmetic, so Delta_struct depends on the map alone."""
    judge = _judge({"structural": True, "kind": "merge", "concept_ids": ["c1", "c2"],
                    "finding": "these are one concept"})
    cmap = _map()
    finding = judge.scan_for_structural(cmap, {})
    assert finding and finding["kind"] == "merge"

    merged = judge.implied_edits(finding, cmap)
    assert [c.concept_id for c in merged.concepts] == ["c1"]
    survivor = merged.concepts[0]
    assert survivor.claim_ids == ["C1", "C2"]          # evidence unioned, never dropped
    assert survivor.source_ids == ["s1", "s2"]
    assert "anchor seeding" in survivor.aliases        # the folded term survives as an alias


def test_an_unknown_concept_id_cannot_drive_an_edit():
    """A hallucinated id must not restructure the map — it would silently delete real concepts."""
    judge = _judge({"structural": True, "kind": "merge", "concept_ids": ["c1", "does-not-exist"],
                    "finding": "x"})
    assert judge.scan_for_structural(_map(), {}) is None


def test_a_depth_finding_is_not_a_structural_one():
    judge = _judge({"structural": False, "kind": "none", "concept_ids": [], "finding": ""})
    assert judge.scan_for_structural(_map(), {}) is None


def test_an_unreachable_judge_settles_rather_than_inventing_a_finding():
    """An outage must not trigger a re-grounding cycle. 'No structural finding observed' is the
    honest reading of silence; a fabricated finding costs a whole campaign."""
    from research.claude_structure_judge import ClaudeStructureJudge
    from utils.claude_cli import CliUnavailable

    judge = ClaudeStructureJudge.__new__(ClaudeStructureJudge)
    judge.params, judge.scans = {}, []

    def _boom(_instruction):
        raise CliUnavailable("simulated outage")

    judge.cli = type("_Cli", (), {"result_json": staticmethod(_boom)})()
    assert judge.scan_for_structural(_map(), {}) is None
    assert "error" in judge.scans[0]

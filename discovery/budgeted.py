"""Deterministic, query-budgeted search over explicit intervention candidates.

The evaluator executes the intervention and supplies the measured objective.
This module never infers causal support from graph topology or a search score.
Caching assumes a deterministic evaluator (including any fixed seed ensemble).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from math import comb, isfinite
from numbers import Real
import random
from typing import Callable, Mapping, Sequence


@dataclass(frozen=True)
class Candidate:
    """One intervenable node; outcome nodes are deliberately not search actions."""

    id: str
    region: str

    def __post_init__(self) -> None:
        if not self.id or self.region not in {"sender", "message", "receiver"}:
            raise ValueError("Candidate requires an id and sender/message/receiver region")


@dataclass(frozen=True)
class Evaluation:
    """Executed objective, benign damage, actual forward cost and raw evidence."""

    faithfulness: float
    benign_damage: float
    forward_passes: int
    raw_outputs: Mapping[str, object]

    def __post_init__(self) -> None:
        for value in (self.faithfulness, self.benign_damage):
            if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
                raise ValueError("Evaluation metrics must be finite real numbers")
        if self.benign_damage < 0:
            raise ValueError("Benign damage cannot be negative")
        if type(self.forward_passes) is not int or self.forward_passes < 0:
            raise ValueError("Forward passes must be a nonnegative integer")
        if not isinstance(self.raw_outputs, Mapping) or not self.raw_outputs:
            raise ValueError("Raw executed outputs are required")


@dataclass(frozen=True)
class SearchConfig:
    """Predeclared constraints; query budget includes baseline and verification."""

    max_queries: int = 64
    faithfulness_threshold: float = 0.8
    max_benign_damage: float = 0.1
    beam_width: int = 2
    split: str = "development"

    def __post_init__(self) -> None:
        for value in (self.max_queries, self.beam_width):
            if type(value) is not int or value < 1:
                raise ValueError("Query budget and beam width must be positive integers")
        for value in (self.faithfulness_threshold, self.max_benign_damage):
            if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
                raise ValueError("Search thresholds must be finite real numbers")
        if self.max_benign_damage < 0:
            raise ValueError("Benign damage limit cannot be negative")
        if self.split not in {"development", "synthetic"}:
            raise ValueError("Search is restricted to development or synthetic data")


@dataclass(frozen=True)
class QueryRecord:
    """One unique executed mask, in its original query order."""

    retained: tuple[str, ...]
    evaluation: Evaluation


@dataclass(frozen=True)
class SearchResult:
    """Measured search result, with no global-minimality or BVP claim."""

    method: str
    retained: tuple[str, ...]
    evaluation: Evaluation
    feasible: bool
    stop_reason: str
    one_step_locally_minimal: bool | None
    queries: int
    forward_passes: int
    records: tuple[QueryRecord, ...]


class QueryBudgetExceeded(RuntimeError):
    """No new evaluator invocation is permitted under the declared budget."""


class _Session:
    def __init__(self, candidates: Sequence[Candidate], evaluate: Callable[[tuple[str, ...]], Evaluation],
                 config: SearchConfig) -> None:
        self.ids = tuple(sorted(candidate.id for candidate in candidates))
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("Candidate ids must be unique")
        self.evaluate = evaluate
        self.config = config
        self.cache: dict[tuple[str, ...], Evaluation] = {}

    def query(self, mask: tuple[str, ...]) -> Evaluation:
        if mask not in self.cache:
            if len(self.cache) >= self.config.max_queries:
                raise QueryBudgetExceeded("Query budget exhausted")
            value = self.evaluate(mask)
            if not isinstance(value, Evaluation):
                raise TypeError("Evaluator must return Evaluation")
            self.cache[mask] = value
        return self.cache[mask]

    def feasible(self, value: Evaluation) -> bool:
        return (value.faithfulness >= self.config.faithfulness_threshold
                and value.benign_damage <= self.config.max_benign_damage)

    def rank(self, mask: tuple[str, ...]) -> tuple:
        value = self.cache[mask]
        return (len(mask), -value.faithfulness, value.benign_damage, mask)

    def finish(self, method: str, stopped: str) -> SearchResult:
        valid = [mask for mask, value in self.cache.items() if self.feasible(value)]
        best = min(valid, key=self.rank) if valid else self.ids
        minimal: bool | None = None
        if valid:
            minimal = True
            # Verification consumes the same budget; cached removals are free.
            for node in best:
                removed = tuple(item for item in best if item != node)
                try:
                    if self.feasible(self.query(removed)):
                        minimal = False
                        break
                except QueryBudgetExceeded:
                    minimal = None
                    stopped = "query_budget_exhausted"
                    break
        else:
            stopped = "no_feasible_mask" if stopped == "search_complete" else stopped
        records = tuple(QueryRecord(mask, value) for mask, value in self.cache.items())
        return SearchResult(method, best, self.cache[best], bool(valid), stopped, minimal,
                            len(records), sum(row.evaluation.forward_passes for row in records), records)


def search(candidates: Sequence[Candidate], evaluate: Callable[[tuple[str, ...]], Evaluation],
           config: SearchConfig, *, method: str = "greedy") -> SearchResult:
    """Prune masks using greedy or beam search under identical query accounting.

    Every unique child of the current beam is evaluated before beam selection,
    unless the budget interrupts that layer. The best actually observed feasible
    mask is returned even when a layer could not be completed. Single removals
    are audited before claiming local minimality. No monotonicity is assumed.
    """
    if method not in {"greedy", "beam"}:
        raise ValueError("Method must be greedy or beam")
    session = _Session(candidates, evaluate, config)
    session.query(session.ids)
    frontier = [session.ids]
    width = 1 if method == "greedy" else config.beam_width
    stopped = "search_complete"
    while frontier:
        children = sorted({tuple(item for item in mask if item != node)
                           for mask in frontier for node in mask})
        if not children:
            break
        try:
            for child in children:
                session.query(child)
        except QueryBudgetExceeded:
            stopped = "query_budget_exhausted"
            break
        frontier = sorted((child for child in children if session.feasible(session.cache[child])),
                          key=session.rank)[:width]
    return session.finish(method, stopped)


def receiver_candidates(candidates: Sequence[Candidate]) -> tuple[Candidate, ...]:
    """Restrict allowed actions; the caller must keep its evaluator/context fixed."""
    return tuple(candidate for candidate in candidates if candidate.region == "receiver")


def matched_random_masks(candidates: Sequence[Candidate], reference: Sequence[str], *,
                         samples: int, seed: int) -> tuple[tuple[str, ...], ...]:
    """Sample unique masks with exactly the reference's per-region node counts.

    The reference is a possible draw, not silently excluded. Small finite spaces
    are enumerated; larger spaces use bounded rejection sampling. Returning fewer
    masks is explicit and prevents unbounded loops on exhausted mask spaces.
    """
    by_id = {candidate.id: candidate for candidate in candidates}
    if len(by_id) != len(candidates) or len(set(reference)) != len(reference):
        raise ValueError("Candidate and reference ids must be unique")
    if not set(reference) <= by_id.keys():
        raise ValueError("Reference contains unknown candidates")
    if type(samples) is not int or samples < 1 or type(seed) is not int:
        raise ValueError("Samples must be positive and seed must be an integer")
    groups = [tuple(sorted(c.id for c in candidates if c.region == region))
              for region in ("sender", "message", "receiver")]
    counts = [sum(node in reference for node in group) for group in groups]
    total = 1
    for group, count in zip(groups, counts):
        total *= comb(len(group), count)
    rng = random.Random(seed)
    wanted = min(samples, total)
    if total <= 10000:
        masks = [tuple(sorted(node for part in parts for node in part))
                 for parts in product(*(combinations(group, count) for group, count in zip(groups, counts)))]
        return tuple(rng.sample(masks, wanted))
    selected: dict[tuple[str, ...], None] = {}
    for _ in range(wanted * 100):
        mask = tuple(sorted(node for group, count in zip(groups, counts) for node in rng.sample(group, count)))
        selected[mask] = None
        if len(selected) == wanted:
            break
    return tuple(selected)


def random_control(candidates: Sequence[Candidate], evaluate: Callable[[tuple[str, ...]], Evaluation],
                   config: SearchConfig, reference: Sequence[str], *, samples: int, seed: int) -> SearchResult:
    """Evaluate region/size-matched random masks with the same query accounting.

    Search-style local minimality is not tested for a random control; the result
    reports the best measured sample at the requested size, including failures.
    """
    masks = matched_random_masks(candidates, reference, samples=samples, seed=seed)
    session = _Session(candidates, evaluate, config)
    stopped = "sample_space_or_request_complete"
    for mask in masks:
        try:
            session.query(mask)
        except QueryBudgetExceeded:
            stopped = "query_budget_exhausted"
            break
    valid = [mask for mask, value in session.cache.items() if session.feasible(value)]
    best = min(valid or list(session.cache), key=session.rank)
    records = tuple(QueryRecord(mask, value) for mask, value in session.cache.items())
    return SearchResult("matched_random", best, session.cache[best], bool(valid), stopped, None,
                        len(records), sum(row.evaluation.forward_passes for row in records), records)

# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/resident_knowledge.py
# Component: REPOSITORY-KNOWLEDGE-PROVIDER
# Revision: 1.0.1
# Purpose: Rank bounded task-relevant excerpts from pinned resident sources
# Execution Model: In-process bounded lexical selection over verified source files
# Observability: Full-source provenance with explicit VERIFIED/NO_MATCH/INCOMPLETE outcomes
# Dependencies: RepositoryKnowledgeProvider; knowledge-provider v1
# Authority: Read-only repository evidence; never authorizes an action
# Changed: 2026-10-11 UTC | RV-M4.4-RESIDENT-KNOWLEDGE-SELECT | Initial bounded resident knowledge selector
# Changed: 2026-10-15 UTC | RV-GRACE-GROUNDING-BOUNDED-001 | Rank complete passages within the evidence envelope while verifying the full source set
# Contracts: docs/components/RESIDENT_REASONING.md; knowledge-provider v1
# Tests: tests/test_resident_knowledge.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Select ranked complete passages from a fully verified source corpus.

The base provider verifies every allowlisted source at one commit. This adapter
scans that complete source set and selects informative complete paragraphs
within the evidence envelope. It does not claim to return every lexical match:
the full source references, revision and digest prove which corpus was scanned,
and coverage metadata makes the bounded selection explicit. Text is never
clipped; no viable selection remains INCOMPLETE.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Mapping

from .repository_knowledge import RepositoryKnowledgeProvider
from .knowledge_provider_v1.contract import KnowledgeResult, KnowledgeStatus


class TaskRelevantRepositoryKnowledgeProvider:
    """Knowledge-provider v1 adapter for the fixed resident source corpus."""

    CONTRACT_REF = RepositoryKnowledgeProvider.RESIDENT_CONTRACT
    MAX_CONTEXT_BYTES = 8 * 1024
    # Leave room for KnowledgeResult provenance and the pipeline evidence envelope.
    MAX_SELECTION_BYTES = 7 * 1024
    MAX_QUERY_BYTES = 4096
    _STOP_WORDS = frozenset({
        "about", "after", "again", "also", "and", "are", "because", "before",
        "between", "build", "change", "does", "from", "have", "into", "make",
        "must", "only", "should", "that", "their", "them", "then", "there",
        "these", "this", "through", "with", "within", "work", "would",
        "the", "for", "was", "were", "will", "can", "may", "our", "you",
        "objective", "ref", "engineering", "repository",
    })

    def __init__(self, repository, approved_commit: str, *, max_context_bytes: int = MAX_CONTEXT_BYTES):
        if type(max_context_bytes) is not int or not 512 <= max_context_bytes <= self.MAX_CONTEXT_BYTES:
            raise ValueError("max_context_bytes must be between 512 and the fixed 8 KiB cap")
        self.repository = RepositoryKnowledgeProvider(repository, approved_commit)
        self.approved_commit = approved_commit
        self.max_context_bytes = max_context_bytes

    @staticmethod
    def _result(status, *, refs=(), revision=None, digest=None, complete=None, value=None):
        return KnowledgeResult(status, value=value, source_references=tuple(refs),
                               source_revision=revision, source_sha256=digest,
                               retrieval_complete=complete)

    @classmethod
    def _query_terms(cls, assignment: Mapping) -> tuple[str, ...]:
        fields = [assignment.get("objective"), assignment.get("objective_ref"),
                  assignment.get("acceptance_criteria")]
        raw = " ".join(item if isinstance(item, str) else " ".join(item)
                       if isinstance(item, (list, tuple)) and all(isinstance(x, str) for x in item)
                       else "" for item in fields)
        if not raw or len(raw.encode("utf-8")) > cls.MAX_QUERY_BYTES:
            return ()
        return tuple(sorted({token for token in re.findall(r"[a-z0-9_]+", raw.lower())
                             if len(token) >= 3 and token not in cls._STOP_WORDS}))

    @staticmethod
    def _paragraphs(content: str):
        lines = content.splitlines()
        start = 1
        block = []
        for number, line in enumerate(lines, start=1):
            if line.strip():
                if not block:
                    start = number
                block.append(line)
            elif block:
                yield start, number - 1, "\n".join(block)
                block = []
        if block:
            yield start, len(lines), "\n".join(block)

    def _select(self, assignment: Mapping) -> KnowledgeResult:
        if not isinstance(assignment, Mapping):
            return self._result(KnowledgeStatus.UNVERIFIED, complete=False)
        contract_ref = assignment.get("grounding_contract_ref", assignment.get("contract_ref"))
        if contract_ref != self.CONTRACT_REF:
            return self.repository.ground_assignment(assignment)
        terms = self._query_terms(assignment)
        if not terms:
            return self._result(KnowledgeStatus.UNVERIFIED, complete=False)
        source = self.repository.ground_assignment({"contract_ref": self.CONTRACT_REF})
        if source.status is not KnowledgeStatus.VERIFIED or source.retrieval_complete is not True:
            return source

        term_set = set(terms)
        candidates = []
        for document in source.value["documents"]:
            document_digest = hashlib.sha256(
                document["content"].encode("utf-8")).hexdigest()
            for first, last, text in self._paragraphs(document["content"]):
                words = re.findall(r"[a-z0-9_]+", text.lower())
                found = term_set.intersection(words)
                if found:
                    candidates.append({
                        "reference": document["reference"],
                        "source_sha256": document_digest,
                        "line_start": first,
                        "line_end": last,
                        "text": text,
                        "matches": found,
                        "word_count": max(1, len(words)),
                    })
        if not candidates:
            return self._result(KnowledgeStatus.NO_MATCH, refs=source.source_references,
                                revision=source.source_revision, digest=source.source_sha256,
                                complete=True)

        document_frequency = {
            term: sum(term in item["matches"] for item in candidates)
            for term in terms
        }
        paragraph_count = len(candidates)
        idf = {
            term: math.log(1 + (paragraph_count - frequency + 0.5) /
                           (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }
        selected = []
        covered = set()
        remaining = list(candidates)
        selection_budget = min(self.max_context_bytes, self.MAX_SELECTION_BYTES)

        def make_value(passages):
            documents = []
            selected_terms = set().union(*(item["matches"] for item in passages))
            for document in source.value["documents"]:
                matches = [item for item in passages
                           if item["reference"] == document["reference"]]
                if matches:
                    documents.append({
                        "reference": document["reference"],
                        "source_sha256": matches[0]["source_sha256"],
                        "passages": [{
                            "line_start": item["line_start"],
                            "line_end": item["line_end"],
                            "text": item["text"],
                        } for item in matches],
                    })
            return {
                "contract_ref": self.CONTRACT_REF,
                "selection_complete": True,
                "selection_policy": "ranked-complete-paragraphs-v1",
                "query_sha256": hashlib.sha256(" ".join(terms).encode()).hexdigest(),
                "query_term_coverage": {
                    "matched": len(set().union(*(item["matches"] for item in candidates))),
                    "selected": len(selected_terms),
                },
                "documents": documents,
            }

        # Greedily cover high-information query terms per byte. Stable source
        # and line tie breakers keep identical retries deterministic.
        while remaining:
            current_size = len(json.dumps(
                make_value(selected), ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8"))
            ranked = []
            for item in remaining:
                new_terms = item["matches"] - covered
                if not new_terms:
                    continue
                trial = make_value(selected + [item])
                trial_size = len(json.dumps(
                    trial, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")).encode("utf-8"))
                if trial_size > selection_budget:
                    continue
                gain = sum(idf[term] for term in new_terms)
                added_bytes = max(1, trial_size - current_size)
                ranked.append((gain / added_bytes, gain, -item["word_count"],
                               item["reference"], -item["line_start"], item))
            if not ranked:
                break
            item = max(ranked, key=lambda result: result[:-1])[-1]
            selected.append(item)
            covered.update(item["matches"])
            remaining.remove(item)

        if not selected:
            return self._result(KnowledgeStatus.INCOMPLETE,
                                refs=source.source_references,
                                revision=source.source_revision,
                                digest=source.source_sha256, complete=False)
        value = make_value(selected)
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")
        if len(encoded) > selection_budget:
            return self._result(KnowledgeStatus.INCOMPLETE,
                                refs=source.source_references,
                                revision=source.source_revision,
                                digest=source.source_sha256, complete=False)
        return self._result(KnowledgeStatus.VERIFIED,
                            refs=source.source_references,
                            revision=source.source_revision,
                            digest=source.source_sha256, complete=True, value=value)

    def ground_assignment(self, assignment: Mapping) -> KnowledgeResult:
        return self._select(assignment)

    def reground_assignment(self, assignment: Mapping, trigger: str) -> KnowledgeResult:
        if not isinstance(trigger, str) or not trigger or len(trigger) > 64:
            return self._result(KnowledgeStatus.UNVERIFIED, complete=False)
        result = self._select(assignment)
        if result.status is not KnowledgeStatus.VERIFIED:
            return result
        value = dict(result.value)
        value["trigger"] = trigger
        return self._result(result.status, refs=result.source_references,
                            revision=result.source_revision, digest=result.source_sha256,
                            complete=result.retrieval_complete, value=value)

    def preflight_action(self, assignment: Mapping, action: str) -> KnowledgeResult:
        if action == "resident.reasoning.v1":
            if (not isinstance(assignment, Mapping) or
                    assignment.get("grounding_contract_ref", assignment.get("contract_ref")) != self.CONTRACT_REF):
                return self._result(KnowledgeStatus.CONTRADICTORY, complete=True)
            return self._select(assignment)
        return self.repository.preflight_action(assignment, action)

    def record_learning(self, assignment: Mapping, outcome: Mapping) -> KnowledgeResult:
        return self.repository.record_learning(assignment, outcome)

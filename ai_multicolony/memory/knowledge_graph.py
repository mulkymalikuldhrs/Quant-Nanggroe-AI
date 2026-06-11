"""TemporalKnowledgeGraph – Zep-style temporal knowledge graph with
subject-predicate-object triples, time validity tracking, point-in-time
queries, evolution queries, and confidence scoring.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────────

class Triple(BaseModel):
    """A subject-predicate-object triple with temporal validity."""
    model_config = ConfigDict(frozen=False)

    triple_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    subject: str = ""
    predicate: str = ""
    object: str = ""
    valid_from: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    valid_to: Optional[str] = None  # None = still valid
    confidence: float = 1.0
    source: Dict[str, Any] = Field(default_factory=dict)
    supersedes: Optional[str] = None  # triple_id of older version
    superseded_by: Optional[str] = None  # triple_id of newer version
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    access_count: int = 0


class Entity(BaseModel):
    """An entity (node) in the knowledge graph."""
    model_config = ConfigDict(frozen=False)

    entity_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    entity_type: str = "generic"
    attributes: Dict[str, Any] = Field(default_factory=dict)
    triple_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EvolutionEntry(BaseModel):
    """An entry in an evolution timeline."""
    model_config = ConfigDict(frozen=False)

    timestamp: str
    action: str  # "added" | "superseded" | "expired"
    triple: Optional[Dict[str, Any]] = None
    details: Dict[str, Any] = Field(default_factory=dict)


# ── Temporal Knowledge Graph ────────────────────────────────────

class TemporalKnowledgeGraph:
    """Zep-style temporal knowledge graph.

    Stores knowledge as subject-predicate-object triples with time
    validity windows.  Supports:

    * Point-in-time queries: "What did we know about X at time T?"
    * Evolution queries: "How has knowledge about X changed?"
    * Confidence scoring: filter by confidence threshold
    * Supersession: newer facts automatically supersede older ones
    * Entity extraction: auto-discover entities from triples
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name

        # Triple storage
        self._triples: Dict[str, Triple] = {}

        # Indexes for fast lookup
        self._subject_index: Dict[str, Set[str]] = {}  # subject -> {triple_ids}
        self._predicate_index: Dict[str, Set[str]] = {}  # predicate -> {triple_ids}
        self._object_index: Dict[str, Set[str]] = {}  # object -> {triple_ids}

        # Entity storage
        self._entities: Dict[str, Entity] = {}

    # ── Add triple ───────────────────────────────────────────────

    async def add_triple(
        self,
        subject: str,
        predicate: str,
        object: str,
        valid_from: Optional[str] = None,
        valid_to: Optional[str] = None,
        confidence: float = 1.0,
        source: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        supersede: bool = True,
    ) -> Triple:
        """Add a triple to the knowledge graph.

        If ``supersede`` is True, any existing active triple with the
        same subject+predicate will be superseded by this new triple.
        """
        triple = Triple(
            subject=subject,
            predicate=predicate,
            object=object,
            valid_from=valid_from or datetime.now(timezone.utc).isoformat(),
            valid_to=valid_to,
            confidence=confidence,
            source=source or {},
            metadata=metadata or {},
        )

        # Handle supersession
        if supersede:
            existing = self._find_active_triple(subject, predicate)
            if existing:
                existing.superseded_by = triple.triple_id
                existing.valid_to = triple.valid_from
                triple.supersedes = existing.triple_id

        # Store triple
        self._triples[triple.triple_id] = triple

        # Update indexes
        self._subject_index.setdefault(subject, set()).add(triple.triple_id)
        self._predicate_index.setdefault(predicate, set()).add(triple.triple_id)
        self._object_index.setdefault(object, set()).add(triple.triple_id)

        # Update entities
        self._ensure_entity(subject)
        self._ensure_entity(object)

        logger.debug("Added triple: %s %s %s (id=%s)", subject, predicate, object, triple.triple_id)
        return triple

    # ── Point-in-time queries ────────────────────────────────────

    async def query_at_time(
        self,
        point_in_time: str,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[Triple]:
        """Query the knowledge graph as it was at a specific point in time.

        Returns triples that were valid (not superseded, within valid_from/valid_to)
        at the given timestamp.
        """
        candidates = self._get_candidates(subject, predicate, object)

        results = []
        for tid in candidates:
            triple = self._triples.get(tid)
            if not triple:
                continue

            # Check temporal validity
            if not self._is_valid_at(triple, point_in_time):
                continue

            # Check confidence
            if triple.confidence < min_confidence:
                continue

            # Check supersession at the given time
            if triple.superseded_by:
                newer = self._triples.get(triple.superseded_by)
                if newer and newer.valid_from <= point_in_time:
                    continue  # This triple was already superseded at the given time

            triple.access_count += 1
            results.append(triple)

        return results

    # ── Current state queries ────────────────────────────────────

    async def query(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,
        min_confidence: float = 0.0,
        include_expired: bool = False,
        limit: int = 100,
    ) -> List[Triple]:
        """Query the current state of the knowledge graph.

        By default, only returns active (non-superseded) triples.
        """
        candidates = self._get_candidates(subject, predicate, object)

        results = []
        now = datetime.now(timezone.utc).isoformat()

        for tid in candidates:
            triple = self._triples.get(tid)
            if not triple:
                continue

            # Skip superseded unless include_expired
            if not include_expired and triple.superseded_by:
                continue

            # Skip expired
            if not include_expired and triple.valid_to and triple.valid_to < now:
                continue

            # Check confidence
            if triple.confidence < min_confidence:
                continue

            triple.access_count += 1
            results.append(triple)

        return results[:limit]

    # ── Evolution queries ────────────────────────────────────────

    async def evolution(
        self,
        subject: str,
        predicate: Optional[str] = None,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
    ) -> List[EvolutionEntry]:
        """Get the evolution timeline for a subject (and optionally predicate).

        Shows how knowledge about an entity has changed over time.
        """
        triple_ids = self._subject_index.get(subject, set())
        entries: List[EvolutionEntry] = []

        for tid in triple_ids:
            triple = self._triples.get(tid)
            if not triple:
                continue
            if predicate and triple.predicate != predicate:
                continue

            # Filter time range
            if from_time and triple.valid_from < from_time:
                continue
            if to_time and triple.valid_from > to_time:
                continue

            # Entry for when this triple was added
            entries.append(EvolutionEntry(
                timestamp=triple.valid_from,
                action="added",
                triple=triple.model_dump(),
                details={"object": triple.object, "confidence": triple.confidence},
            ))

            # Entry for supersession
            if triple.superseded_by:
                newer = self._triples.get(triple.superseded_by)
                if newer:
                    entries.append(EvolutionEntry(
                        timestamp=newer.valid_from,
                        action="superseded",
                        triple=triple.model_dump(),
                        details={
                            "new_object": newer.object,
                            "new_confidence": newer.confidence,
                        },
                    ))

            # Entry for expiry
            if triple.valid_to:
                entries.append(EvolutionEntry(
                    timestamp=triple.valid_to,
                    action="expired",
                    triple=triple.model_dump(),
                ))

        # Sort by timestamp
        entries.sort(key=lambda e: e.timestamp)
        return entries

    # ── Entity management ────────────────────────────────────────

    async def get_entity(self, name: str) -> Optional[Entity]:
        """Get an entity by name."""
        return self._entities.get(name)

    async def get_entity_triples(self, name: str, active_only: bool = True) -> List[Triple]:
        """Get all triples involving an entity (as subject or object)."""
        results = []
        now = datetime.now(timezone.utc).isoformat()

        # As subject
        for tid in self._subject_index.get(name, set()):
            triple = self._triples.get(tid)
            if triple:
                if active_only and triple.superseded_by:
                    continue
                if active_only and triple.valid_to and triple.valid_to < now:
                    continue
                results.append(triple)

        # As object
        for tid in self._object_index.get(name, set()):
            triple = self._triples.get(tid)
            if triple:
                if active_only and triple.superseded_by:
                    continue
                if active_only and triple.valid_to and triple.valid_to < now:
                    continue
                results.append(triple)

        return results

    async def get_neighbors(
        self,
        entity_name: str,
        max_depth: int = 1,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get neighboring entities through graph traversal."""
        visited: Set[str] = {entity_name}
        result_triples: List[Triple] = []
        current_level = {entity_name}

        for depth in range(max_depth):
            next_level: Set[str] = set()
            for entity in current_level:
                # Find triples where this entity is subject or object
                triples = await self.get_entity_triples(entity, active_only)
                for triple in triples:
                    result_triples.append(triple)
                    # Add the other end
                    if triple.subject == entity and triple.object not in visited:
                        next_level.add(triple.object)
                    elif triple.object == entity and triple.subject not in visited:
                        next_level.add(triple.subject)

            visited.update(next_level)
            current_level = next_level

        return [
            {
                "subject": t.subject,
                "predicate": t.predicate,
                "object": t.object,
                "confidence": t.confidence,
                "valid_from": t.valid_from,
            }
            for t in result_triples
        ]

    # ── Delete ───────────────────────────────────────────────────

    async def delete_triple(self, triple_id: str) -> bool:
        """Delete a triple from the graph."""
        triple = self._triples.pop(triple_id, None)
        if not triple:
            return False

        # Clean up indexes
        if triple.subject in self._subject_index:
            self._subject_index[triple.subject].discard(triple_id)
        if triple.predicate in self._predicate_index:
            self._predicate_index[triple.predicate].discard(triple_id)
        if triple.object in self._object_index:
            self._object_index[triple.object].discard(triple_id)

        # Fix supersession links
        if triple.supersedes:
            old = self._triples.get(triple.supersedes)
            if old:
                old.superseded_by = None
        if triple.superseded_by:
            newer = self._triples.get(triple.superseded_by)
            if newer:
                newer.supersedes = triple.supersedes

        return True

    # ── Statistics ───────────────────────────────────────────────

    def triple_count(self, active_only: bool = True) -> int:
        if active_only:
            return sum(1 for t in self._triples.values() if not t.superseded_by)
        return len(self._triples)

    def entity_count(self) -> int:
        return len(self._entities)

    def predicate_count(self) -> int:
        return len(self._predicate_index)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total_triples": len(self._triples),
            "active_triples": self.triple_count(active_only=True),
            "superseded_triples": sum(1 for t in self._triples.values() if t.superseded_by),
            "entities": len(self._entities),
            "predicates": len(self._predicate_index),
            "avg_confidence": (
                sum(t.confidence for t in self._triples.values()) / max(1, len(self._triples))
            ),
        }

    # ── Internal helpers ─────────────────────────────────────────

    def _find_active_triple(self, subject: str, predicate: str) -> Optional[Triple]:
        """Find an active (non-superseded) triple with the given subject and predicate."""
        subject_triples = self._subject_index.get(subject, set())
        predicate_triples = self._predicate_index.get(predicate, set())
        candidates = subject_triples & predicate_triples

        for tid in candidates:
            triple = self._triples.get(tid)
            if triple and not triple.superseded_by:
                return triple
        return None

    def _get_candidates(
        self,
        subject: Optional[str],
        predicate: Optional[str],
        object: Optional[str],
    ) -> Set[str]:
        """Get candidate triple IDs based on provided filters."""
        if subject:
            s_set = self._subject_index.get(subject, set())
        else:
            s_set = set(self._triples.keys())

        if predicate:
            p_set = self._predicate_index.get(predicate, set())
        else:
            p_set = set(self._triples.keys())

        if object:
            o_set = self._object_index.get(object, set())
        else:
            o_set = set(self._triples.keys())

        return s_set & p_set & o_set

    @staticmethod
    def _is_valid_at(triple: Triple, point_in_time: str) -> bool:
        """Check if a triple was valid at a given point in time."""
        if triple.valid_from > point_in_time:
            return False
        if triple.valid_to and triple.valid_to < point_in_time:
            return False
        return True

    def _ensure_entity(self, name: str) -> None:
        """Create an entity entry if it doesn't exist."""
        if name not in self._entities:
            self._entities[name] = Entity(name=name)
        # Update triple count
        entity = self._entities[name]
        count = len(self._subject_index.get(name, set())) + len(self._object_index.get(name, set()))
        entity.triple_count = count

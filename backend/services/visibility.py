"""
D20 — Visibility predicate: defined once, used everywhere.

A single helper that returns the set of matches visible to a guest in the
public portal.  Used by: portal photo list, download auth, ZIP builder,
photo counts.

    visible_matches(db, guest_id) → Query[Match]

WHERE m.guest_id = :guest_id
  AND m.status IN ('active', 'manually_added')
"""
from uuid import UUID

from sqlalchemy.orm import Session, Query

from models.match import Match


VISIBLE_STATUSES = ("active", "manually_added")


def visible_matches(db: Session, guest_id: UUID) -> Query:
    """Return a query of Match rows that are visible to the guest portal."""
    return (
        db.query(Match)
        .filter(
            Match.guest_id == guest_id,
            Match.status.in_(VISIBLE_STATUSES),
        )
    )


def visible_match_count(db: Session, guest_id: UUID) -> int:
    """Cheap COUNT of portal-visible photos for a guest."""
    return visible_matches(db, guest_id).count()


def visible_photo_ids(db: Session, guest_id: UUID, best_only: bool = False) -> list[UUID]:
    """Return the ordered list of photo IDs visible to a guest."""
    query = visible_matches(db, guest_id)
    if best_only:
        query = query.filter((Match.cluster_rank == 1) | (Match.cluster_rank.is_(None)))
        
    rows = (
        query
        .with_entities(Match.photo_id)
        .order_by(Match.similarity.desc())
        .all()
    )
    return [r[0] for r in rows]

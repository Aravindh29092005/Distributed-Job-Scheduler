# Design Decisions
- SQLite fallback for development/testing when PostgreSQL is down.
- Atomic claims using SELECT FOR UPDATE SKIP LOCKED.
- Coerced UUID inputs to prevent SQLite hex errors.

# Backend Audit

## Executive Summary

The backend of the Motors project follows a clean layered architecture with clear separation between routes (HTTP layer), repositories (SQL layer), services (business logic), and utility modules (photo manager, auth, backup). The codebase is generally well‑structured, with minimal framework coupling and a strong emphasis on keeping SQL out of routes. However, a few issues affect reliability and maintainability, primarily around caching of file system state and error handling during engine deletion.

## Overall Assessment

- Architecture: 8/10
- Readability: 8/10
- Coupling: 7/10
- Duplication: 6/10
- Error handling: 6/10
- Testability: 7/10
- Technical debt: 6/10

## Architecture Overview

```
HTTP / routes
      � ↓
business logic / services (export, backup, auth)
      � ↓
repositories / data access (engine_repo, mode_repo, work_repo)
      � ↓
database (SQLite)
```

Additional layers:
- **Filesystem**: `modules/photo_manager/manager` – sole source of truth for photo naming and disk operations.
- **Authentication**: `modules/auth` – split into hashing, DB users, file users, tokens, decorators.
- **Backup**: `modules/backup_system/backup` – atomic backup/restore with rollback, locking, checksums.
- **Configuration**: `config/settings.py` – single source for paths and constants.

## Dependency Problems

No serious dependency violations were found. Routes depend only on repositories and services; repositories depend solely on the database connection; services depend on repositories and utility modules. The direction of dependencies is correct (high‑level → low‑level). No circular imports were observed.

## Responsibility Problems

### [P1] Engine deletion may leave orphaned photos

**File:** `routes/engines.py`

**Location:** `delete_engine()` (lines 129‑151)

**Problem:**
After deleting the engine record from the database, the function calls `photo_manager.delete_engine_photos_from_disk()` to remove associated photo files. If photo deletion fails (e.g., due to file permissions or antivirus locking), the function logs a warning but still returns a success response. The engine ID is then considered free for reuse. Because the orphaned photos remain on disk with the naming pattern `ID{engine_id}_*.ext`, a later engine that receives the same ID will incorrectly inherit those old photos (the manager’s `engine_photo_disk_paths` will include them). This leads to mismatched photo counts and wrong images being displayed.

**Why it matters:**
Orphaned photos cause data inconsistency: the database shows no photos for an engine, but the UI displays stale images. Over time, deleted engines’ photos accumulate, wasting disk space and potentially confusing users.

**Recommended change:**
Make photo deletion a critical step of engine deletion. If photo deletion fails, abort the operation, roll back the database deletion (or prevent it), and return an error to the caller. A simple approach is to attempt photo deletion first, then delete the engine record, and if photo deletion fails, return an error without touching the DB.

**Risk:** Medium (requires changing the order of operations and adding rollback logic, but the flow is localized).

**Affected modules:** `routes/engines.py`, `modules/photo_manager/manager.py`

**Tests:**
Existing unit tests for engine deletion (if any) should verify that photo deletion occurs and that failure propagates as an error. Integration tests should simulate a failed photo removal (e.g., by making the file read‑only) and confirm that the engine is not deleted.

---

### [P2] Photo manager cache can become stale after backup restore or external file changes

**File:** `modules/photo_manager/manager.py`

**Location:** Global `_photo_paths_cache` and functions `engine_photo_disk_paths`, `next_photo_index`, `delete_engine_photos_from_disk`, `upload_engine_photos`, `replace_engine_photo`

**Problem:**
The photo manager caches the list of disk paths per engine ID in a module‑level dictionary (`_photo_paths_cache`). The cache is invalidated only when photos are added or removed via the manager’s own functions (`upload_engine_photos`, `delete_engine_photos_from_disk`, `replace_engine_photo`). It is **not** invalidated when the photos folder is replaced wholesale, as happens during a backup restore (`modules/backup_system/backup.py` performs an atomic `os.replace` of the entire `PHOTOS_FOLDER`). After such a restore, cached entries still point to the old file list (now deleted), causing the manager to return stale paths. Similarly, any external process that modifies the photos folder (e.g., manual copy) will not be reflected until the cache entry for that engine is evicted (which never happens).

**Why it matters:**
Stale cache leads to incorrect photo listings (missing new photos or showing deleted ones), wrong `photo_count` values, and potential errors when trying to serve non‑existent files. In a multi‑worker deployment (e.g., Gunicorn), each worker holds its own cache, increasing the chance of inconsistency.

**Recommended change:**
Either remove the caching layer (the `glob` operation is cheap for typical photo counts) or provide a centralised way to invalidate the cache when the photos folder is known to have changed. A simple solution is to clear the entire `_photo_paths_cache` after any operation that replaces the photos folder (e.g., add a function `invalidate_photo_cache()` called from the backup restore code). Alternatively, replace the cache with a per‑engine timestamp check against the folder’s modification time.

**Risk:** Low to Medium (clear‑cache approach is trivial; timestamp‑based invalidation requires slightly more code but is still localized).

**Affected modules:** `modules/photo_manager/manager.py`, `modules/backup_system/backup.py`

**Tests:**
Unit tests should verify that after a simulated photos‑folder replace, subsequent calls to `engine_photo_disk_paths` return the updated list. Integration tests can mimic a backup restore and check that photo listings are correct.

---

### [P3] Duplicate logic for associating modes and works with an engine

**File:** `routes/engines.py`

**Location:** `create_engine()` (lines 77‑96) and `update_engine()` (lines 99‑126)

**Problem:**
Both functions contain nearly identical blocks that, after creating/updating the engine record, call `replace_modes()` and `replace_works()` when the incoming payload includes `modes` or `works`. This duplication increases the chance of inconsistency if the logic needs to change (e.g., adding validation or transaction handling).

**Why it matters:**
While the duplication is minor, it violates the DRY principle and makes future changes more error‑prone. Centralising this logic improves maintainability.

**Recommended change:**
Extract a helper function `_save_modes_and_works(conn, engine_id, data)` that handles the conditional replacement of modes and works. Call it from both `create_engine` and `update_engine`.

**Risk:** Low (refactoring is straightforward and does not alter behavior).

**Affected modules:** `routes/engines.py`

**Tests:**
Existing tests for engine creation and update should continue to pass. No new test logic is required.

---

### [P4] Import routine assumes empty DB and computes IDs from `last_insert_rowid`

**File:** `routes/import_routes.py`

**Location:** Lines 117‑130 (ID calculation) and the guard at lines 85‑102

**Problem:**
The mass import endpoint first checks that the engine table is empty, then inserts all engines in a single transaction and derives the assigned IDs by subtracting the count from `last_insert_rowid`. This works only under the guarantee of an empty table and no concurrent inserts. While the guard enforces emptiness, the comment notes that the assumption is critical. If the guard were bypassed (e.g., via a race condition or future code change), ID assignment would become incorrect, causing mismatched foreign keys for modes and works.

**Why it matters:**
The correctness of the import relies on a fragile assumption. Although protected by a runtime check, any future modification that removes or weakens that check could silently corrupt data.

**Recommended change:**
Replace the custom ID calculation with a call to the repository’s `_next_free_id()` (or reuse the `create` function) for each engine, wrapping the entire import in a transaction. This would make the import robust to non‑empty tables and eliminate the dependency on insertion order. Performance impact is minimal given typical import sizes.

**Risk:** Medium (changes the ID generation strategy but eliminates a subtle bug class).

**Affected modules:** `routes/import_routes.py`, `repositories/engine_repo.py`

**Tests:**
Unit tests should verify that importing into a non‑empty database (with the guard removed) still produces correct IDs and foreign‑key relationships.

---

### [P5] Auth before_app_request loads current_user for every API request (except login)

**File:** `routes/auth.py`

**Location:** `load_current_user()` (lines 45‑64)

**Problem:**
The `before_app_request` hook in the auth blueprint executes for every request under `/api/` (except the login endpoint). It extracts the token, queries the database to load the user object, and stores it on `request.current_user`. For GET requests that do not require user data (e.g., serving static assets, health checks, or public endpoints), this work is unnecessary. While the overhead is small, it adds unnecessary latency and database load.

**Why it matters:**
In high‑traffic scenarios, the extra query per request can accumulate. Moreover, it couples the auth mechanism to all routes, making it harder to introduce truly public API endpoints in the future without modifying the hook.

**Recommended change:**
Move the user‑loading logic into a dedicated decorator (e.g., `@require_auth`) and apply it only to endpoints that actually need the user object. Keep the `before_app_request` hook solely for enforcing authentication/authorization on write‑only routes, or replace it with a more granular approach.

**Risk:** Low (refactoring is localized and improves clarity).

**Affected modules:** `routes/auth.py`

**Tests:**
Ensure that protected endpoints still receive `request.current_user` and that public endpoints (if any) do not incur the user‑lookup overhead.

---

## Things NOT Worth Refactoring

- The use of `PRAGMA journal_mode=WAL` and `synchronous=NORMAL` in `modules/db.py` – these are deliberate performance choices for SQLite and are appropriate given the application’s workload.
- The separation of file‑based and database‑based users in `modules/auth` – while it adds complexity, it supports a specific deployment scenario (initial admin setup) and is well‑encapsulated.
- The global `_photo_paths_cache` in the photo manager – **only** if the cache is removed or made safe (see P2). As‑is, it is a liability.
- The duplicate DELETE endpoint in `routes/backup_routes.py` (`/api/backup/delete/<filename>` and `/api/backup/<filename>`) – kept for backward compatibility; the cost is minimal.
- The heavyweight Excel generation in `services/export_service.py` – this is isolated to the export feature and does not affect core request latency.

## Recommended Refactoring Order

1. **Fix engine deletion orphaned photos (P1)**
   - **Benefit:** Eliminates a tangible data‑corruption risk.
   - **Complexity:** Low‑Medium (requires adding rollback or changing order, plus error handling).
   - **Risk:** Medium (touching deletion flow; ensure tests cover failure cases).
   - **Files:** `routes/engines.py`, optionally `modules/photo_manager/manager.py` for better error reporting.

2. **Make photo manager cache safe (P2)**
   - **Benefit:** Prevents stale data after backup restore and in multi‑worker setups.
   - **Complexity:** Low (clear cache after folder replace) to Medium (timestamp‑based validation).
   - **Risk:** Low.
   - **Files:** `modules/photo_manager/manager.py`, `modules/backup_system/backup.py`.

3. **Refactor modes/works association logic (P3)**
   - **Benefit:** Reduces duplication, centralises behaviour.
   - **Complexity:** Low.
   - **Risk:** Very Low.
   - **Files:** `routes/engines.py`.

4. **Replace import ID calculation with repository helper (P4)**
   - **Benefit:** Removes fragile assumption, improves robustness.
   - **Complexity:** Low‑Medium (adjust import loop, ensure transaction).
   - **Risk:** Low.
   - **Files:** `routes/import_routes.py`, `repositories/engine_repo.py`.

5. **Move user loading to decorator (P5)**
   - **Benefit:** Reduces unnecessary DB queries, clarifies auth responsibilities.
   - **Complexity:** Low.
   - **Risk:** Low.
   - **Files:** `routes/auth.py`.

## Suggested Target Architecture

No fundamental architectural changes are needed. The current layered structure is sound. The recommended refactors stay within existing layers and improve internal consistency without altering the public API or data model.

## Final Recommendation

Focus first on the two reliability‑critical issues (engine deletion photo cleanup and photo manager cache safety). They address real risks of data inconsistency and are relatively inexpensive to fix. The remaining refactors are clean‑ups that will improve maintainability but can be scheduled for later sprints. All changes should be accompanied by unit‑ or integration‑level tests to guard against regressions.

���📲 Уведомление отправлено в ntfy
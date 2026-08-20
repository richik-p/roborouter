# RoboRouter agent instructions

Read `START_HERE.md`, `docs/PRODUCT.md`, `docs/MVP.md`, `docs/ARCHITECTURE.md`,
`docs/DATA_MODEL.md`, `docs/SAFETY.md`, and `docs/DECISIONS.md` before changing
core behavior.

## Engineering rules

- Keep policy adapters separate from robot adapters.
- Treat executable policy revisions and rollout provenance as immutable.
- Compatibility is evidence-backed and graded; never infer unknown camera,
  state, action, normalization, frame, or controller semantics.
- Keep physical actuation absent until an approved M6 ExecPlan enables it.
- The robot-side runtime is always the physical safety authority.
- Prefer a working vertical slice over premature services or abstractions.
- Add or update tests whenever a contract, compatibility rule, job transition,
  or safety behavior changes.
- Use an ExecPlan under `docs/plans/` when `PLANS.md` requires one.

## Validation

Run `make check` before handing off changes. Run the browser end-to-end suite
when web behavior changes. Remote GPU smoke tests are opt-in and must record
the exact upstream revisions used.


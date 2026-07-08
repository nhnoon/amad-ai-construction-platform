---
name: Orval zod target — no schemas dir
description: Why lib/api-zod/src/index.ts is manually maintained and not regenerated
---

`lib/api-zod/src/index.ts` is a **manually maintained** re-export barrel. Do not regenerate it with orval.

**Why:** Adding a `schemas` option to the `zod` target in `orval.config.ts` caused orval to write a `schemas/` directory AND the main output file, both exporting the same types. This produced duplicate export conflicts at the `lib/api-zod` level. Removing `schemas` from the `zod` target and writing a simple `export * from './generated/...'` barrel fixed codegen cleanly.

**How to apply:** After running codegen, `lib/api-zod/src/index.ts` must still export from the generated Zod file path. Only touch it if the generated output path changes.

# v0.24.1 native-build compatibility hotfix

## Failure that was reported

Rust compiler emitted `E0308` at `src/main.rs:57` and five `E0277` errors at `:76`, `:77`, `:80`, `:87`, and `:93` when compiling `claims-dogwood-gate` with `dogwood-language = 1.1.1` and `dogwood-local-engine = 1.1.2`.

## Fix

- Pass `&principal`, not `principal`, to `EventBuilder::principal(&str)`.
- Convert `DurableError` into `std::io::Error` with context before using `?` in a `Result<T, Box<dyn std::error::Error>>` function. This preserves fail-closed behavior.
- Policy and Cedar schema unchanged; audit contract format remains `v0.24.0`.

## Verification status

- Python: `cd backend && python -m pytest -q --disable-warnings --maxfail=1` => **123 passed** in the authoring environment.
- Native Rust compile and Dogwood runtime: **not executed in the authoring environment** (Rust/Docker unavailable). User needs to run the following on a Docker-equipped system:

```bash
docker compose build --no-cache api
# The Dockerfile runs `cargo test --release && cargo build --release`.
docker compose up -d --force-recreate
docker compose exec -T api sh -c 'test -x /usr/local/bin/claims-dogwood-gate'
```

If the native tests fail for an independent policy/schema/runtime reason, capture the first `error:` or `panicked at` and the preceding lines for another source-level fix.

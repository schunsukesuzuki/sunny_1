# Optional native build (also used by ../Dockerfile's Rust build stage).
# Requires crates.io/network access on the developer's machine at build time.
FROM rust:bookworm AS build
WORKDIR /src
COPY Cargo.toml ./Cargo.toml
COPY src ./src
COPY policy ./policy
RUN cargo test --release --quiet > /tmp/dogwood-rust-tests.log 2>&1 \
    || { cat /tmp/dogwood-rust-tests.log; exit 1; }
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=build /src/target/release/claims-dogwood-gate /usr/local/bin/claims-dogwood-gate
COPY --from=build /tmp/dogwood-rust-tests.log /opt/dogwood-rust-tests.log
USER 65534:65534
ENTRYPOINT ["/usr/local/bin/claims-dogwood-gate"]

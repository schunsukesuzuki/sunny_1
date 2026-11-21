# Optional native build (also used by ../Dockerfile's Rust build stage).
# Requires crates.io/network access on the developer's machine at build time.
FROM rust:bookworm AS build
WORKDIR /src
COPY Cargo.toml ./Cargo.toml
COPY src ./src
COPY policy ./policy
RUN cargo test --release && cargo build --release

FROM debian:bookworm-slim
COPY --from=build /src/target/release/claims-dogwood-gate /usr/local/bin/claims-dogwood-gate
USER 65534:65534
ENTRYPOINT ["/usr/local/bin/claims-dogwood-gate"]

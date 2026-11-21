# Build the real Dogwood Local Engine policy adapter (Rust, compiled at image build).
FROM rust:bookworm AS dogwood-builder
WORKDIR /dogwood
COPY dogwood_gate/Cargo.toml ./Cargo.toml
COPY dogwood_gate/src ./src
COPY dogwood_gate/policy ./policy
RUN cargo test --release && cargo build --release

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements-solver.txt ./
ARG INSTALL_SOLVER=0
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_SOLVER" = "1" ]; then pip install --no-cache-dir -r requirements-solver.txt; fi
COPY app ./app
COPY dogwood_gate/policy ./dogwood_gate/policy
COPY --from=dogwood-builder /dogwood/target/release/claims-dogwood-gate /usr/local/bin/claims-dogwood-gate
COPY skills ./skills
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

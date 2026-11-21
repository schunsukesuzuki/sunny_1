FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements-solver.txt ./
ARG INSTALL_SOLVER=0
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_SOLVER" = "1" ]; then pip install --no-cache-dir -r requirements-solver.txt; fi
COPY app ./app
COPY skills ./skills
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

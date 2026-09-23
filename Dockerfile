# Dashboard Aksesibilitas TES Banjir Kulon Progo — image untuk Hugging Face Spaces (Docker)
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

# Hugging Face Spaces menjalankan container sebagai user UID 1000
RUN useradd -m -u 1000 user
WORKDIR /app

COPY --chown=user:user requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY --chown=user:user . .
# folder cache graf jalan harus dapat ditulis
RUN mkdir -p /app/scratch/graph_cache && chown -R user:user /app

USER user
EXPOSE 7860

# satu worker: state data & cache graf disimpan di memori proses
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]

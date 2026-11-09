FROM python:3.12-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/hf_cache \
    PYTHONUNBUFFERED=1

# CPU-only torch keeps the image much smaller
RUN pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY data ./data
COPY src ./src
COPY tests ./tests

# Internet is used only here: download DictaBERT and fit the model once.
RUN python -m src.model

# From here on everything runs offline
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1
EXPOSE 8000
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]

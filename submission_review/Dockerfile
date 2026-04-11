FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "openenv-core[core]>=0.2.2" \
    uvicorn \
    fastapi \
    openai \
    requests \
    pydantic

COPY . .

EXPOSE 7860

ENV ENABLE_WEB_INTERFACE=true

CMD ["python", "server/app.py"]

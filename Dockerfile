FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 botuser

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=botuser:botuser app ./app
COPY --chown=botuser:botuser aggregation/csv ./aggregation/csv
COPY --chown=botuser:botuser aggregation/export/media ./aggregation/export/media

USER botuser

EXPOSE 10000

CMD ["python", "-m", "app.main"]

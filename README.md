# Travel Bot

Telegram bot for browsing travel places from normalized CSV files in `aggregation/csv`.

## Configuration

Create `.env` from `.env.example` and set:

```env
BOT_TOKEN=your-telegram-bot-token
CSV_DIR=aggregation/csv
MEDIA_ROOT=aggregation/export
```

`BOT_TOKEN` is required. `CSV_DIR` and `MEDIA_ROOT` are optional. Local image
paths such as `media/image1.jpg` are resolved relative to `MEDIA_ROOT`.

## Run

```bash
pip install -r requirements.txt
python -m app.main
```

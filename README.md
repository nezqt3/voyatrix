# Travel Bot

Telegram bot for browsing travel places from normalized CSV files in `aggregation/csv`.

## Configuration

Create `.env` from `.env.example` and set:

```env
BOT_TOKEN=your-telegram-bot-token
CSV_DIR=aggregation/csv
```

`BOT_TOKEN` is required. `CSV_DIR` is optional and defaults to `aggregation/csv`.

## Run

```bash
pip install -r requirements.txt
python -m app.main
```

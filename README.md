# Travel Bot

> **PROPRIETARY COMMERCIAL SOFTWARE — ALL RIGHTS RESERVED**
>
> Copyright © 2026 Alekseenko Denis. This project is not open source. No use,
> copying, modification, distribution, deployment, hosting, resale, or creation
> of derivative works is permitted without prior written authorization. See
> [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

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

Keep `.env` local. Never commit it or copy it into a published Docker image.

## Run

```bash
pip install -r requirements.txt
python -m app.main
```

For development and tests, install `requirements-dev.txt` instead.

Without a public URL the bot uses long polling, which is convenient for local
development and a regular VM.

## Docker

```bash
docker compose up --build -d
docker compose logs -f bot
```

Redis and a database are not required. The Compose service automatically
restarts unless it is explicitly stopped.

## Deploy to Render

The repository contains a `render.yaml` Blueprint for a free Docker Web
Service. On Render the bot automatically switches from polling to a Telegram
webhook using Render's `RENDER_EXTERNAL_URL`.

1. Revoke any previously exposed Telegram token in `@BotFather` and generate a
   new token.
2. Push the repository to GitHub or GitLab.
3. In Render, choose **New > Blueprint** and connect the repository.
4. When prompted, set `BOT_TOKEN` to the new token.
5. Set `WEBHOOK_SECRET` to a long random value containing only letters,
   numbers, `_`, and `-`.
6. Deploy and wait until `https://<service>.onrender.com/health` returns
   `{"status":"ok"}`.
7. Send `/start` to the bot. The webhook is registered automatically during
   every service startup.

The free Render service sleeps after a period without inbound traffic. A new
Telegram webhook request wakes it, so the first response after a quiet period
can be delayed. Free services can also restart at any time and do not provide
production availability guarantees.

### Local images

The Docker build includes `aggregation/export/media` when that directory is
present in the build context. Those images are currently ignored by Git, so a
Render build made directly from this repository will show text cards instead
of the 1,659 local photos. To deploy the photos too, either publish them in
object storage and put HTTPS URLs in `places.csv`, or intentionally add the
media assets to the deployment source after checking their size and usage
rights.

## Versioned parser snapshots

Run the complete DOCX parsing pipeline with:

```bash
python -m aggregation.main
# or
make parse
```

Every successful run creates an immutable timestamped directory:

```text
aggregation/snapshots/2026-08-28_14-35-20/
├── export/
│   ├── media/
│   └── text.json
├── merged_data/places.csv
├── csv/*.csv
├── reports/
│   ├── audit_report.txt
│   ├── comparison_report.txt
│   └── comparison.json
└── manifest.json
```

`comparison_report.txt` shows the count delta and lists places that were added,
removed, or changed since the previous successful snapshot. The JSON report
contains the same data for automation. Place matching uses semantic location,
category, and name instead of paragraph numbers, so inserting a paragraph near
the top of the DOCX does not make every later place look new.

Only after extraction, normalization, audit, and comparison all succeed is the
snapshot copied to the live `aggregation/csv`, `aggregation/merged_data`, and
`aggregation/export` directories used by the bot. `snapshots/latest.json`
records which version was published. A failed run writes its traceback to a
`*_FAILED/error.txt` directory and leaves the live catalog unchanged.

The running bot checks the published `places.csv` version on each catalog
request. When a new snapshot replaces the live catalog, all CSV tables are
reloaded automatically without restarting the bot.

Snapshots include media and can use significant disk space. They are ignored
by Git and are retained until you intentionally archive or remove them.

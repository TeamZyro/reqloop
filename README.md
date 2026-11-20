# ReqLoop — Hindi Song Request Worker

A Python worker that sends unique Hindi-song YouTube video IDs to the configured Xenobot2 URL endpoint.

## What it does

- Starts with 53 curated Hindi songs and shuffles their order.
- Stores requested video IDs in `played_hindi_songs.json` to avoid duplicates during the current filesystem lifetime.
- Searches YouTube for additional candidate songs after the curated queue is exhausted.
- Sends one GET request on the configured interval.
- Logs HTTP status codes, response time, and errors.

> This script sends API requests. It does not itself play audio in a Telegram voice chat; playback depends on the API backend.

## Heroku deployment

This repository is configured as a **worker process**, not a web app.

1. Create a Heroku app and connect this GitHub repository, or deploy it with the Heroku CLI.
2. Ensure the `heroku/python` buildpack is selected.
3. Deploy the `main` branch.
4. Scale the worker process to one instance:

   ```bash
   heroku ps:scale worker=1 -a YOUR_HEROKU_APP
   ```

5. View logs:

   ```bash
   heroku logs --tail -a YOUR_HEROKU_APP
   ```

The included `Procfile` runs:

```bash
python -u "Auto Play Hindi Songs.py" --interval 3.6 --limit 3000
```

That schedules at most 3,000 requests, approximately one every 3.6 seconds. The process exits when the limit is reached. Confirm that you own or are authorized to use the target API and that its rate limits permit this request rate before starting the worker.

## Local run

Requires Python 3.9+.

```bash
python3 "Auto Play Hindi Songs.py" --dry-run --limit 10
```

To send real requests locally:

```bash
python3 "Auto Play Hindi Songs.py" --interval 3.6 --limit 3000
```

Other options:

- `--reset`: clear the local played-song history before starting.
- `--no-auto-discover`: use only the curated song list.
- `--dry-run`: print requests without calling the API.

## Important notes

- The app has no web server; use a Heroku **worker** dyno.
- Heroku dyno filesystems are ephemeral. The JSON history file is not durable across dyno replacement/recreation, so do not treat it as permanent storage.
- HTTP errors and timeouts are logged, but the current script does not retry failed requests.
- The script uses Python's standard library and requires no external pip packages.

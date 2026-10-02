# Product Research and Personalized Notifications

This prototype contains a resumable Books to Scrape collector, strict preference matching for ten fictional customers, personalized message drafts, and gated provider adapters for one controlled test send. Product prices and ratings come from the site's deliberately fictional practice catalogue.

## What is included and what was actually run

- `extract_products.py`: Python standard-library crawler for five catalogue pages and each product detail page; upserts by URL and checkpoints after every product. It handles missing fields as blank values and logs failed detail requests.
- `verify_sample.py`: refetches five spaced product detail pages and compares the required fields to the saved CSV.
- `match_and_message.py`: cleans/deduplicates the extracted CSV, enforces exact category, budget and minimum-rating conditions, ranks qualifying products, records reasons, and creates email/WhatsApp copy.
- `deliver.py`: default mode is local draft/simulation and never calls a provider. Explicit test sending additionally requires `delivery.mode=test`, `--send`, controlled recipients, a Gmail OAuth access token or WhatsApp Cloud API access token, and WhatsApp phone-number ID. API acceptance is logged as `API_ACCEPTED`, never as receipt. Uncertain requests are recorded and blocked from automatic retry.
- `delivery_failure_demo.py`: creates a clearly labeled local failure and duplicate-block demonstration without contacting a provider.
- `customers.csv`: fictional customer preferences only. It contains no email addresses or phone numbers.
- `PAD_FLOW.md`: reconstruction instructions for the Windows-only PAD flow.
- `output/`: generated product data, checkpoint, matches, messages and logs.

This package was built on macOS. The live Python extractor was used to collect the included source data; it fetches catalogue/detail HTML directly and is **not** proof of a PAD browser run. PAD, Gmail authentication, WhatsApp Business Platform setup, actual sends, receipt evidence, screenshots, and screen recording were not available in this environment. No message was sent. The PAD flow instructions are for reconstruction on Windows and are not an exported PAD flow file.

## Run

Requires Python 3.10+; no third-party dependencies.

```sh
cd product_research
python3 extract_products.py --config config.json
python3 verify_sample.py
python3 match_and_message.py --config config.json
python3 deliver.py --config config.json
```

The extractor collects up to the configured 100 records from five 20-book catalogue pages. Running it again reads `output/checkpoint.json`, skips completed pages and duplicate product URLs, and resumes pages interrupted before completion. To repeat from a clean start, move or delete `output/checkpoint.json` and `output/products.csv` yourself.

PAD should call `run_pipeline.py --extract --prepare` from **Run application**, with this folder as working directory. Python communicates with PAD through the CSV/JSON files and process exit status. PAD owns browser navigation and its visible workflow; the direct HTTP extractor is included for this macOS demo and as a fallback/reproducible crawler implementation.

## Matching and message rules

Categories compare case-insensitively as exact labels. A product must have a parsed price and rating, belong to a preferred category, cost no more than the customer's budget, and meet the minimum star rating. At most three results are emitted, sorted by rating descending, then price ascending. An empty match set is explicitly stated. Recommendations are explanations of the site's assigned data, not personalized claims beyond those fields.

## Draft and test sending

The ten generated sets are in `output/messages.json`. Default `deliver.py` records an email `DRAFT_PREPARED` and WhatsApp `SIMULATED_ONLY` for each customer; these are local payloads, not drafts placed in Gmail and not WhatsApp sends. To use Gmail API and WhatsApp Cloud API, configure only your own controlled test recipients and provider identifiers in `config.json`, set OAuth/API tokens in environment variables (`GMAIL_ACCESS_TOKEN`, `WHATSAPP_ACCESS_TOKEN`), set `delivery.mode` to `test`, then deliberately run:

```sh
python3 deliver.py --config config.json --send --sample C001 --channels email,whatsapp
```

This one-message-per-channel option must be used only with destinations you control or have permission to message. Never commit token values. Delivery state uses a content/recipient/channel key and will block repeated attempts; on `UNCERTAIN`, do not automatically retry. Inspect the provider manually first. Gmail/WhatsApp API acceptance is not confirmed receipt; record inbox/WhatsApp receipt separately. This environment was not authenticated, so the send path was not exercised.

The separate `output/delivery_failure_demo.log` demonstrates a simulated failed attempt followed by `DUPLICATE_BLOCKED`; it is not evidence of a provider error or a delivered message. The normal `output/delivery.log` records the ten local email payloads, ten WhatsApp simulation-only results, and the duplicate-blocked second draft run.

## Evidence to complete on Windows

Follow the recovery and recording checklist in `PAD_FLOW.md`. Export/save the actual PAD flow and subflows after reconstruction; record the visible five-page browsing, product detail navigation, Python call, checkpoint resume, matching/message outputs, duplicate prevention, one controlled email receipt, and one controlled WhatsApp receipt or the precise official test-setup blocker. Keep secrets out of screenshots and the video. Do not describe simulation as delivery.

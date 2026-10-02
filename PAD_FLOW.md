# Power Automate Desktop reconstruction guide

## Compatibility and transfer

This submission was assembled and run on macOS. PAD is Windows-only, so there is no genuine `.pad` export, PAD run history, or Windows UI recording in this package. Reconstruct the following flow in Power Automate Desktop on Windows and save it as `ProductResearch.pad`; use the Python source in this folder as its callable processing layer. This is a precise action sequence, not a claim that PAD ran here.

## Main flow: `ProductResearch_Main`

1. **Set variables**: `ProjectDir` to this folder; `ConfigPath` = `%ProjectDir%\config.json`; `OutputDir` = `%ProjectDir%\output`; `RunMode` = `draft`. Read config JSON with *Read from JSON file* (or use the literal defaults from `config.json`).
2. **Create folders** if `OutputDir` does not exist. Append timestamped `PAD_START` to `output\processing.log`.
3. **Try block / On block error**: launch Chrome (visible) at the configured source URL. Keep the browser visible for the demonstration.
4. Read `catalogue_pages` and `max_products`. For page numbers 1 through 5 (or configured count), navigate the browser to `/catalogue/page-<n>.html` (page 1 is `/`). Wait for page load. Confirm a product listing is present. Record the current page URL and timestamp to `processing.log`.
5. For each listing card, collect its product link. Navigate the browser to the link, wait for the detail page, and collect title, price, star rating, breadcrumb category, availability, and description. Build a row in a PAD data table. On missing elements, write an empty value, log `FIELD_MISSING` with URL/field, then continue.
6. Avoid duplicate URLs by checking the product URL against the data table before adding. After each detail page, persist the table to a temporary CSV and rename it to `products.csv`; write `checkpoint.json` with completed pages, last URL, and record count. If interrupted, reload both files, skip known URLs, and resume.
7. After each page, navigate to the next configured catalogue page. Stop at `max_products`. Close browser only after extraction or an error is logged.
8. Run Python action (below) with `--prepare`, wait for completion, check exit code, and log `PREPARATION_OK` or `PREPARATION_FAILED`.
9. Keep sending disabled. For the optional one-recipient demonstration, require an operator to set `delivery.mode` to `test` in the config and explicitly enable the `--send` branch. Run only one sample ID to a recipient the operator controls. Never put credentials into flow variables or the recording.

## Suggested subflows

- `ExtractCatalog`: the browser navigation, listing iteration, product detail navigation, field capture and URL deduplication steps above.
- `PersistCheckpoint`: append valid rows to the CSV, write current page/last URL/count to the checkpoint, and leave failed detail URLs eligible for a later rerun.
- `PrepareMatchesAndMessages`: run `run_pipeline.py --prepare` (after extraction), wait for exit, then surface `matching_results.csv` and `messages.json` in PAD.
- `DraftOrTestDelivery`: default to local draft/simulation. If the operator explicitly enabled test mode, pass the single selected sample and channel list to the send action; record the returned state and stop on uncertainty.

## Python call action

Use **Run application** with application path to the installed Python executable, arguments `"%ProjectDir%\run_pipeline.py" --prepare`, and working folder `%ProjectDir%`. To run extraction from PAD use `"%ProjectDir%\run_pipeline.py" --extract --prepare`. Python writes `output\products.csv`, `checkpoint.json`, `processing.log`, `matching_results.csv`, and `messages.json`. PAD owns navigation and browser visibility; Python cleans, matches, and prepares messages. On this Mac prototype, `extract_products.py` also has a direct HTTP mode for reproducible data collection; this was used to create the included sample CSV and must not be described as a PAD browser run.

## Recovery and recording checklist (perform on Windows)

- Start extraction, interrupt after one catalogue page, rerun, and show that prior product URLs are skipped while the checkpoint resumes. The Python extractor writes each detail record immediately; PAD flow should do the same.
- Use a deliberate unavailable test value in a copy of the config or stop the network before extraction; capture a failed page log, restore connectivity, resume, and show completion.
- Run `deliver.py` twice in draft mode and show `DUPLICATE_BLOCKED` entries in `delivery.log`. For send recovery, never retry a channel attempt with result `UNCERTAIN`; inspect provider state manually first.
- Capture one sample email sent only to your own controlled inbox and one WhatsApp test message to a controlled test number if the official test setup is available. Capture inbox/message receipt (not only the API response) while hiding tokens, account identifiers, and unrelated personal information.
- If WhatsApp setup is unavailable, retain the `SIMULATED_ONLY` log outcome and screen-capture the exact missing setup requirement; do not show it as a sent message.

## PAD details to implement

Use `For each` over the listing element collection; `Extract data from web page` can capture list card title/link/rating/price. Use `Go to web page` for each detail URL and `Extract data from web page` for detail fields. Selector suggestions: listing `article.product_pod`; detail title `div.product_main h1`, price `div.product_main p.price_color`, stock `div.product_main p.instock`, stars `div.product_main p.star-rating` class, category `ul.breadcrumb li:nth-child(3)`, description `#product_description + p`. Verify selectors in PAD's browser recorder for your browser version before running.

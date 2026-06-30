# Gwydion Bid Tool

Standalone helper to enter a round of DKP bids and work out who wins each item,
cross-checking each bid against the **live master spreadsheet the bot uses**
(read-only). Independent of the bot — it never imports `gwydion dkp.py`.

## Run it

```bash
python bidtool/bidtool_gui.py
```

A window opens. Add items (name, KP pool, quantity), then for each item add the
bidders and their bids. Tick **Validate against live sheet** to check
affordability, then hit **Resolve ▶**. Results appear in the template style you
post in Discord, with ⚠ flags for anything that needs a manual decision. You can
**Save CSV** to keep the round and **Open CSV** to reload it later.

### Headless / scripting

```bash
python bidtool/bidtool_gui.py template blank.csv        # write a fill-in template
python bidtool/bidtool_gui.py resolve mybids.csv        # validate against live sheet
python bidtool/bidtool_gui.py resolve mybids.csv --offline   # no balance checks
```

## What it needs for live validation

* `pip install gspread`
* The bot's read-only credentials file `paranoid-kp-bot-b724a91cd608.json`
  (account 4, "lia-leaderboard-bot") in the project root next to
  `gwydion dkp.py`. Override the location with the `BIDTOOL_CREDS` env var.

Without these it still resolves **offline** — it just picks the raw highest
bidder per item and skips affordability/disqualification. (The GUI offers to
fall back automatically; the CLI does so with a warning.)

## CSV format

One row per bid:

```csv
item,kp,qty,bidder,for_player,amount
Defiled Fetter of the poisoner,VKP,1,Chich1,,200
Voidsworn hammer of Ashes,DPKP,1,Chich1,CarlosOrtis,750
Imperial Eidolic Necklace Of Brawlers,DPKP,2,Chich1,,200
```

* `kp` — the pool: `VKP`, `GKP`, `PKP`, `AKP`, `RBPPUNOX`, `DPKP`, `RBPP`.
* `qty` — how many copies of the item exist (top `qty` bids each win one).
* `for_player` — recipient for a proxy bid; leave blank if the bidder keeps it.
  The **bidder** always pays (mirrors the bot's `$sendbid` / `$deduct`).

## How winners are decided

* Highest bid wins; the named bidder pays out of that item's KP pool
  (`Current`, column 7 — exactly the value the bot checks).
* `qty` copies → the top `qty` bidders each win one and **each pays their own
  bid**, listed as separate blocks. With ≤ `qty` bidders it's uncontested.
* A bid the bidder can't afford on its own is **disqualified** and the next
  bidder is promoted (shown with ✗).
* An exact tie for a winning slot is **flagged for a manual roll** — never auto
  broken.
* If one bidder's combined wins in a pool exceed their balance (cumulative
  **overrun**), all of that bidder's wins are flagged for you to sort out
  manually rather than auto-dropping any.

## Files

| File | Role |
|------|------|
| `bidtool_gui.py` | Tkinter GUI + headless CLI (entry point) |
| `bid_resolver.py` | Pure winner logic (no Discord/gspread/Tk) |
| `sheet_reader.py` | Live read-only access to the master sheet |
| `bid_io.py` | CSV load / save / template |
| `test_bid_resolver.py` | Unit tests for the resolver |
| `sample_bids.csv` | The example round, ready to resolve offline |

## Tests

```bash
python bidtool/test_bid_resolver.py
```

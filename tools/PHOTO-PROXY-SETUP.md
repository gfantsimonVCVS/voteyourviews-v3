# Photo Proxy — one-time Google setup

The "Get missing photos" button (Google route) needs two free Google credentials. ~10 minutes, once.

## 1. Get a Google API key
1. Go to **https://console.cloud.google.com/** and sign in.
2. Create a project (or pick one) — top bar project dropdown → New Project → name it `voteyourviews` → Create.
3. Enable the API: search bar → **"Custom Search API"** → **Enable**.
4. Left menu → **APIs & Services → Credentials → Create credentials → API key**. Copy the key (looks like `AIza...`).

## 2. Create a Programmable Search Engine (gives the "CSE ID")
1. Go to **https://programmablesearchengine.google.com/** → **Add**.
2. Name it anything. Under "What to search?" pick **"Search the entire web."**
3. Create it → open its **Control Panel** → turn **ON "Image search."**
4. Copy the **"Search engine ID"** (looks like `a1b2c3d4e5...`).

## 3. Plug them in
Create a file **`tools/photo-proxy.config.json`** (this is gitignored — never committed):
```json
{ "api_key": "AIza...your key...", "cse_id": "your-search-engine-id" }
```

## 4. Run the proxy (leave it running while you source photos)
```
cd "/Users/ginafant-simon/Downloads/State Over Party V3"
PATH="$HOME/Library/Python/3.9/bin:$PATH" python3 tools/photo-proxy.py
```
You should see `Photo proxy running on http://localhost:8770`. Leave that terminal open.

## 5. Use it
In the photo tool (in real Chrome, `localhost:8761/photo-tool.html`): load a county →
**✨ Get missing photos** → it auto-fills the top Google image for each missing candidate
(background removed, squared). **Verify each** (amber "VERIFY" flag) — reject/replace any wrong
person — then Approve. Whatever it can't find drops to the guided search.

## Notes
- **Free tier = 100 searches/day.** Plenty for a county; if you hit the cap, it resets next day.
- The key stays on your Mac (in the gitignored config). Never paste it into the browser or commit it.
- Quality: uses the same `u2net_human_seg` background removal as the rest of the pipeline.

# Candidate Photo Solutions

## The Problem
Google Drive photos (`lh3.googleusercontent.com/d/...`) require Google authentication to load.
Works for you when logged in — fails for all other users, including deployed site visitors.

## Recommended Workflow at Scale

### Step 1 — Background Removal: Remove.bg
- **Best-in-class** AI background removal
- Free tier: 50 images/month
- Bulk credits: ~$50–80 for 600 images (one-time per election cycle)
- API available for scripted bulk processing
- https://remove.bg

### Step 2 — Hosting + Transforms: Cloudinary
- Upload processed PNGs once, get a permanent public CDN URL
- URL-based transformations (no Photoshop needed):
  - `g_face` — auto-centers crop on the face
  - `r_max` — circular crop
  - `b_rgb:e2e8f0` — adds a consistent background color
  - `w_400,h_400,c_fill` — uniform 400×400 size
- Free tier: 25 GB storage, 25 credits/month — covers hosting fine
- Example URL: `https://res.cloudinary.com/yourname/image/upload/g_face,w_400,h_400,c_fill,r_max/candidates/talarico.png`
- https://cloudinary.com

### Step 3 — Google Sheet
- `photo` column in each county sheet gets the Cloudinary URL
- App loads it automatically — no code changes needed

## Scale Estimate (Top 10 Texas Counties)

| Item | Count | Cost |
|------|-------|------|
| Statewide candidates | ~100 | shared across all counties |
| Local candidates (10 counties) | ~500 | unique per county |
| **Total unique photos** | **~600** | |
| Remove.bg processing | 600 images | ~$50–80 one-time |
| Cloudinary hosting | free tier | $0 |
| **Total** | | **~$50–80 per election cycle** |

## Automation Script (To Build)
A Python script that:
1. Reads candidate names + existing photo URLs from Google Sheet
2. Sends each photo to Remove.bg API → gets transparent PNG back
3. Uploads PNG to Cloudinary with standard transformation settings
4. Writes the final Cloudinary URL back to the Google Sheet `photo` column

This would process all 600 candidates in one run (~20 minutes).

## Alternative: GitHub + jsDelivr (Free, No Background Removal)
- Store photos in a GitHub repo
- Serve via jsDelivr CDN: `https://cdn.jsdelivr.net/gh/account/repo@main/photos/talarico.jpg`
- Free forever, version controlled
- Manual photo management (no background removal)
- Good for getting started quickly before investing in Cloudinary

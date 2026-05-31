# Indie Folk 2026 - Playlister Results Tracker

**Generated:** 2026-05-29 13:27  
**Source:** Playlister search (results ID 437570)  
**Total Playlists:** 180

## How to Use This CSV

### Recommended: Google Sheets (Best on Mac)

1. Go to [sheets.google.com](https://sheets.google.com) and create a new spreadsheet.
2. File → Import → Upload → Select `Indie_Folk_2026_Tracker.csv`
3. In the import options:
   - Separator type: **Detect automatically** (or Comma)
   - Convert text to numbers/dates: **No** (keep everything as text)
4. Once imported:
   - Freeze the header row (View → Freeze → 1 row)
   - Turn on Filters (Data → Create a filter)
   - Optionally create a "Status" dropdown via Data validation

### Alternative: Apple Numbers (native on Mac)

1. Double-click the CSV file — it should open in Numbers.
2. Or File → Open in Numbers.
3. It will usually convert cleanly.

### Column Guide

| Column                    | Purpose                                      | Who Fills It      |
|---------------------------|----------------------------------------------|-------------------|
| Rank                      | Our suggested order to review                | Pre-filled        |
| Priority Score            | Heuristic score (0–1). Higher = better candidate | Pre-filled     |
| Title                     | Playlist name from Playlister                | Pre-filled        |
| Subscribers               | Follower count                               | Pre-filled        |
| Description (short)       | Short description (may contain clues)        | Pre-filled        |
| Playlister Internal ID    | Internal ID (useful if you need to reference back) | Pre-filled |
| **Spotify URL**           | The real open.spotify.com link               | **You**           |
| **Contact Type**          | IG Handle / Email / Form/Bitly / etc.        | **You**           |
| **Contact Detail**        | The actual @handle, email, or link           | **You**           |
| **Status**                | Progress tracker (see dropdown values)       | **You**           |
| Notes                     | Any extra observations                       | **You**           |
| Date Reviewed             | When you checked this one                    | **You**           |

### Suggested Status Values

- `Not Reviewed` (default)
- `Revealed - No Contact`
- `Revealed - Has Contact`
- `Imported`
- `Skipped`
- `Pitched`

### Recommended Workflow

1. Sort/filter by **Rank** or **Priority Score** (highest first).
2. Open Playlister in a browser and work down the list.
3. For promising ones:
   - Click the card → reveal contact info.
   - Copy the Spotify playlist URL.
   - Note the contact method (IG, email, form, etc.).
4. Fill in columns G, H, I, J, K, L in this sheet.
5. When you have a good batch with real contacts, import them into DKPlaylister using the rich flags:

```bash
dkplaylister add "https://open.spotify.com/playlist/XXXX" \
  --source playlister \
  --query "Indie Folk" \
  --curator-instagram "handle" \
  --contact-via playlister_popup
```

### Tips

- You do **not** need to process all 180 entries. Focus on the top 30–50.
- The Priority Score already tries to favor mid-sized playlists with submission-friendly language.
- Keep this file in your project (or Google Drive) so you can come back to it later.
- When you're ready, we can add a feature that reads a filled version of this CSV and bulk-imports the good rows directly into DKPlaylister.

---

**Next step ideas (let me know if you want any of these):**
- A second CSV with only the top 40 highest priority rows (smaller daily worklist)
- A script that reads this CSV and generates ready-to-run `dkplaylister add` commands for rows where Status = "Revealed - Has Contact"
- Integration directly into the Streamlit UI ("Import from Playlister CSV")

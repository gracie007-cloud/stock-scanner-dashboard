# Quick Start Guide

Get the CANSLIM Scanner Dashboard running in 5 minutes!

## Prerequisites

- Python 3.9 or higher
- Google account with Sheets API access
- `gog` CLI installed ([installation guide](https://github.com/yourusername/gog))

## Step 1: Clone & Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/canslim-scanner-dashboard.git
cd canslim-scanner-dashboard

# Copy environment template
cp .env.example .env
```

## Step 2: Google Sheets Configuration

### Create Service Account
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select a project
3. Enable "Google Sheets API"
4. Create a service account
5. Download the JSON key
6. Note the service account email (looks like: `xxx@xxx.iam.gserviceaccount.com`)

### Setup gog
```bash
# Authenticate gog with your service account
gog auth add your-service-account@your-project.iam.gserviceaccount.com \
  --key-file ~/Downloads/your-key-file.json

# Verify
gog auth list
```

### Prepare Your Sheet
1. Create a Google Sheet
2. Share it with your service account email (Viewer access)
3. Copy the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
   ```

## Step 3: Configure Environment

Edit `.env`:
```bash
GOOGLE_SHEET_ID=your_actual_sheet_id_here
GOG_ACCOUNT=your-service-account@your-project.iam.gserviceaccount.com
```

## Step 4: Launch!

```bash
./run.sh
```

The script will:
- Create a Python virtual environment
- Install Flask dependencies
- Create data directories
- Start the web server

## Step 5: Open Dashboard

Navigate to:
```
http://localhost:5561
```

## Troubleshooting

### "Failed to fetch data"

Test manually:
```bash
gog sheets get YOUR_SHEET_ID 'Main'!A1:W50 --json
```

If this fails:
- ✅ Check the Sheet ID is correct
- ✅ Verify the sheet is shared with your service account
- ✅ Ensure `gog` is authenticated: `gog auth list`

### Port already in use

Change the port in `.env`:
```env
PORT=5562
```

### Python version issues

Check your version:
```bash
python3 --version
```

Must be 3.9 or higher.

## Next Steps

### Populate Your Sheet

The dashboard expects this structure:

**Row 1**: Header with timestamp
```
CANSLIM Scanner | Last Scan: | 2024-02-11 08:45:23
```

**Row 2**: Market regime
```
Confirmed | | 2 | | TRUE
```

**Row 3**: Account info
```
$100,000 | | $1,000 | | 12
```

**Row 5**: Column headers
```
Ticker | Name | Score | C | A | N | S | L | I | M | ...
```

**Rows 6+**: Stock data

See [README.md](README.md) for full format details.

### Configure Settings

Click ⚙️ Settings in the dashboard to set:
- Account equity
- Risk percentage
- Max positions

### Explore Features

- **Dashboard**: Main view with all stocks
- **Calendar**: Track daily routines
- **Calls**: Log covered call trades
- **Alerts**: Set price alerts

## Getting Help

- 📖 [Full Documentation](README.md)
- 🔧 [Detailed Setup Guide](SETUP.md)
- 🐛 [Report Issues](https://github.com/yourusername/canslim-scanner-dashboard/issues)
- 💬 [Discussions](https://github.com/yourusername/canslim-scanner-dashboard/discussions)

## Tips

### Run in Background

```bash
# Using screen (Linux/macOS)
screen -S canslim
./run.sh
# Press Ctrl+A then D to detach
# Reconnect: screen -r canslim

# Using tmux
tmux new -s canslim
./run.sh
# Press Ctrl+B then D to detach
# Reconnect: tmux attach -t canslim
```

### Auto-start on Boot

Add to crontab:
```bash
@reboot cd /path/to/canslim-scanner-dashboard && ./run.sh
```

### Access from Other Devices

Edit `app.py` line where Flask runs:
```python
# Change from:
app.run(host='0.0.0.0', port=port, debug=False)

# To bind to specific IP or keep as-is for LAN access
```

Then access via: `http://YOUR_COMPUTER_IP:5561`

---

**🎉 You're all set!** 

Happy trading! Remember: This is a tool for research. Always do your own due diligence.

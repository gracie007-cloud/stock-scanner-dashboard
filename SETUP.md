# Detailed Setup Guide

This guide walks you through setting up the CANSLIM Scanner Dashboard from scratch.

## Prerequisites

### 1. Install Python 3.9+

**macOS:**
```bash
brew install python3
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/)

### 2. Install gog CLI

The `gog` CLI tool is required to read data from Google Sheets.

```bash
# Installation instructions for gog
# Replace with actual installation command when gog is published
```

### 3. Set Up Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

### 4. Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Give it a name (e.g., "canslim-scanner")
4. Click "Create and Continue"
5. Skip the optional permissions
6. Click "Done"
7. Click on the newly created service account
8. Go to the "Keys" tab
9. Click "Add Key" > "Create new key"
10. Choose JSON format
11. Save the downloaded JSON file securely

**Note the service account email** - it looks like:
```
your-service-account@your-project.iam.gserviceaccount.com
```

### 5. Configure gog with Service Account

```bash
# Authenticate gog with your service account
gog auth add your-service-account@your-project.iam.gserviceaccount.com --key-file path/to/downloaded-key.json

# Verify authentication
gog auth list
```

## Dashboard Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/canslim-scanner-dashboard.git
cd canslim-scanner-dashboard
```

### 2. Create Google Sheet

1. Create a new Google Sheet
2. Structure it according to the format in README.md
3. Get the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit
   ```
4. Share the sheet with your service account email (Viewer access is sufficient)

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your favorite editor
nano .env  # or vim, code, etc.
```

Fill in the required values:
```env
GOOGLE_SHEET_ID=your_actual_sheet_id
GOG_ACCOUNT=your-service-account@your-project.iam.gserviceaccount.com
```

### 4. First Run

```bash
# Make run script executable
chmod +x run.sh

# Launch the dashboard
./run.sh
```

The script will:
- Create a Python virtual environment
- Install dependencies
- Create data directories
- Start the Flask server

### 5. Verify Setup

Open your browser to:
```
http://localhost:5561
```

You should see the dashboard. If you see "Failed to fetch data", check:

1. **Google Sheet is shared with service account**
   - Open your sheet
   - Click "Share"
   - Add the service account email
   - Set permissions to "Viewer"

2. **gog is authenticated**
   ```bash
   gog auth list
   # Should show your service account
   ```

3. **Test gog manually**
   ```bash
   gog sheets get YOUR_SHEET_ID 'Main'!A1:W50 --json
   ```

## Integrating with a Scanner

The dashboard expects data in a specific Google Sheets format. Here's how to integrate your own scanner:

### Option 1: Python Scanner with gog

```python
import subprocess
import json

# Your scanner results
scan_results = {
    'timestamp': '2024-02-11 08:45:23',
    'market_regime': 'Confirmed',
    'distribution_days': 2,
    'buy_signal': True,
    'stocks': [
        {'ticker': 'AAPL', 'score': 85, 'c': 'A', 'a': 'A', ...},
        {'ticker': 'MSFT', 'score': 82, 'c': 'B', 'a': 'A', ...},
    ]
}

# Format as sheet rows
rows = format_for_sheets(scan_results)  # Your formatting function

# Write to sheet using gog
cmd = [
    'gog', 'sheets', 'update',
    'YOUR_SHEET_ID',
    "'Main'!A1:W50",
    '--values', json.dumps(rows)
]

subprocess.run(cmd, env={'GOG_ACCOUNT': 'your-service-account@...'})
```

### Option 2: Any Language via gog CLI

The `gog` CLI can be called from any programming language:

```javascript
// Node.js example
const { exec } = require('child_process');

const sheetId = 'YOUR_SHEET_ID';
const values = JSON.stringify([
  ['CANSLIM Scanner', 'Last Scan:', '2024-02-11 08:45:23'],
  ['Confirmed', '', '2', '', 'TRUE'],
  // ... more rows
]);

exec(`gog sheets update ${sheetId} 'Main'!A1:W50 --values '${values}'`, 
  { env: { GOG_ACCOUNT: 'your-service-account@...' } },
  (error, stdout, stderr) => {
    if (error) console.error(error);
    else console.log('Sheet updated');
  }
);
```

### Option 3: Manual Entry (Testing)

For testing, you can manually populate the Google Sheet:

1. Follow the structure in README.md
2. Add sample stock data
3. The dashboard will pick it up automatically

## Troubleshooting

### "gog: command not found"

Install gog CLI or add it to your PATH:
```bash
export PATH=$PATH:/path/to/gog
```

### Permission Denied Errors

Ensure run.sh is executable:
```bash
chmod +x run.sh
```

### Port Already in Use

Change the port in `.env`:
```env
PORT=5562
```

### Data Not Refreshing

- Force refresh with the 🔄 button
- Check cache duration: `CACHE_DURATION=60` in .env for 1-minute cache
- Verify sheet timestamp is recent

### Import Errors

Ensure you're in the virtual environment:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Next Steps

- Set up a cron job to run your scanner periodically
- Customize the dashboard styling in `templates/index.html`
- Add your own scoring factors to the display
- Configure price alerts for your watchlist

## Getting Help

- Check the main [README.md](README.md)
- Review the code comments in `app.py`
- Open an issue on GitHub with:
  - Your OS and Python version
  - Full error messages
  - Steps to reproduce the problem

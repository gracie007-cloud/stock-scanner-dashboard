# CANSLIM Scanner Dashboard

A real-time web dashboard for viewing and analyzing stock scans based on CANSLIM methodology. Scores stocks across 15+ technical and fundamental factors including C.A.N.S.L.I.M. criteria, institutional sponsorship, market regime awareness, and more.

![CANSLIM Dashboard](docs/screenshot-placeholder.png)

## Features

### 📊 Core Functionality
- **Real-time Stock Scanning**: Displays stocks scored on 15+ CANSLIM factors
- **Market Regime Tracking**: Shows current market state (Confirmed, Rally Attempt, Under Pressure, Correction)
- **Position Sizing Calculator**: Automatically calculates shares and cost based on your risk parameters
- **Historical Snapshots**: Saves scan results over time for comparison and backtesting
- **CSV Export**: Export filtered results for further analysis

### 📈 Trading Tools
- **Price Alerts**: Set alerts for when stocks hit target prices
- **Earnings Calendar**: Track upcoming earnings dates
- **Daily Routine Tracker**: Pre-market and post-close trading checklists
- **Trade Journal**: Log covered calls and stock positions with P&L tracking
- **Risk Management**: Configure account size, risk per trade, and max positions

### 🎨 Dashboard Features
- **Live Filtering**: Search and filter stocks in real-time
- **Sort by Column**: Click any column header to sort
- **Color-Coded Signals**: Visual indicators for buy/sell signals, RS ratings, and more
- **Dark Mode UI**: Easy-on-the-eyes interface for extended screen time
- **Auto-Refresh**: Configurable cache with manual refresh option

## Tech Stack

- **Backend**: Python 3.9+ with Flask
- **Frontend**: Vanilla JavaScript (no frameworks!)
- **Data Source**: Google Sheets via `gog` CLI
- **Storage**: JSON file-based persistence

## Prerequisites

1. **Python 3.9+**
2. **Google Sheets API access** via service account
3. **gog CLI tool** - [Install gog](https://github.com/yourusername/gog) for Google Sheets integration
4. A scanner that outputs data to Google Sheets in the expected format

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/canslim-scanner-dashboard.git
cd canslim-scanner-dashboard
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```env
# Required: Your Google Sheet ID (from the sheet URL)
GOOGLE_SHEET_ID=your_sheet_id_here

# Required: Your Google service account email
GOG_ACCOUNT=your-service-account@your-project.iam.gserviceaccount.com

# Optional: Sheet range (default: 'Main'!A1:W50)
SHEET_RANGE='Main'!A1:W50

# Optional: Cache duration in seconds (default: 300 = 5 minutes)
CACHE_DURATION=300

# Optional: Port to run on (default: 5561)
PORT=5561
```

### 3. Google Sheets Setup

Your Google Sheet should be structured as follows:

**Row 1**: Title and scan timestamp
```
CANSLIM Scanner | Last Scan: | 2024-02-11 08:45:23
```

**Row 2**: Market regime data
```
Market Regime | | Distribution Days | | Buy Signal
Confirmed     | | 2                 | | TRUE
```

**Row 3**: Account settings
```
Account Balance | | Risk Per Trade | | Actionable Count
$100,000        | | $1,000         | | 12
```

**Row 4**: Empty

**Row 5**: Column headers
```
Ticker | Name | Score | C | A | N | S | L | I | M | RS | Price | Pivot | Stop | Signal | ...
```

**Rows 6+**: Stock data

Share the Google Sheet with your service account email with at least "Viewer" permissions.

### 4. Install Dependencies

```bash
# Using the provided run script (recommended - handles venv automatically)
chmod +x run.sh
./run.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### 5. Access the Dashboard

Open your browser to:
```
http://localhost:5561
```

## Usage

### Main Dashboard

- **Search**: Filter stocks by ticker in the search box
- **Refresh**: Click "🔄 Refresh" to force a data update
- **Export**: Download filtered results as CSV
- **Settings**: Configure account equity, risk %, and max positions

### Trading Tools

Navigate using the top menu:

- **Calendar**: View and log daily trading routines
- **Calls**: Track covered call positions
- **Alerts**: Manage price alerts
- **History**: Browse past scan snapshots

### Configuration

Default settings can be modified via the web UI or by editing `data/settings.json`:

```json
{
  "account_equity": 100000,
  "risk_pct": 0.01,
  "max_positions": 6
}
```

## Project Structure

```
canslim-scanner-dashboard/
├── app.py                 # Main Flask application
├── templates/             # HTML templates
│   ├── index.html        # Main dashboard
│   ├── calendar.html     # Trading calendar
│   ├── calls.html        # Covered calls tracker
│   ├── routine.html      # Daily routine viewer
│   └── routine_form.html # Routine form
├── data/                  # Data storage (auto-created)
│   ├── settings.json     # App settings
│   ├── alerts.json       # Price alerts
│   ├── earnings.json     # Earnings calendar
│   ├── covered_calls.json # Covered call trades
│   ├── positions.json    # Stock positions
│   ├── history/          # Historical scan snapshots
│   └── routines/         # Daily trading routines
├── requirements.txt       # Python dependencies
├── run.sh                # Launch script
├── .env                  # Environment config (create from .env.example)
├── .env.example          # Example environment variables
├── .gitignore            # Git ignore rules
├── LICENSE               # MIT License
└── README.md             # This file
```

## How It Works

1. **Data Fetching**: The app uses the `gog` CLI tool to fetch data from Google Sheets
2. **Caching**: Results are cached for 5 minutes (configurable) to reduce API calls
3. **Position Sizing**: Automatically calculates share quantities based on risk parameters
4. **Persistence**: All user data (alerts, positions, settings) stored in JSON files
5. **History**: Each unique scan is automatically saved to the history directory

## Customization

### Scoring Factors

The dashboard displays whatever columns your scanner outputs. Common CANSLIM factors include:

- **C**: Current quarterly earnings
- **A**: Annual earnings growth
- **N**: New highs, new products, new management
- **S**: Supply and demand (shares outstanding, volume)
- **L**: Leader or laggard (RS rating)
- **I**: Institutional sponsorship
- **M**: Market direction

### Add Your Own Features

The codebase is designed to be hackable:

- Add new API endpoints in `app.py`
- Create custom dashboard views in `templates/`
- Modify position sizing logic in the `api_data()` route
- Extend the scanner integration to trigger scans programmatically

## Troubleshooting

### "Failed to fetch data" error

- Verify `GOOGLE_SHEET_ID` is correct in `.env`
- Ensure the Google Sheet is shared with your service account email
- Check that `gog` CLI is installed and authenticated: `gog auth list`
- Test manually: `gog sheets get YOUR_SHEET_ID 'Main'!A1:W50 --json`

### Data not updating

- Check the scan timestamp in the sheet - is it recent?
- Force refresh using the 🔄 button
- Reduce `CACHE_DURATION` in `.env` for more frequent updates
- Verify the scanner is writing to the correct sheet

### Port already in use

Change the port in `.env`:
```env
PORT=5562
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Credits

Built with [OpenClaw](https://openclaw.ai) - AI-powered development assistant.

---

**Disclaimer**: This tool is for educational and research purposes. Always do your own due diligence before making investment decisions. Past performance does not guarantee future results.

#!/usr/bin/env python3
import os
import subprocess
import json
import time
import calendar as cal
import fcntl
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response, redirect, url_for
import io
import csv

app = Flask(__name__)

# Configuration from environment variables
SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')
SHEET_RANGE = os.getenv('SHEET_RANGE', "'Main'!A1:W50")
GOG_ACCOUNT = os.getenv('GOG_ACCOUNT', '')
CACHE_DURATION = int(os.getenv('CACHE_DURATION', '300'))  # 5 minutes default

# File paths - relative to app directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

ALERTS_FILE = os.path.join(DATA_DIR, 'alerts.json')
EARNINGS_FILE = os.path.join(DATA_DIR, 'earnings.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
HISTORY_DIR = os.path.join(DATA_DIR, 'history')
ROUTINES_DIR = os.path.join(DATA_DIR, 'routines')
CALLS_DATA = os.path.join(DATA_DIR, 'covered_calls.json')
POSITIONS_DATA = os.path.join(DATA_DIR, 'positions.json')

os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(ROUTINES_DIR, exist_ok=True)

# Cache storage
cache = {
    'data': None,
    'timestamp': 0,
    'last_scan_time': None  # Track scan_time to avoid duplicate snapshots
}

def fetch_sheet_data():
    """Fetch data from Google Sheets using gog CLI"""
    if not SHEET_ID or not GOG_ACCOUNT:
        print("Error: GOOGLE_SHEET_ID and GOG_ACCOUNT environment variables must be set")
        return None
    
    try:
        env = os.environ.copy()
        env['GOG_ACCOUNT'] = GOG_ACCOUNT
        
        cmd = ['gog', 'sheets', 'get', SHEET_ID, SHEET_RANGE, '--json']
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Error fetching sheet: {result.stderr}")
            return None
        
        data = json.loads(result.stdout)
        return data.get('values', [])
    except Exception as e:
        print(f"Exception fetching sheet: {e}")
        return None

def get_cached_data(force_refresh=False):
    """Get data from cache or fetch if expired"""
    current_time = time.time()
    
    if force_refresh or cache['data'] is None or (current_time - cache['timestamp']) > CACHE_DURATION:
        raw_data = fetch_sheet_data()
        if raw_data:
            cache['data'] = parse_sheet_data(raw_data)
            cache['timestamp'] = current_time
            
            # Save historical snapshot if it's a new scan
            if cache['data'] and cache['data'].get('scan_time') != cache.get('last_scan_time'):
                save_historical_snapshot(cache['data'])
                cache['last_scan_time'] = cache['data'].get('scan_time')
    
    return cache['data']

def save_historical_snapshot(data):
    """Save a snapshot of the current scan to history"""
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
        filename = f"scan_{datetime.now().strftime('%Y-%m-%d_%H%M')}.json"
        filepath = os.path.join(HISTORY_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved historical snapshot: {filename}")
    except Exception as e:
        print(f"Error saving snapshot: {e}")

def load_json_file(filepath, default=None):
    """Load JSON file or return default if not exists"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return default if default is not None else []

def save_json_file(filepath, data):
    """Save data to JSON file using atomic write with file locking"""
    try:
        tmp_path = filepath + '.tmp'
        lock_path = filepath + '.lock'
        with open(lock_path, 'w') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                with open(tmp_path, 'w') as f:
                    json.dump(data, f, indent=2)
                os.rename(tmp_path, filepath)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

def parse_sheet_data(raw_values):
    """Parse raw sheet values into structured data"""
    if not raw_values or len(raw_values) < 5:
        return None
    
    # Row 0: Title and timestamp
    scan_time = raw_values[0][2] if len(raw_values[0]) > 2 else "Unknown"
    
    # Row 1: Market regime
    market_regime = raw_values[1][0] if len(raw_values[1]) > 0 else ""
    dist_days = raw_values[1][2] if len(raw_values[1]) > 2 else ""
    buy_ok = raw_values[1][4] if len(raw_values[1]) > 4 else ""
    
    # Row 2: Account info
    account = raw_values[2][0] if len(raw_values[2]) > 0 else ""
    risk_per_trade = raw_values[2][2] if len(raw_values[2]) > 2 else ""
    actionable = raw_values[2][4] if len(raw_values[2]) > 4 else ""
    
    # Row 4: Headers (skip row 3 which is empty)
    headers = raw_values[4] if len(raw_values) > 4 else []
    
    # Rows 5+: Stock data
    stocks = []
    for i in range(5, len(raw_values)):
        row = raw_values[i]
        if row and len(row) > 1:  # Skip empty rows
            stock = {}
            for j, header in enumerate(headers):
                stock[header] = row[j] if j < len(row) else ""
            stocks.append(stock)
    
    return {
        'scan_time': scan_time,
        'market': {
            'regime': market_regime,
            'dist_days': dist_days,
            'buy_ok': buy_ok
        },
        'account': {
            'balance': account,
            'risk_per_trade': risk_per_trade,
            'actionable': actionable
        },
        'headers': headers,
        'stocks': stocks,
        'cache_time': cache['timestamp']
    }

@app.route('/')
def index():
    """Render the dashboard"""
    return render_template('index.html')

@app.route('/api/data')
def api_data():
    """Return cached sheet data as JSON"""
    data = get_cached_data()
    if data is None:
        return jsonify({'error': 'Failed to fetch data'}), 500
    
    # Calculate Shares and Cost for each stock
    settings = load_json_file(SETTINGS_FILE, {})
    account_equity = settings.get('account_equity', 100000)
    risk_pct = settings.get('risk_pct', 0.01)
    risk_per_trade = account_equity * risk_pct
    
    for stock in data['stocks']:
        try:
            pivot = float(stock.get('Pivot', 0))
            stop = float(stock.get('Stop', 0))
            if pivot > 0 and stop > 0 and pivot > stop:
                risk_per_share = pivot - stop
                shares = int(risk_per_trade / risk_per_share)
                stock['Shares'] = str(shares)
                stock['Cost'] = f"${shares * pivot:,.0f}"
            else:
                stock['Shares'] = ''
                stock['Cost'] = ''
        except (ValueError, ZeroDivisionError):
            stock['Shares'] = ''
            stock['Cost'] = ''
    
    # Add 'Cost' to headers if not already present
    if 'Cost' not in data['headers']:
        # Add after 'Shares' if it exists, otherwise at the end
        if 'Shares' in data['headers']:
            shares_idx = data['headers'].index('Shares')
            data['headers'].insert(shares_idx + 1, 'Cost')
        else:
            data['headers'].append('Cost')
    
    return jsonify(data)

@app.route('/api/refresh')
def api_refresh():
    """Force refresh the data"""
    data = get_cached_data(force_refresh=True)
    if data is None:
        return jsonify({'error': 'Failed to refresh data'}), 500
    return jsonify(data)

@app.route('/api/export')
def api_export():
    """Export filtered data as CSV"""
    data = get_cached_data()
    if data is None:
        return jsonify({'error': 'Failed to fetch data'}), 500
    
    # Get filter parameter if provided
    filter_text = request.args.get('filter', '').lower()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(data['headers'])
    
    # Write stock data
    for stock in data['stocks']:
        # Apply filter if provided
        if filter_text:
            ticker = stock.get('Ticker', '').lower()
            if filter_text not in ticker:
                continue
        
        row = [stock.get(header, '') for header in data['headers']]
        writer.writerow(row)
    
    # Prepare response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=canslim_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

# --- Alert API endpoints ---
@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts"""
    alerts = load_json_file(ALERTS_FILE, [])
    return jsonify(alerts)

@app.route('/api/alerts', methods=['POST'])
def add_alert():
    """Add a new alert"""
    try:
        data = request.json or {}
        
        # Validate ticker
        ticker = data.get('ticker', '').strip().upper()
        if not ticker or len(ticker) > 10 or not ticker.replace('.', '').replace('-', '').isalnum():
            return jsonify({'error': 'Invalid ticker (max 10 alphanumeric chars)'}), 400
        
        # Validate condition
        condition = data.get('condition', 'above')
        if condition not in ['above', 'below']:
            return jsonify({'error': 'Invalid condition (must be above or below)'}), 400
        
        # Validate price
        try:
            price = float(data.get('price', 0))
            if price <= 0 or price > 1000000:
                return jsonify({'error': 'Invalid price (must be positive, max $1M)'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid price (must be a number)'}), 400
        
        alerts = load_json_file(ALERTS_FILE, [])
        
        new_alert = {
            'ticker': ticker,
            'condition': condition,
            'price': price,
            'created': datetime.utcnow().isoformat(),
            'triggered': False
        }
        
        alerts.append(new_alert)
        
        if save_json_file(ALERTS_FILE, alerts):
            return jsonify(new_alert), 201
        else:
            return jsonify({'error': 'Failed to save alert'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/<int:index>', methods=['DELETE'])
def delete_alert(index):
    """Delete an alert by index"""
    try:
        alerts = load_json_file(ALERTS_FILE, [])
        
        if index < 0 or index >= len(alerts):
            return jsonify({'error': 'Invalid index'}), 404
        
        deleted = alerts.pop(index)
        
        if save_json_file(ALERTS_FILE, alerts):
            return jsonify({'deleted': deleted}), 200
        else:
            return jsonify({'error': 'Failed to delete alert'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Earnings API endpoints ---
@app.route('/api/earnings', methods=['GET'])
def get_earnings():
    """Get all earnings dates"""
    earnings = load_json_file(EARNINGS_FILE, {})
    return jsonify(earnings)

@app.route('/api/earnings', methods=['POST'])
def set_earnings():
    """Set earnings date for a ticker"""
    try:
        data = request.json
        ticker = data.get('ticker', '').upper()
        date = data.get('date', '')
        
        if not ticker or not date:
            return jsonify({'error': 'Invalid ticker or date'}), 400
        
        earnings = load_json_file(EARNINGS_FILE, {})
        earnings[ticker] = date
        
        if save_json_file(EARNINGS_FILE, earnings):
            return jsonify({'ticker': ticker, 'date': date}), 200
        else:
            return jsonify({'error': 'Failed to save earnings date'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- History API endpoints ---
@app.route('/api/history', methods=['GET'])
def get_history():
    """List all historical snapshots"""
    try:
        if not os.path.exists(HISTORY_DIR):
            return jsonify([])
        
        files = []
        for filename in sorted(os.listdir(HISTORY_DIR), reverse=True):
            if filename.endswith('.json'):
                filepath = os.path.join(HISTORY_DIR, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    files.append({
                        'filename': filename,
                        'scan_time': data.get('scan_time', 'Unknown'),
                        'stock_count': len(data.get('stocks', []))
                    })
        
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/<filename>', methods=['GET'])
def get_historical_snapshot(filename):
    """Get a specific historical snapshot"""
    try:
        filepath = os.path.join(HISTORY_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Snapshot not found'}), 404
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Settings API endpoints ---
DEFAULT_SETTINGS = {
    'account_equity': 100000,
    'risk_pct': 0.01,
    'max_positions': 6
}

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get scanner settings"""
    settings = load_json_file(SETTINGS_FILE, DEFAULT_SETTINGS)
    # Merge with defaults for any missing keys
    for k, v in DEFAULT_SETTINGS.items():
        if k not in settings:
            settings[k] = v
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update scanner settings"""
    try:
        data = request.json
        settings = load_json_file(SETTINGS_FILE, DEFAULT_SETTINGS)
        
        if 'account_equity' in data:
            settings['account_equity'] = float(data['account_equity'])
        if 'risk_pct' in data:
            settings['risk_pct'] = float(data['risk_pct'])
        if 'max_positions' in data:
            settings['max_positions'] = int(data['max_positions'])
        
        if save_json_file(SETTINGS_FILE, settings):
            return jsonify(settings), 200
        else:
            return jsonify({'error': 'Failed to save settings'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


## ── Daily Trading Routine ────────────────────────────────

def load_routine(date_str):
    path = os.path.join(ROUTINES_DIR, f'{date_str}.json')
    if os.path.exists(path):
        return json.loads(open(path).read())
    return {'date': date_str}


def save_routine(date_str, data):
    data['date'] = date_str
    data['updated_at'] = datetime.now().isoformat()
    path = os.path.join(ROUTINES_DIR, f'{date_str}.json')
    tmp_path = path + '.tmp'
    lock_path = path + '.lock'
    with open(lock_path, 'w') as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            with open(tmp_path, 'w') as f:
                json.dump(data, f, indent=2)
            os.rename(tmp_path, path)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def get_all_routine_dates():
    """Get set of dates that have routine files."""
    dates = {}
    for f in os.listdir(ROUTINES_DIR):
        if f.endswith('.json'):
            ds = f[:-5]
            try:
                data = json.loads(open(os.path.join(ROUTINES_DIR, f)).read())
                dates[ds] = {
                    'has_premarket': bool(data.get('premarket')),
                    'has_postclose': bool(data.get('postclose')),
                }
            except:
                pass
    return dates


@app.route('/routine')
def routine_today():
    today = datetime.now().strftime('%Y-%m-%d')
    return redirect(url_for('routine_view', date_str=today))


@app.route('/routine/<date_str>')
def routine_view(date_str):
    data = load_routine(date_str)
    return render_template('routine.html', date_str=date_str, data=data)


@app.route('/routine/<date_str>/<routine_type>', methods=['GET', 'POST'])
def routine_form(date_str, routine_type):
    if routine_type not in ('premarket', 'postclose'):
        return 'Invalid type', 404
    data = load_routine(date_str)
    if request.method == 'POST':
        fields = {}
        for key in request.form:
            if key.startswith('routine_'):
                fields[key[8:]] = request.form[key]
        data[routine_type] = fields
        save_routine(date_str, data)
        return redirect(url_for('routine_view', date_str=date_str))
    existing = data.get(routine_type, {})
    return render_template('routine_form.html', date_str=date_str,
                         routine_type=routine_type, data=existing)


@app.route('/calendar')
@app.route('/calendar/<int:year>/<int:month>')
def calendar_view(year=None, month=None):
    today = datetime.now()
    if year is None: year = today.year
    if month is None: month = today.month
    weeks = cal.monthcalendar(year, month)
    num_days = cal.monthrange(year, month)[1]
    all_dates = get_all_routine_dates()
    days_data = {}
    for day in range(1, num_days + 1):
        ds = f'{year}-{month:02d}-{day:02d}'
        if ds in all_dates:
            days_data[day] = all_dates[ds]
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    return render_template('calendar.html', year=year, month=month,
                         month_name=cal.month_name[month], weeks=weeks,
                         days_data=days_data, prev_year=prev_year,
                         prev_month=prev_month, next_year=next_year,
                         next_month=next_month,
                         today_str=today.strftime('%Y-%m-%d'))


@app.route('/api/routine/<date_str>', methods=['GET'])
def api_routine_get(date_str):
    return jsonify(load_routine(date_str))


@app.route('/api/routine/<date_str>', methods=['POST'])
def api_routine_save(date_str):
    req = request.json
    data = load_routine(date_str)
    rtype = req.get('type', 'premarket')
    if rtype in ('premarket', 'postclose'):
        data[rtype] = req.get('data', {})
    save_routine(date_str, data)
    return jsonify({'ok': True})


## ── Trade Tracker: Covered Calls ─────────────────────────

def load_calls():
    return load_json_file(CALLS_DATA, [])


def save_calls(trades):
    save_json_file(CALLS_DATA, trades)


@app.route('/calls')
def calls_page():
    return render_template('calls.html')


@app.route('/api/calls', methods=['GET'])
def api_calls_get():
    trades = load_calls()
    return jsonify({'trades': trades, 'summary': _calls_summary(trades)})


@app.route('/api/calls', methods=['POST'])
def api_calls_add():
    try:
        data = request.json or {}
        trades = load_calls()
        
        # Validate ticker
        ticker = data.get('ticker', 'SPY').strip().upper()
        if not ticker or len(ticker) > 10 or not ticker.replace('.', '').replace('-', '').isalnum():
            return jsonify({'error': 'Invalid ticker (max 10 alphanumeric chars)'}), 400
        
        # Validate contracts
        try:
            contracts = int(data.get('contracts', 1))
            if contracts <= 0 or contracts > 10000:
                return jsonify({'error': 'Invalid contracts (must be 1-10,000)'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid contracts (must be an integer)'}), 400
        
        # Validate premium_per_contract
        try:
            premium_per = float(data.get('premium_per_contract', 0))
            if premium_per < 0 or premium_per > 10000:
                return jsonify({'error': 'Invalid premium (must be 0-$10,000)'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid premium (must be a number)'}), 400
        
        # Validate strike
        try:
            strike = float(data.get('strike', 0))
            if strike <= 0 or strike > 100000:
                return jsonify({'error': 'Invalid strike (must be positive, max $100k)'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid strike (must be a number)'}), 400
        
        trade = {
            'id': (max((t.get('id', 0) for t in trades), default=0) + 1),
            'ticker': ticker,
            'sell_date': data.get('sell_date', datetime.now().strftime('%Y-%m-%d')),
            'expiry': data.get('expiry', ''),
            'strike': strike,
            'contracts': contracts,
            'premium_per_contract': premium_per,
            'premium_total': round(premium_per * contracts * 100, 2),
            'delta': data.get('delta', 0.10),
            'stock_price_at_sell': data.get('stock_price', 0),
            'status': 'open',
            'close_date': None,
            'close_price': None,
            'pnl': None,
            'notes': data.get('notes', ''),
            'created_at': datetime.now().isoformat(),
        }
        trades.append(trade)
        save_calls(trades)
        return jsonify({'ok': True, 'trade': trade}), 201
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/calls/<int:trade_id>', methods=['PATCH'])
def api_calls_close(trade_id):
    data = request.json
    trades = load_calls()
    for t in trades:
        if t.get('id') == trade_id:
            status = data.get('status', 'expired')
            t['status'] = status
            t['close_date'] = data.get('close_date', datetime.now().strftime('%Y-%m-%d'))
            if status == 'expired':
                t['pnl'] = t['premium_total']
            elif status == 'called_away':
                price_at_sell = t.get('stock_price_at_sell', 0)
                appreciation = (t['strike'] - price_at_sell) * t['contracts'] * 100
                t['pnl'] = round(t['premium_total'] + appreciation, 2)
            else:
                buyback = data.get('buyback_price', 0) * t['contracts'] * 100
                t['pnl'] = round(t['premium_total'] - buyback, 2)
                t['close_price'] = data.get('buyback_price', 0)
            t['notes'] = data.get('notes', t.get('notes', ''))
            break
    save_calls(trades)
    return jsonify({'ok': True})


@app.route('/api/calls/<int:trade_id>', methods=['DELETE'])
def api_calls_delete(trade_id):
    trades = load_calls()
    trades = [t for t in trades if t.get('id') != trade_id]
    save_calls(trades)
    return jsonify({'ok': True})


def _calls_summary(trades):
    def _summarize(subset, capital=100000):
        if not subset:
            return {'total_premium': 0, 'total_pnl': 0, 'total_trades': 0,
                    'expired': 0, 'called_away': 0, 'open': 0,
                    'weekly_avg': 0, 'annualized_yield': 0}
        total_premium = sum(t.get('premium_total', 0) for t in subset)
        closed = [t for t in subset if t.get('status') != 'open']
        total_pnl = sum(t.get('pnl', t.get('premium_total', 0)) for t in closed)
        open_t = [t for t in subset if t.get('status') == 'open']
        expired = [t for t in subset if t.get('status') == 'expired']
        called = [t for t in subset if t.get('status') == 'called_away']
        if subset:
            dates = sorted(set(t.get('sell_date', '')[:7] for t in subset if t.get('sell_date')))
            months = max(len(dates), 1)
            annualized = (total_premium / months) * 12 / max(capital, 1) * 100
        else:
            annualized = 0
        return {
            'total_premium': total_premium,
            'total_pnl': total_pnl,
            'total_trades': len(subset),
            'expired': len(expired),
            'called_away': len(called),
            'open': len(open_t),
            'weekly_avg': total_premium / max(len(subset), 1),
            'annualized_yield': annualized,
        }

    # Overall summary
    overall = _summarize(trades)

    # Per-ticker summaries
    tickers = sorted(set(t.get('ticker', 'SPY') for t in trades)) if trades else []
    by_ticker = {}
    for tk in tickers:
        subset = [t for t in trades if t.get('ticker', 'SPY') == tk]
        by_ticker[tk] = _summarize(subset, 100000)

    overall['tickers'] = tickers
    overall['by_ticker'] = by_ticker
    return overall


@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "app": "canslim-dashboard"})


## ── Trade Tracker: Stock Positions ───────────────────────

def load_positions():
    return load_json_file(POSITIONS_DATA, [])


def save_positions(positions):
    save_json_file(POSITIONS_DATA, positions)


@app.route('/api/positions', methods=['GET'])
def api_positions_get():
    positions = load_positions()
    return jsonify({'positions': positions, 'summary': _positions_summary(positions)})


@app.route('/api/quotes', methods=['GET'])
def api_quotes():
    """Get current prices for a list of tickers (requires external API setup)"""
    tickers = request.args.get('tickers', '')
    if not tickers:
        return jsonify({})
    
    # Note: You'll need to configure your own market data API
    # This is a placeholder that returns empty data
    return jsonify({'error': 'Market data API not configured'}), 501


@app.route('/api/positions', methods=['POST'])
def api_positions_add():
    try:
        data = request.json or {}
        positions = load_positions()
        
        # Validate ticker
        ticker = data.get('ticker', '').strip().upper()
        if not ticker or len(ticker) > 10 or not ticker.replace('.', '').replace('-', '').isalnum():
            return jsonify({'error': 'Invalid ticker (max 10 alphanumeric chars)'}), 400
        
        # Validate shares
        try:
            shares = int(data.get('shares', 0))
            if shares <= 0 or shares > 1000000:
                return jsonify({'error': 'Invalid shares (must be 1-1,000,000)'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid shares (must be an integer)'}), 400
        
        # Validate entry_price
        try:
            entry_price = float(data.get('entry_price', 0))
            if entry_price <= 0 or entry_price > 100000:
                return jsonify({'error': 'Invalid entry price (must be positive, max $100k)'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid entry price (must be a number)'}), 400
        
        # Validate optional prices
        stop_price = float(data.get('stop_price', 0)) if data.get('stop_price') else 0
        target_price = float(data.get('target_price', 0)) if data.get('target_price') else 0
        
        # Validate trade_type
        trade_type = data.get('trade_type', 'long')
        if trade_type not in ['long', 'short']:
            return jsonify({'error': 'Invalid trade_type (must be long or short)'}), 400
        
        position = {
            'id': (max((p.get('id', 0) for p in positions), default=0) + 1),
            'ticker': ticker,
            'account': data.get('account', 'default'),
            'trade_type': trade_type,
            'entry_date': data.get('entry_date', datetime.now().strftime('%Y-%m-%d')),
            'entry_price': entry_price,
            'shares': shares,
            'cost_basis': round(shares * entry_price, 2),
            'stop_price': stop_price,
            'target_price': target_price,
            'setup_type': data.get('setup_type', ''),
            'status': 'open',
            'close_date': None,
            'close_price': None,
            'pnl': None,
            'notes': data.get('notes', ''),
            'created_at': datetime.now().isoformat(),
        }
        positions.append(position)
        save_positions(positions)
        return jsonify({'ok': True, 'position': position}), 201
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/positions/<int:position_id>', methods=['PATCH'])
def api_positions_update(position_id):
    data = request.json
    positions = load_positions()
    
    for p in positions:
        if p.get('id') == position_id:
            # Update stop price if provided
            if 'stop_price' in data:
                p['stop_price'] = data['stop_price']
            
            # Close position if close_price provided
            if 'close_price' in data:
                p['status'] = 'closed'
                p['close_price'] = data['close_price']
                p['close_date'] = data.get('close_date', datetime.now().strftime('%Y-%m-%d'))
                
                # Calculate P&L
                if p['trade_type'] == 'long':
                    p['pnl'] = round((p['close_price'] - p['entry_price']) * p['shares'], 2)
                else:  # short
                    p['pnl'] = round((p['entry_price'] - p['close_price']) * p['shares'], 2)
            
            # Update notes if provided
            if 'notes' in data:
                p['notes'] = data['notes']
            
            break
    
    save_positions(positions)
    return jsonify({'ok': True})


@app.route('/api/positions/<int:position_id>', methods=['DELETE'])
def api_positions_delete(position_id):
    positions = load_positions()
    positions = [p for p in positions if p.get('id') != position_id]
    save_positions(positions)
    return jsonify({'ok': True})


def _positions_summary(positions):
    """Calculate summary statistics for stock positions"""
    def _summarize(subset):
        if not subset:
            return {
                'total_capital': 0,
                'total_pnl': 0,
                'open_count': 0,
                'closed_count': 0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0,
                'avg_r_multiple': 0,
            }
        
        open_positions = [p for p in subset if p['status'] == 'open']
        closed_positions = [p for p in subset if p['status'] == 'closed']
        
        total_capital = sum(p['cost_basis'] for p in open_positions)
        total_pnl = sum(p.get('pnl', 0) for p in closed_positions)
        
        wins = [p for p in closed_positions if p.get('pnl', 0) > 0]
        losses = [p for p in closed_positions if p.get('pnl', 0) <= 0]
        
        win_rate = (len(wins) / len(closed_positions) * 100) if closed_positions else 0
        
        # Calculate average R-multiple for closed trades
        r_multiples = []
        for p in closed_positions:
            risk = abs(p['entry_price'] - p.get('stop_price', p['entry_price']))
            if risk > 0:
                pnl_per_share = (p['close_price'] - p['entry_price']) if p['trade_type'] == 'long' else (p['entry_price'] - p['close_price'])
                r_multiple = pnl_per_share / risk
                r_multiples.append(r_multiple)
        
        avg_r = (sum(r_multiples) / len(r_multiples)) if r_multiples else 0
        
        return {
            'total_capital': total_capital,
            'total_pnl': total_pnl,
            'open_count': len(open_positions),
            'closed_count': len(closed_positions),
            'win_count': len(wins),
            'loss_count': len(losses),
            'win_rate': win_rate,
            'avg_r_multiple': avg_r,
        }
    
    # Overall summary
    overall = _summarize(positions)
    
    # By account breakdown
    accounts = sorted(set(p.get('account', 'default') for p in positions)) if positions else []
    by_account = {}
    for acc in accounts:
        subset = [p for p in positions if p.get('account', 'default') == acc]
        by_account[acc] = _summarize(subset)
    
    overall['accounts'] = accounts
    overall['by_account'] = by_account
    
    return overall


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5561'))
    app.run(host='0.0.0.0', port=port, debug=False)

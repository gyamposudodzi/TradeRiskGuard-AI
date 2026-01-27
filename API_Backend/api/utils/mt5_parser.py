import pandas as pd
from bs4 import BeautifulSoup
import io
import re
from datetime import datetime

def _clean_number(text):
    """Clean currency string to float"""
    if not text:
        return 0.0
        
    # Handle brackets for negative numbers often used in finance: (50.00) -> -50.00
    if '(' in text and ')' in text:
        text = '-' + text.replace('(', '').replace(')', '')
        
    # Remove currency symbols ($ € £), spaces, and thousand separators
    # Keep digits, dot, minus
    clean = re.sub(r'[^\d\.\-]', '', text)
    try:
        return float(clean)
    except:
        return 0.0

def _clean_date(text):
    """Clean and standardize date strings"""
    if not text:
        return None
    # Replace dots with dashes (2025.11.01 -> 2025-11-01)
    return text.replace('.', '-')

def parse_mt5_html(content_bytes: bytes) -> pd.DataFrame:
    """
    Robustly parses an MT5 HTML Report.
    Handles duplicate columns (Time, Price) for Entry/Exit.
    """
    print("DEBUG: Starting MT5 Parse (v2)")
    soup = BeautifulSoup(content_bytes, 'html.parser')
    tables = soup.find_all('table')
    
    target_table = None
    headers = []
    
    # 1. Look for known table signatures
    candidate_tables = []
    
    for idx, table in enumerate(tables):
        rows = table.find_all('tr')
        if not rows: 
            continue
            
        # Check first 50 rows for header candidates (MT5 reports can have long preambles)
        for r_idx, r in enumerate(rows[:50]):
            cells = [c.get_text(strip=True) for c in r.find_all(['th', 'td'])]
            
            # Debug: what are we seeing?
            # print(f"DEBUG: Scanned Row {idx}:{r_idx} -> {cells}")
            
            # Simple signature check
            score = 0
            # Convert to set for O(1) lookup and case insensitivity logic if needed
            cell_set = set(cells)
            
            if "Time" in cell_set or "Open Time" in cell_set: score += 1
            if "Profit" in cell_set: score += 1
            if "Symbol" in cell_set: score += 1
            if "Type" in cell_set: score += 1
            if "Volume" in cell_set or "Size" in cell_set: score += 1
            
            # Also catch "Positions" or "Orders" single headers if we want to be smarter? 
            # No, looking for the column headers is safest.
            
            if score >= 3:
                # Store candidate: (Score, TableIndex, TableObj, HeaderRow, HeaderRowIndex)
                candidate_tables.append((score, idx, table, cells, r_idx))
                
    if not candidate_tables:
        print("DEBUG: No table matched enough MT5 headers.")
        raise ValueError("Could not visually identify an MT5 History table.")
        
    # Pick best table
    candidate_tables.sort(key=lambda x: x[0], reverse=True)
    best_score, best_idx, target_table, header_row, header_row_idx = candidate_tables[0]
    print(f"DEBUG: Found best table (Score {best_score}) with headers: {header_row}")

    # 2. Dynamic Column Mapping (Handling Duplicates)
    col_map = {
        'entry_time': -1,
        'exit_time': -1,
        'symbol': -1,
        'type': -1,
        'volume': -1,
        'profit': -1,
        'entry_price': -1,
        'exit_price': -1
    }
    
    lower_headers = [h.lower() for h in header_row]
    
    # helper to find index (optionally skipping used indices, not needed for unique)
    def find_all_indices(keywords):
        indices = []
        for i, h in enumerate(lower_headers):
            for k in keywords:
                if k in h:
                    indices.append(i)
                    break
        return sorted(list(set(indices)))

    # Map Symbol, Type, Profit (usually unique)
    sym_idxs = find_all_indices(['symbol', 'item'])
    if sym_idxs: col_map['symbol'] = sym_idxs[0]
    
    type_idxs = find_all_indices(['type'])
    if type_idxs: col_map['type'] = type_idxs[0]
    
    profit_idxs = find_all_indices(['profit'])
    if profit_idxs: col_map['profit'] = profit_idxs[-1] # Use last profit if multiple (e.g. swap/profit) - though usually "Profit" is last
    
    vol_idxs = find_all_indices(['volume', 'size', 'quantity'])
    if vol_idxs: col_map['volume'] = vol_idxs[0]
    
    # Map Time (Entry vs Exit)
    time_idxs = find_all_indices(['time', 'date'])
    if len(time_idxs) >= 2:
        col_map['entry_time'] = time_idxs[0]
        col_map['exit_time'] = time_idxs[1] # Second time column is Exit
    elif len(time_idxs) == 1:
        col_map['entry_time'] = time_idxs[0]
        col_map['exit_time'] = time_idxs[0] # Fallback
        
    # Map Price (Entry vs Exit)
    price_idxs = find_all_indices(['price'])
    # Filter out "price" that might be a subheading? Usually "Price" occurs twice.
    if len(price_idxs) >= 2:
        col_map['entry_price'] = price_idxs[0]
        col_map['exit_price'] = price_idxs[1]
    elif len(price_idxs) == 1:
        col_map['entry_price'] = price_idxs[0]
        
    print(f"DEBUG: Column Map: {col_map}")
    
    # 3. Parse Data
    if col_map['profit'] == -1: 
        raise ValueError("Could not find 'Profit' column.")
        
    data = []
    rows = target_table.find_all('tr')
    
    # Start parsing from the row AFTER the header
    data_rows = rows[header_row_idx + 1:]
    
    failure_log = []
    
    for row in data_rows:
        cells = [c.get_text(strip=True) for c in row.find_all('td')]
        
        # Validation checks
        if not cells: continue
        
        try:
            # Check length against max required index
            required_idx = max(col_map.values())
            if len(cells) <= required_idx:
                # Often happens for spacer rows or summaries
                # failure_log.append(f"Row too short: len={len(cells)} required={required_idx}")
                continue

            symbol = cells[col_map['symbol']]
            profit_raw = cells[col_map['profit']]
            trade_type = cells[col_map['type']] if col_map['type'] != -1 else "Unknown"
            
            # Skip invalid rows
            if not symbol or not trade_type: 
                continue
            if trade_type.lower() in ['balance', 'credit', 'total']: 
                continue

            # Parse Numbers
            profit = _clean_number(profit_raw)
            vol = _clean_number(cells[col_map['volume']]) if col_map['volume'] != -1 else 0.0
            entry_px = _clean_number(cells[col_map['entry_price']]) if col_map['entry_price'] != -1 else 0.0
            exit_px = _clean_number(cells[col_map['exit_price']]) if col_map['exit_price'] != -1 else 0.0
            
            # Parse Date
            entry_t_str = _clean_date(cells[col_map['entry_time']]) if col_map['entry_time'] != -1 else ""
            exit_t_str = _clean_date(cells[col_map['exit_time']]) if col_map['exit_time'] != -1 else entry_t_str
            
            entry_time = pd.to_datetime(entry_t_str, errors='coerce')
            exit_time = pd.to_datetime(exit_t_str, errors='coerce')
            
            # If dates failed, fallback
            if pd.isna(entry_time): entry_time = datetime.now()
            if pd.isna(exit_time): exit_time = entry_time
            
            trade = {
                "trade_id": f"mt5_{len(data)+1}",
                "symbol": symbol,
                "trade_type": trade_type,
                "lot_size": vol,
                "profit_loss": profit,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_px,
                "exit_price": exit_px
            }
            
            data.append(trade)
            
        except Exception as e:
            failure_log.append(f"Error parsing row: {str(e)} | Cells: {cells[:5]}...")
            continue

    if not data:
        print("DEBUG: FAILURE LOG (First 5):")
        for log in failure_log[:5]:
            print(log)
        raise ValueError(f"No valid trades found. Parser failed on {len(failure_log)} candidate rows.")
    
    print(f"DEBUG: Success. Extracted {len(data)} trades.")
    return pd.DataFrame(data)

import robin_stocks.robinhood as r
import pandas as pd
import time
import gspread
from typing import List, Dict, Any, Optional, Tuple
import dotenv

GOOGLE_SHEETS_CREDENTIALS_PATH = dotenv.get_key('.env', 'GOOGLE_SHEETS_CREDENTIALS_PATH')   
SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1HEEy30Axok_zWtWiD2N3UMj8Ou9MjFF2ddkirlBg5oo/edit?gid=0#gid=0'
WORKSHEET_NAME = '24 Hour Market Data'

# --- ROBINHOOD CONFIGURATION ---
ROBINHOOD_USERNAME = '' 
ROBINHOOD_PASSWORD = ''
WATCHLIST_NAME = '24 Hour Market'
CHUNK_SIZE = 100 

def format_market_cap(market_cap_str: Optional[str]) -> Tuple[str, str]:
    """
    Converts a raw market cap number string into a formatted tuple: (Value, Unit).
    (e.g., '4440000000000.00' -> ('4.44', 'T')).
    
    Returns a tuple of (Formatted Market Cap Value, Unit String).
    """
    if not market_cap_str:
        return "N/A", ""
    try:
        cap = float(market_cap_str)
        
        # Check for Trillions (10^12)
        if cap >= 1e12:
            value = cap / 1e12
            return f"{value:.2f}", "T"
        # Check for Billions (10^9)
        elif cap >= 1e9:
            value = cap / 1e9
            return f"{value:.2f}", "B"
        # Check for Millions (10^6)
        elif cap >= 1e6:
            value = cap / 1e6
            return f"{value:.2f}", "M"
        else:
            # For smaller caps, return the full value and an empty unit string
            return f"{cap:.2f}", "" 
    except (ValueError, TypeError):
        return "N/A", ""


def fetch_latest_prices(tickers: List[str]) -> Dict[str, str]:
    """
    Fetches the latest real-time price for a list of tickers.
    """
    prices: Dict[str, str] = {}
    if not tickers:
        return prices
        
    try:
        # Get the latest price quotes for all tickers
        latest_prices_list = r.stocks.get_latest_price(tickers)
        
        if latest_prices_list and isinstance(latest_prices_list, list):
            for ticker, price_str in zip(tickers, latest_prices_list):
                try:
                    price = float(price_str)
                    prices[ticker] = f"${price:.2f}"
                except (ValueError, TypeError):
                    prices[ticker] = 'N/A'
        
        print(f"--- Successfully fetched latest prices for {len(prices)} tickers. ---")
    except Exception as e:
        print(f"WARNING: Failed to fetch latest prices: {e}")
        prices = {ticker: 'N/A' for ticker in tickers}
        
    return prices


def upload_to_google_sheets(df: pd.DataFrame):
    """
    Authenticates with Google Sheets and uploads the DataFrame to the target spreadsheet.
    Explicitly uses 'A1' for the start range to ensure headers are included.
    """
    print("--- Attempting to connect to Google Sheets... ---")
    try:
        # Authenticate using the service account JSON file
        gc = gspread.service_account(filename=GOOGLE_SHEETS_CREDENTIALS_PATH)
        
        # Open the sheet by URL (gspread supports URLs directly)
        spreadsheet = gc.open_by_url(SPREADSHEET_URL)
        
        # Check if the target worksheet exists, and create it if it doesn't, or clear it if it does
        try:
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            # Clear existing data but keep any column/row formatting
            worksheet.clear()
            print(f"INFO: Cleared existing worksheet: '{WORKSHEET_NAME}'")
        except gspread.WorksheetNotFound:
            # Add new worksheet based on DataFrame size (+1 for header row)
            worksheet = spreadsheet.add_worksheet(title=WORKSHEET_NAME, rows=df.shape[0] + 1, cols=df.shape[1])
            print(f"INFO: Created new worksheet: '{WORKSHEET_NAME}'")

        # Prepare data: header row followed by all data rows
        header = df.columns.tolist()
        data = df.values.tolist()
        
        # Fix for missing headers: Specify 'A1' range
        worksheet.update([header] + data, 'A1', value_input_option='USER_ENTERED')
        
        print(f"\n✅ Google Sheets SUCCESS! {len(data)} rows uploaded.")
        print(f"Spreadsheet URL: {SPREADSHEET_URL}")

    except Exception as e:
        print(f"❌ ERROR connecting to or uploading to Google Sheets: {e}")
        print("Please ensure your GSheets configuration is correct.")


def export_24hr_market_to_csv_and_sheet():
    """
    Logs into Robinhood, fetches the '24 Hour Market' watchlist, enriches the data
    with fundamental details and real-time prices, and exports the result to Google Sheets.
    """
    
    all_fundamentals = []
    # instrument_map stores ticker details: {'symbol': {'Name': '...'}}
    instrument_map: Dict[str, Dict[str, str]] = {} 
    
    try:
        # 1. Login to Robinhood
        print(f"--- Attempting to log in as {ROBINHOOD_USERNAME} ---")
        login_data = r.login(ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, store_session=True)
        
        if not login_data or 'access_token' not in login_data:
            print("❌ Login failed. The credentials or MFA may be incorrect. Exiting.")
            return

        print(f"--- Successfully logged in. Fetching watchlist: '{WATCHLIST_NAME}' ---")

        # 2. Get the list of instruments
        watchlist_raw_data: Any = r.get_watchlist_by_name(WATCHLIST_NAME)

        list_of_instruments: List[Dict[str, Any]]
        if isinstance(watchlist_raw_data, dict) and 'results' in watchlist_raw_data:
            list_of_instruments = watchlist_raw_data.get('results', [])
        else:
            list_of_instruments = watchlist_raw_data if isinstance(watchlist_raw_data, list) else []

        if not list_of_instruments:
            print(f"❌ ERROR: Watchlist '{WATCHLIST_NAME}' was retrieved but is empty or returned no data.")
            return
        
        # 3. Extract Tickers and map them to their names.
        for i in list_of_instruments:
            if isinstance(i, dict) and i.get('symbol'):
                symbol = i.get('symbol')
                name = i.get('name')
                instrument_map[symbol] = {'Name': name}
        
        unique_tickers = list(instrument_map.keys())
            
        if not unique_tickers:
            print("❌ ERROR: Could not extract any valid ticker symbols from the watchlist data.")
            return
            
        print(f"✅ Retrieved {len(unique_tickers)} unique Ticker Symbols.")
        
        # 4. FETCH THE REAL-TIME PRICES
        latest_prices_map = fetch_latest_prices(unique_tickers)
        
        # 5. Get the Fundamental Data (Market Cap, Sector, Industry) in chunks
        print(f"--- Fetching detailed fundamental data for all tickers in batches of {CHUNK_SIZE}... ---")
        
        ticker_chunks = [unique_tickers[i:i + CHUNK_SIZE] for i in range(0, len(unique_tickers), CHUNK_SIZE)]
        
        for i, chunk in enumerate(ticker_chunks):
            print(f"  > Processing batch {i + 1}/{len(ticker_chunks)} ({len(chunk)} tickers)...")
            time.sleep(0.5) 
            
            chunk_fundamentals = r.stocks.get_fundamentals(chunk) 
            
            if isinstance(chunk_fundamentals, list):
                all_fundamentals.extend(chunk_fundamentals)
            elif isinstance(chunk_fundamentals, dict) and chunk_fundamentals.get('results'):
                 all_fundamentals.extend(chunk_fundamentals.get('results', []))
            
        print(f"--- Finished fetching fundamentals. Total records retrieved: {len(all_fundamentals)} ---")

        # 6. Prepare the final DataFrame with required columns and formatting
        final_data = []
        for fund in all_fundamentals:
            if fund and isinstance(fund, dict):
                ticker = fund.get('symbol', 'N/A')
                
                # Get name and price
                name = instrument_map.get(ticker, {}).get('Name', fund.get('name', 'N/A'))
                price = latest_prices_map.get(ticker, 'N/A') 
                
                # --- MARKET CAP SPLIT ---
                raw_market_cap = fund.get('market_cap')
                formatted_cap_value, formatted_cap_unit = format_market_cap(raw_market_cap)

                # Append data with the two new market cap fields
                final_data.append({
                    'Name': name,
                    'Symbol': ticker,
                    'Price': price,
                    'Marketcap Value': formatted_cap_value,
                    'Marketcap Unit': formatted_cap_unit
                })
                
        # 7. Convert to a DataFrame
        df = pd.DataFrame(final_data)
        
        if not df.empty:
            # Explicitly define the column order for the final output
            df = df[['Name', 'Symbol', 'Price', 'Marketcap Value', 'Marketcap Unit']]
            
            print("\n--- First 5 Rows of Transformed Data ---")
            print(df.head().to_markdown(index=False))
            
            # 8. Upload to Google Sheets
            upload_to_google_sheets(df)
        else:
            print("❌ ERROR: Fundamental data fetching resulted in an empty dataset after merging.")

    except Exception as e:
        print(f"An unexpected error occurred during the process: {e}")
    finally:
        # 9. Logout
        try:
            r.logout()
            print("--- Logged out of Robinhood session. ---")
        except Exception:
            pass


if __name__ == "__main__":
    export_24hr_market_to_csv_and_sheet()
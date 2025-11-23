## 🤖 Robinhood Watchlist to Google Sheets Exporter

This Python script is designed to automate the process of extracting real-time price data and market fundamentals (like Market Cap) for stocks within a specified Robinhood watchlist and automatically uploading the structured data to a Google Sheet.

The script is ideal for maintaining a continuously updated tracker for a specialized list of stocks (e.g., Extended Hours/24-Hour Market stocks).

-----

## ✨ Features

  * **Robinhood Integration:** Securely logs into Robinhood to access your custom watchlists using the `robin-stocks` library.
  * **Data Enrichment:** Fetches both real-time price quotes and fundamental data (Market Cap, Sector, Industry) for each stock.
  * **Safe Batching:** Retrieves fundamental data in chunks (batches of 100) to respect API rate limits and improve reliability.
  * **Google Sheets Automation:** Authenticates using a **Service Account JSON file** and uses `gspread` to create or overwrite a specific worksheet with the latest data, preserving formatting.
  * **Market Cap Formatting:** Custom function to convert large market capitalization numbers into human-readable units (e.g., $4,440,000,000,000.00 becomes `4.44 T`).
  * **Secure Configuration:** All sensitive credentials (API paths, username/password) are loaded securely from a `.env` file.

-----

## ⚙️ Setup and Configuration

### Prerequisites

1.  **Python 3.x**
2.  **Dependencies:** Install the required Python packages:
    ```bash
    pip install robin-stocks pandas gspread python-dotenv
    ```

### Step 1: Create the `.env` File

Create a file named **`.env`** in the root directory of your project and populate it with your Robinhood credentials and the path to your Google Sheets Service Account key.

```env
# --- ROBINHOOD CREDENTIALS ---
# If you use MFA, you must manually log in and acquire a session token 
# or use an MFA library to generate the code.
ROBINHOOD_USERNAME="YOUR_ROBINHOOD_USERNAME"
ROBINHOOD_PASSWORD="YOUR_ROBINHOOD_PASSWORD"

# --- GOOGLE SHEETS CONFIG ---
# IMPORTANT: This must be the actual path to your Service Account JSON file.
GOOGLE_SHEETS_CREDENTIALS_PATH="./path/to/your/service-account-key.json"
```

### Step 2: Configure Google Sheets Service Account

This script requires a **Google Service Account** for headless (non-browser) authentication to Google Sheets.

1.  **Create Service Account:** Follow the Google Cloud documentation to create a new Service Account and download the **JSON key file**.
2.  **Share the Spreadsheet:** Open your target Google Sheet (`SPREADSHEET_URL`) and **Share** it with the email address of the Service Account (the email found within the JSON key file). The Service Account must have **Editor** access.

### Step 3: Configure `main.py` Constants

In the script file (`main.py` or similar), adjust the constants at the top to match your target watchlist and spreadsheet:

```python
# The file path is loaded from .env, but the URL and names are defined here:
SPREADSHEET_URL = 'YOUR_SPREADSHEET_FULL_URL_HERE'
WORKSHEET_NAME = '24 Hour Market Data' # The tab name to create/overwrite
WATCHLIST_NAME = '24 Hour Market' # The name of the watchlist in your Robinhood account
```

-----

## 🏃 Running the Script

Execute the script from your terminal:

```bash
python your_script_name.py
```

The script will log into Robinhood, fetch data in batches, process it, and print a success message along with the URL to the updated Google Sheet upon completion.

-----

## 🔒 Security Note

The script loads sensitive credentials from the `.env` file. **DO NOT** commit the `.env` file to Git. Ensure your `.gitignore` file includes:

```
# .gitignore
.env
*.json
```
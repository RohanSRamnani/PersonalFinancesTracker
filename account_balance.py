import sqlite3
import pandas as pd
from datetime import datetime

def initialize_account_balances(db_path='finance_data.db'):
    """
    Initialize the account balances table if it doesn't exist
    
    Parameters:
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create account_balances table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                balance REAL NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error initializing account balances: {str(e)}")
        return False

def get_account_balances(db_path='finance_data.db'):
    """
    Get all account balances
    
    Parameters:
        db_path (str): Path to the SQLite database
    
    Returns:
        pandas.DataFrame: DataFrame containing account balances
    """
    try:
        # Initialize the table if it doesn't exist
        initialize_account_balances(db_path)
        
        conn = sqlite3.connect(db_path)
        
        query = "SELECT account_name, balance, last_updated FROM account_balances ORDER BY account_name"
        balances_df = pd.read_sql_query(query, conn)
        
        conn.close()
        
        if balances_df.empty:
            # Return empty DataFrame with proper columns
            return pd.DataFrame(columns=['account_name', 'balance', 'last_updated'])
        
        # Convert last_updated to datetime
        balances_df['last_updated'] = pd.to_datetime(balances_df['last_updated'])
        
        return balances_df
    except Exception as e:
        print(f"Error getting account balances: {str(e)}")
        return pd.DataFrame(columns=['account_name', 'balance', 'last_updated'])

def update_account_balance(account_name, balance, db_path='finance_data.db'):
    """
    Update (or create) the balance for a specific account
    
    Parameters:
        account_name (str): Name of the account (e.g., 'Wells Fargo')
        balance (float): Current balance of the account
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Initialize the table if it doesn't exist
        initialize_account_balances(db_path)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if account already exists
        cursor.execute("SELECT COUNT(*) FROM account_balances WHERE account_name = ?", (account_name,))
        account_exists = cursor.fetchone()[0] > 0
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if account_exists:
            # Update existing account
            cursor.execute("""
                UPDATE account_balances 
                SET balance = ?, last_updated = ?
                WHERE account_name = ?
            """, (balance, current_time, account_name))
        else:
            # Create new account
            cursor.execute("""
                INSERT INTO account_balances (account_name, balance, last_updated)
                VALUES (?, ?, ?)
            """, (account_name, balance, current_time))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating account balance: {str(e)}")
        return False

def get_total_balance(db_path='finance_data.db'):
    """
    Get the sum of all account balances
    
    Parameters:
        db_path (str): Path to the SQLite database
    
    Returns:
        float: Total balance across all accounts
    """
    try:
        # Initialize the table if it doesn't exist
        initialize_account_balances(db_path)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(balance) FROM account_balances")
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return total if total is not None else 0.0
    except Exception as e:
        print(f"Error getting total balance: {str(e)}")
        return 0.0

def delete_account(account_name, db_path='finance_data.db'):
    """
    Delete an account from the database
    
    Parameters:
        account_name (str): Name of the account to delete
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM account_balances WHERE account_name = ?", (account_name,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting account: {str(e)}")
        return False
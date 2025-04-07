import pandas as pd
import sqlite3
import os
from datetime import datetime

def check_db_exists(db_path='finance_data.db'):
    """
    Check if the SQLite database exists
    
    Parameters:
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if the database exists, False otherwise
    """
    return os.path.exists(db_path)

def save_to_database(df, db_path='finance_data.db'):
    """
    Save transactions to SQLite database
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        
        # Create transactions table if it doesn't exist
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                description TEXT,
                amount REAL,
                source TEXT,
                category TEXT,
                original_category TEXT
            )
        ''')
        
        # Convert date column to string for SQLite
        df_copy = df.copy()
        
        # If the dataframe has an id column from previous database load, drop it
        if 'id' in df_copy.columns:
            df_copy = df_copy.drop(columns=['id'])
        
        # Write to database
        df_copy.to_sql('transactions', conn, if_exists='append', index=False)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving to database: {str(e)}")
        return False

def load_from_database(db_path='finance_data.db', start_date=None, end_date=None):
    """
    Load transactions from SQLite database with optional date filtering
    
    Parameters:
        db_path (str): Path to the SQLite database
        start_date (str): Optional start date for filtering (YYYY-MM-DD)
        end_date (str): Optional end date for filtering (YYYY-MM-DD)
    
    Returns:
        pandas.DataFrame: DataFrame containing transactions
    """
    if not check_db_exists(db_path):
        return pd.DataFrame()
        
    try:
        conn = sqlite3.connect(db_path)
        
        query = "SELECT * FROM transactions"
        params = []
        
        if start_date:
            query += " WHERE date >= ?"
            params.append(start_date)
            
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
        elif end_date:
            query += " WHERE date <= ?"
            params.append(end_date)
        
        df = pd.read_sql_query(query, conn, params=params)
        
        # Convert date column to datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        conn.close()
        
        return df
    except Exception as e:
        print(f"Error loading from database: {str(e)}")
        return pd.DataFrame()

def delete_transaction(transaction_id, db_path='finance_data.db'):
    """
    Delete a transaction from the database
    
    Parameters:
        transaction_id (int): ID of the transaction to delete
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error deleting transaction: {str(e)}")
        return False

def update_transaction(transaction_id, field, value, db_path='finance_data.db'):
    """
    Update a field in a transaction
    
    Parameters:
        transaction_id (int): ID of the transaction to update
        field (str): Field to update (e.g., 'category', 'description')
        value: New value for the field
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Validate field to prevent SQL injection
        valid_fields = ['date', 'description', 'amount', 'source', 'category', 'original_category']
        if field not in valid_fields:
            raise ValueError(f"Invalid field: {field}")
        
        # Update the transaction
        query = f"UPDATE transactions SET {field} = ? WHERE id = ?"
        cursor.execute(query, (value, transaction_id))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error updating transaction: {str(e)}")
        return False

def get_date_range(db_path='finance_data.db'):
    """
    Get the earliest and latest dates in the database
    
    Parameters:
        db_path (str): Path to the SQLite database
    
    Returns:
        tuple: (min_date, max_date) as datetime objects or (None, None) if no data
    """
    if not check_db_exists(db_path):
        return (None, None)
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get min and max dates
        cursor.execute("SELECT MIN(date), MAX(date) FROM transactions")
        min_date, max_date = cursor.fetchone()
        
        conn.close()
        
        if min_date and max_date:
            return (pd.to_datetime(min_date), pd.to_datetime(max_date))
        return (None, None)
    except Exception as e:
        print(f"Error getting date range: {str(e)}")
        return (None, None)

import pandas as pd
import sqlite3
import os
from datetime import datetime

def initialize_database(db_path='finance_data.db'):
    """
    Initialize the database with all necessary tables
    
    Parameters:
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create transactions table
        cursor.execute('''
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
        
        # Create budget table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                amount REAL,
                month TEXT,  -- Format: YYYY-MM
                created_date DATE
            )
        ''')
        
        # Create categories table for custom categories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                is_income BOOLEAN DEFAULT 0,
                color TEXT
            )
        ''')
        
        # Create account_balances table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                balance REAL NOT NULL,
                last_updated TEXT NOT NULL
            )
        ''')
        
        # Default categories
        default_categories = [
            ('Housing', 'Rent, mortgage, property taxes', 0, '#FF5733'),
            ('Transportation', 'Car payments, gas, public transit', 0, '#33FF57'),
            ('Groceries', 'Food and household supplies', 0, '#3357FF'),
            ('Utilities', 'Electricity, water, gas, internet', 0, '#FF33A8'),
            ('Entertainment', 'Movies, events, subscriptions', 0, '#33FFF5'),
            ('Dining Out', 'Restaurants, cafes, takeout', 0, '#FFF533'),
            ('Healthcare', 'Insurance, medications, doctor visits', 0, '#FF33F5'),
            ('Shopping', 'Clothing, electronics, misc items', 0, '#33FFCA'),
            ('Personal Care', 'Haircuts, gym, etc', 0, '#FF8A33'),
            ('Education', 'Tuition, books, courses', 0, '#33B4FF'),
            ('Savings', 'Deposits to savings accounts', 0, '#6233FF'),
            ('Investments', 'Stock purchases, retirement contributions', 0, '#33FF8F'),
            ('Debt Payments', 'Credit card, loan payments', 0, '#FF3333'),
            ('Income', 'Salary, freelance, investments', 1, '#33FF33'),
            ('Other', 'Miscellaneous expenses', 0, '#AAAAAA')
        ]
        
        # Insert default categories if not exist
        for category in default_categories:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO categories (name, description, is_income, color)
                    VALUES (?, ?, ?, ?)
                ''', category)
            except:
                # If any category fails, continue with others
                pass
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        return False

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
        # Make sure database is initialized
        if not check_db_exists(db_path):
            initialize_database(db_path)
        
        conn = sqlite3.connect(db_path)
        
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
        # Initialize the database if it doesn't exist
        initialize_database(db_path)
        # Return empty DataFrame since there's no data yet
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
        if 'date' in df.columns and not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        
        conn.close()
        
        return df
    except Exception as e:
        print(f"Error loading from database: {str(e)}")
        return pd.DataFrame()

def delete_transaction(transaction_id, db_path='finance_data.db', reindex=True):
    """
    Delete a transaction from the database and optionally reindex remaining transactions
    
    Parameters:
        transaction_id (int): ID of the transaction to delete
        db_path (str): Path to the SQLite database
        reindex (bool): If True, renumber all transaction IDs to ensure sequential order
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not check_db_exists(db_path):
        return False
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Delete the transaction
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        
        # Reindex remaining transactions if requested
        if reindex:
            # Get all transactions in order
            cursor.execute("SELECT id FROM transactions ORDER BY id")
            rows = cursor.fetchall()
            
            # Create a temporary table to store transactions
            cursor.execute("""
                CREATE TEMPORARY TABLE temp_transactions AS 
                SELECT * FROM transactions ORDER BY id
            """)
            
            # Delete all from main table
            cursor.execute("DELETE FROM transactions")
            
            # Reset the auto-increment counter
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
            
            # Copy back from temp table - SQLite will assign new sequential IDs
            cursor.execute("""
                INSERT INTO transactions (date, description, amount, source, category, original_category)
                SELECT date, description, amount, source, category, original_category 
                FROM temp_transactions
                ORDER BY id
            """)
            
            # Drop temporary table
            cursor.execute("DROP TABLE temp_transactions")
        
        # Commit all changes
        cursor.execute("COMMIT")
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error deleting transaction: {str(e)}")
        # If an error occurs, try to rollback
        try:
            if 'cursor' in locals() and cursor:
                cursor.execute("ROLLBACK")
            if 'conn' in locals() and conn:
                conn.close()
        except:
            pass
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
    if not check_db_exists(db_path):
        return False
        
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
        
def save_budget(budget_df, month, db_path='finance_data.db'):
    """
    Save budget data to the database
    
    Parameters:
        budget_df (pandas.DataFrame): DataFrame with columns 'category' and 'amount'
        month (str): Month in YYYY-MM format
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Make sure database is initialized
    if not check_db_exists(db_path):
        initialize_database(db_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First delete any existing budget for this month
        cursor.execute("DELETE FROM budgets WHERE month = ?", (month,))
        
        # Insert new budget data
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        for _, row in budget_df.iterrows():
            cursor.execute("""
                INSERT INTO budgets (category, amount, month, created_date)
                VALUES (?, ?, ?, ?)
            """, (row['category'], row['amount'], month, current_date))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving budget: {str(e)}")
        return False
        
def load_budget(month, db_path='finance_data.db'):
    """
    Load budget data for a specific month
    
    Parameters:
        month (str): Month in YYYY-MM format
        db_path (str): Path to the SQLite database
    
    Returns:
        pandas.DataFrame: Budget data with columns 'category' and 'amount'
    """
    if not check_db_exists(db_path):
        # Initialize the database if it doesn't exist
        initialize_database(db_path)
        return pd.DataFrame(columns=['category', 'amount'])
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Get budget data for the specified month
        query = "SELECT category, amount FROM budgets WHERE month = ?"
        budget_df = pd.read_sql_query(query, conn, params=(month,))
        
        conn.close()
        
        if budget_df.empty:
            return pd.DataFrame(columns=['category', 'amount'])
        
        return budget_df
    except Exception as e:
        print(f"Error loading budget: {str(e)}")
        return pd.DataFrame(columns=['category', 'amount'])
        
def get_budget_months(db_path='finance_data.db'):
    """
    Get a list of months that have budget data
    
    Parameters:
        db_path (str): Path to the SQLite database
    
    Returns:
        list: List of months in YYYY-MM format
    """
    if not check_db_exists(db_path):
        # Initialize the database if it doesn't exist
        initialize_database(db_path)
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT month FROM budgets ORDER BY month DESC")
        months = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return months
    except Exception as e:
        print(f"Error getting budget months: {str(e)}")
        return []
        
def get_categories(db_path='finance_data.db'):
    """
    Get list of all categories from the database
    
    Parameters:
        db_path (str): Path to the SQLite database
    
    Returns:
        pandas.DataFrame: DataFrame containing categories
    """
    if not check_db_exists(db_path):
        # Initialize database if it doesn't exist
        initialize_database(db_path)
    
    try:
        conn = sqlite3.connect(db_path)
        
        query = "SELECT id, name, description, is_income, color FROM categories ORDER BY name"
        categories_df = pd.read_sql_query(query, conn)
        
        conn.close()
        return categories_df
    except Exception as e:
        print(f"Error getting categories: {str(e)}")
        return pd.DataFrame()

def delete_transactions_by_source(source, db_path='finance_data.db', reindex=True):
    """
    Delete all transactions from a specific source and optionally reindex remaining transactions
    
    Parameters:
        source (str): Source of transactions to delete (e.g., 'wells_fargo')
        db_path (str): Path to the SQLite database
        reindex (bool): If True, renumber all transaction IDs to ensure sequential order
    
    Returns:
        int: Number of transactions deleted, -1 if error
    """
    if not check_db_exists(db_path):
        return -1
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Get count of transactions to be deleted
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE source = ?", (source,))
        count = cursor.fetchone()[0]
        
        # Delete the transactions
        cursor.execute("DELETE FROM transactions WHERE source = ?", (source,))
        
        # Reindex remaining transactions if requested
        if reindex:
            # Create a temporary table to store transactions
            cursor.execute("""
                CREATE TEMPORARY TABLE temp_transactions AS 
                SELECT * FROM transactions ORDER BY id
            """)
            
            # Delete all from main table
            cursor.execute("DELETE FROM transactions")
            
            # Reset the auto-increment counter
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
            
            # Copy back from temp table - SQLite will assign new sequential IDs
            cursor.execute("""
                INSERT INTO transactions (date, description, amount, source, category, original_category)
                SELECT date, description, amount, source, category, original_category 
                FROM temp_transactions
                ORDER BY id
            """)
            
            # Drop temporary table
            cursor.execute("DROP TABLE temp_transactions")
        
        # Commit all changes
        cursor.execute("COMMIT")
        conn.close()
        
        return count
    except Exception as e:
        print(f"Error deleting transactions by source: {str(e)}")
        # If an error occurs, try to rollback
        try:
            if 'cursor' in locals() and cursor:
                cursor.execute("ROLLBACK")
            if 'conn' in locals() and conn:
                conn.close()
        except:
            pass
        return -1

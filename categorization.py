import pandas as pd
import re

def categorize_transactions(df):
    """
    Categorize transactions based on description keywords.
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions
    
    Returns:
        pandas.DataFrame: DataFrame with added/updated category column
    """
    # Define categories and their keywords
    categories = {
        'Groceries': ['trader', 'safeway', 'grocery', 'market', 'food', 'whole foods', 'albertsons', 'kroger', 'publix', 'aldi'],
        'Dining': ['restaurant', 'mcdonalds', 'starbucks', 'coffee', 'doordash', 'grubhub', 'uber eats', 'chipotle', 'wendys', 'burger', 'pizza', 'taco', 'cafe'],
        'Transportation': ['uber', 'lyft', 'gas', 'shell', 'chevron', 'transit', 'parking', 'exxon', 'mobil', 'bp', 'valero', 'toll', 'auto', 'car'],
        'Shopping': ['amazon', 'target', 'walmart', 'bestbuy', 'ebay', 'etsy', 'costco', 'sams club', 'macys', 'nordstrom', 'tj maxx', 'marshalls', 'kohls'],
        'Entertainment': ['netflix', 'hbo', 'spotify', 'movie', 'hulu', 'disney', 'theatre', 'theater', 'cinema', 'apple music', 'prime video', 'youtube', 'games'],
        'Housing': ['rent', 'mortgage', 'hoa', 'maintenance', 'apartment', 'property', 'lease', 'landlord', 'home', 'house'],
        'Utilities': ['electric', 'water', 'gas', 'internet', 'phone', 'utility', 'bill', 'power', 'cable', 'comcast', 'verizon', 'at&t', 'sprint', 'sewer'],
        'Health': ['doctor', 'pharmacy', 'medical', 'fitness', 'gym', 'health', 'dental', 'vision', 'cvs', 'walgreens', 'hospital', 'clinic', 'insurance'],
        'Insurance': ['insurance', 'geico', 'allstate', 'state farm', 'progressive', 'nationwide', 'liberty mutual', 'farmers', 'policy'],
        'Education': ['tuition', 'course', 'book', 'school', 'university', 'college', 'student', 'loan', 'class', 'education', 'learning'],
        'Income': ['payroll', 'salary', 'deposit', 'dividend', 'direct deposit', 'payment received', 'interest', 'refund', 'tax return'],
        'Investments': ['investment', 'transfer to', 'schwab', 'fidelity', 'vanguard', 'etrade', 'robinhood', 'stocks', 'bonds', 'mutual fund', 'retirement'],
        'Subscriptions': ['subscription', 'membership', 'monthly', 'annual fee', 'renewal', 'recurring'],
        'Travel': ['hotel', 'flight', 'airbnb', 'airline', 'expedia', 'booking.com', 'airfare', 'vacation', 'travel', 'resort', 'cruise', 'tour', 'trip'],
        'Personal Care': ['salon', 'haircut', 'spa', 'beauty', 'cosmetics', 'barber', 'stylist', 'nail', 'massage'],
        'Gifts & Donations': ['gift', 'donation', 'charity', 'donate', 'present', 'gofundme', 'fundraiser', 'patreon', 'kickstarter'],
        'Fees & Charges': ['fee', 'charge', 'interest', 'overdraft', 'penalty', 'late', 'service charge', 'atm fee', 'bank fee']
    }
    
    # Function to determine category based on description
    def get_category(description):
        if not description or pd.isna(description):
            return 'Uncategorized'
            
        description = str(description).lower()
        
        for category, keywords in categories.items():
            if any(re.search(r'\b' + re.escape(keyword) + r'\b', description) for keyword in keywords):
                return category
        
        return 'Miscellaneous'
    
    # Apply categorization
    if 'original_category' in df.columns and df['original_category'].notna().any():
        # Use original categories if available (from Chase, etc.)
        # Map the bank's categories to your standardized ones
        df['category'] = df.apply(
            lambda row: map_original_category(row['original_category']) 
            if pd.notna(row['original_category']) 
            else (row['category'] if pd.notna(row['category']) else get_category(row['description'])), 
            axis=1
        )
    else:
        # Use keyword matching where category is not already set
        df['category'] = df.apply(
            lambda row: row['category'] if pd.notna(row['category']) else get_category(row['description']),
            axis=1
        )
    
    return df

def map_original_category(original):
    """
    Map bank-provided categories to standardized categories
    
    Parameters:
        original (str): Original category from the bank
        
    Returns:
        str: Mapped standardized category
    """
    if pd.isna(original):
        return 'Uncategorized'
        
    mapping = {
        # Chase mappings
        'Food & Drink': 'Dining',
        'Groceries': 'Groceries',
        'Travel': 'Travel',
        'Shopping': 'Shopping',
        'Bills & Utilities': 'Utilities',
        'Health & Wellness': 'Health',
        'Entertainment': 'Entertainment',
        'Gas': 'Transportation',
        'Home': 'Housing',
        'Education': 'Education',
        'Personal': 'Personal Care',
        'Gifts & Donations': 'Gifts & Donations',
        'Business Services': 'Miscellaneous',
        # Bank of America mappings
        'Dining': 'Dining',
        'Grocery': 'Groceries',
        'Travel & Entertainment': 'Entertainment',
        'Shopping': 'Shopping',
        'Household Expenses': 'Housing',
        'Auto & Transport': 'Transportation',
        'Health & Wellness': 'Health',
        'Education': 'Education',
        'Subscriptions': 'Subscriptions',
        'Income & Transfers': 'Income',
        # Wells Fargo mappings
        'Dining Out': 'Dining',
        'Groceries/Supermarkets': 'Groceries',
        'Transportation': 'Transportation',
        'Shopping/Retail': 'Shopping',
        'Entertainment': 'Entertainment',
        'Home/Rent': 'Housing',
        'Utilities': 'Utilities',
        'Health/Medical': 'Health',
        'Insurance': 'Insurance',
        'Education/School': 'Education',
        'Income': 'Income',
        'Investments': 'Investments',
        'Travel/Vacation': 'Travel',
    }
    
    # Try to find an exact match
    if original in mapping:
        return mapping[original]
    
    # Try to find a partial match
    for bank_category, std_category in mapping.items():
        if bank_category.lower() in original.lower():
            return std_category
            
    return 'Miscellaneous'

def get_category_list(db_path='finance_data.db'):
    """
    Return a list of all categories including custom categories
    
    Parameters:
        db_path (str): Path to the SQLite database
        
    Returns:
        list: List of category names
    """
    # Default categories
    standard_categories = [
        'Groceries', 'Dining', 'Transportation', 'Shopping', 'Entertainment',
        'Housing', 'Utilities', 'Health', 'Insurance', 'Education',
        'Income', 'Investments', 'Subscriptions', 'Travel', 'Personal Care',
        'Gifts & Donations', 'Fees & Charges', 'Miscellaneous', 'Uncategorized'
    ]
    
    # Get any custom categories from the database
    custom_categories = get_custom_categories(db_path)
    
    # Combine standard and custom categories, ensuring no duplicates
    all_categories = list(set(standard_categories + custom_categories))
    all_categories.sort()  # Sort alphabetically
    
    return all_categories

def get_custom_categories(db_path='finance_data.db'):
    """
    Get custom categories from the database
    
    Parameters:
        db_path (str): Path to the SQLite database
    
    Returns:
        list: List of custom category names
    """
    import sqlite3
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if custom_categories table exists
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='custom_categories'
        ''')
        
        if cursor.fetchone() is None:
            # Table doesn't exist, create it
            cursor.execute('''
                CREATE TABLE custom_categories (
                    id INTEGER PRIMARY KEY,
                    category_name TEXT UNIQUE
                )
            ''')
            conn.commit()
            return []
        
        # Fetch all custom categories
        cursor.execute('SELECT category_name FROM custom_categories')
        categories = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return categories
    
    except Exception as e:
        print(f"Error getting custom categories: {str(e)}")
        return []

def add_custom_category(category_name, db_path='finance_data.db'):
    """
    Add a new custom category to the database
    
    Parameters:
        category_name (str): Name of the category to add
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if successful, False otherwise
    """
    import sqlite3
    
    try:
        # Validate category name
        if not category_name or len(category_name.strip()) == 0:
            return False
        
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure the table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_categories (
                id INTEGER PRIMARY KEY,
                category_name TEXT UNIQUE
            )
        ''')
        
        # Insert new category if it doesn't already exist
        cursor.execute(
            'INSERT OR IGNORE INTO custom_categories (category_name) VALUES (?)',
            (category_name.strip(),)
        )
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        # Check if anything was actually inserted (based on rowcount)
        return cursor.rowcount > 0
    
    except Exception as e:
        print(f"Error adding custom category: {str(e)}")
        return False

def delete_custom_category(category_name, db_path='finance_data.db'):
    """
    Delete a custom category from the database
    
    Parameters:
        category_name (str): Name of the category to delete
        db_path (str): Path to the SQLite database
    
    Returns:
        bool: True if successful, False otherwise
    """
    import sqlite3
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Delete the category
        cursor.execute(
            'DELETE FROM custom_categories WHERE category_name = ?',
            (category_name,)
        )
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        return True
    
    except Exception as e:
        print(f"Error deleting custom category: {str(e)}")
        return False

def update_transaction_category(df, transaction_id, new_category):
    """
    Update the category of a specific transaction
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions
        transaction_id (int): Index of the transaction to update
        new_category (str): New category to assign
        
    Returns:
        pandas.DataFrame: Updated DataFrame
    """
    df.at[transaction_id, 'category'] = new_category
    return df

def get_income_categories():
    """
    Return a list of categories that are typically income (positive amounts)
    
    Returns:
        list: List of income category names
    """
    return ['Income', 'Investments', 'Refund']
    
def normalize_transaction_signs(df):
    """
    Normalize transaction signs based on category - income categories should be positive, 
    expense categories should be negative
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions with 'amount' and 'category' columns
    
    Returns:
        pandas.DataFrame: DataFrame with normalized amount signs
    """
    # Make a copy to avoid SettingWithCopyWarning
    df_copy = df.copy()
    
    # Get income categories
    income_categories = get_income_categories()
    
    # Function to apply correct sign
    def apply_sign(row):
        # Skip if amount is zero
        if row['amount'] == 0:
            return row['amount']
            
        # If category is income
        if row['category'] in income_categories:
            # Amount should be positive
            return abs(row['amount'])
        else:
            # Expense amounts should be negative
            return -abs(row['amount'])
    
    # Apply the sign normalization
    df_copy.loc[:, 'amount'] = df_copy.apply(apply_sign, axis=1)
    
    return df_copy

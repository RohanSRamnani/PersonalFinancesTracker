import pandas as pd
import numpy as np
import os
from datetime import datetime

def import_statement(filepath, source):
    """
    Import a statement from any source and standardize the format
    
    Parameters:
        filepath (str): Path to the statement file
        source (str): One of 'wells_fargo', 'chase', 'bank_of_america', 'apple_pay', 'schwab'
    
    Returns:
        pandas.DataFrame: Standardized dataframe with transactions
    """
    try:
        if source == 'wells_fargo':
            df = pd.read_csv(filepath)
            # Wells Fargo specific column mapping
            df = df.rename(columns={
                'Date': 'date',
                'Description': 'description',
                'Amount': 'amount'
            })
        elif source == 'chase':
            # Chase specific format
            df = pd.read_csv(filepath)
            df = df.rename(columns={
                'Transaction Date': 'date',
                'Post Date': 'post_date',
                'Description': 'description',
                'Amount': 'amount',
                'Category': 'original_category'
            })
        elif source == 'bank_of_america':
            df = pd.read_csv(filepath)
            df = df.rename(columns={
                'Posted Date': 'date',
                'Payee': 'description',
                'Amount': 'amount'
            })
        elif source == 'apple_pay':
            df = pd.read_csv(filepath)
            df = df.rename(columns={
                'Date': 'date',
                'Description': 'description',
                'Amount (USD)': 'amount'
            })
        elif source == 'schwab':
            df = pd.read_csv(filepath)
            df = df.rename(columns={
                'Date': 'date',
                'Description': 'description',
                'Amount': 'amount'
            })
        else:
            raise ValueError(f"Unsupported source: {source}")
        
        # Standardize date format
        df['date'] = pd.to_datetime(df['date'])
        
        # Ensure amount is consistently signed (expenses negative, income positive)
        if source in ['chase', 'wells_fargo']:
            # These sources may have reversed signs
            df['amount'] = -df['amount']
        
        # Add source column
        df['source'] = source
        
        # Ensure all necessary columns exist
        required_columns = ['date', 'description', 'amount', 'source']
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        
        # Add standard columns if they don't exist
        if 'category' not in df.columns:
            df['category'] = None
            
        if 'original_category' not in df.columns:
            df['original_category'] = None
        
        # Select only the columns we need
        return df[['date', 'description', 'amount', 'source', 'category', 'original_category']]
    
    except Exception as e:
        raise Exception(f"Error importing file: {str(e)}")

def detect_source_from_header(filepath):
    """
    Try to automatically detect the source bank from CSV headers
    
    Parameters:
        filepath (str): Path to the CSV file
    
    Returns:
        str: Detected source or None if not detected
    """
    try:
        # Read just the header row
        header = pd.read_csv(filepath, nrows=0).columns.tolist()
        header_str = ' '.join(header).lower()
        
        if 'wells' in header_str or ('date' in header_str and 'description' in header_str and 'wells fargo' in header_str):
            return 'wells_fargo'
        elif 'transaction date' in header_str and 'post date' in header_str:
            return 'chase'
        elif 'posted date' in header_str and 'payee' in header_str:
            return 'bank_of_america'
        elif 'apple' in header_str or 'apple pay' in header_str:
            return 'apple_pay'
        elif 'schwab' in header_str or ('date' in header_str and 'description' in header_str and 'schwab' in header_str):
            return 'schwab'
        return None
    except:
        return None

def read_file_to_preview(filepath, num_rows=5):
    """
    Read a CSV file and return a preview for displaying to the user
    
    Parameters:
        filepath (str): Path to the CSV file
        num_rows (int): Number of rows to preview
    
    Returns:
        pandas.DataFrame: Preview of the file content
    """
    try:
        preview = pd.read_csv(filepath, nrows=num_rows)
        return preview
    except:
        return pd.DataFrame({"Error": ["Could not read file. Please check the format."]})

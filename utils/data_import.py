import pandas as pd
import numpy as np
import os
from datetime import datetime
import re

def import_statement(filepath, source, page_numbers=None):
    """
    Import a statement from any source and standardize the format
    
    Parameters:
        filepath (str): Path to the statement file
        source (str): One of 'wells_fargo', 'chase', 'bank_of_america', 'apple_pay', 'schwab'
        page_numbers (list, optional): This parameter is kept for backward compatibility but is not used
    
    Returns:
        pandas.DataFrame: Standardized dataframe with transactions
    """
    try:
        # Handle CSV files based on source
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
        
        # Standardize date format with error handling for incomplete dates
        try:
            # First attempt - try standard conversion
            df['date'] = pd.to_datetime(df['date'])
        except (ValueError, TypeError, pd.errors.OutOfBoundsDatetime):
            print("Initial date parsing failed, attempting to fix date formats...")
            
            # Try to find the year from:
            # 1. First, check the filename
            # 2. Next, check if sheet name might have year information
            # 3. If all else fails, use current year
            year = None
            
            # 1. Check if we can extract year from filename
            if os.path.basename(filepath).startswith('20') and len(os.path.basename(filepath)) >= 4:
                try:
                    year = int(os.path.basename(filepath)[:4])
                    print(f"Extracted year from filename: {year}")
                except ValueError:
                    pass
            
            # 2. See if the first row contains a cell that could be a year (sheet name or header)
            if year is None and 'Sheet' in df.columns:
                sheet_name = df['Sheet'].iloc[0] if not pd.isna(df['Sheet'].iloc[0]) else None
                if sheet_name and str(sheet_name).startswith('20') and len(str(sheet_name)) >= 4:
                    try:
                        year = int(str(sheet_name)[:4])
                        print(f"Extracted year from sheet name: {year}")
                    except ValueError:
                        pass
            
            # 3. Check if there's any column name that looks like a year
            if year is None:
                for col in df.columns:
                    if str(col).startswith('20') and len(str(col)) >= 4:
                        try:
                            year = int(str(col)[:4])
                            print(f"Extracted year from column name: {year}")
                            break
                        except ValueError:
                            pass
            
            # 4. Fallback to current year if we still don't have a year
            if year is None:
                year = datetime.now().year
                print(f"Using current year as fallback: {year}")
            
            # Handle different date formats
            
            # For MM/DD format (e.g., "12/27")
            if isinstance(df['date'].iloc[0], str) and len(df['date'].iloc[0].split('/')) == 2:
                print(f"Detected MM/DD format, adding year {year}")
                # Add extracted year to make dates parseable
                df['date'] = df['date'].apply(lambda x: f"{x}/{year}" if isinstance(x, str) and len(x.split('/')) == 2 else x)
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # If we still have NaT values, try other common date formats
            if df['date'].isna().any():
                temp_dates = pd.Series(df['date'].copy())
                formats_to_try = ['%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y', '%m/%d/%y', '%d/%m/%Y']
                
                for date_format in formats_to_try:
                    # Try to parse with this format
                    try:
                        parsed = pd.to_datetime(temp_dates, format=date_format, errors='coerce')
                        
                        # If this format parsed any dates successfully, merge them in
                        if not parsed.isna().all():
                            print(f"Successfully parsed some dates with format: {date_format}")
                            # For rows where current is NaT but parsed is not, use the parsed value
                            mask = df['date'].isna() & ~parsed.isna()
                            df.loc[mask, 'date'] = parsed[mask]
                            
                            # If all dates are now valid, stop trying formats
                            if not df['date'].isna().any():
                                break
                    except Exception as e:
                        # Format didn't work, try the next one
                        continue
            
            # If we still have NaT values, try a last-resort approach for MM/DD format with extracted year
            if df['date'].isna().any():
                print("Attempting last-resort date parsing for remaining NaT values...")
                
                # Get only the rows with NaT dates
                mask = df['date'].isna()
                nat_dates = df.loc[mask, 'date'].copy()
                
                # Try to convert each string to a date with the known year
                fixed_dates = []
                for date_str in nat_dates:
                    try:
                        if isinstance(date_str, str):
                            parts = date_str.strip().split('/')
                            if len(parts) == 2:
                                # Assume MM/DD format, add the year
                                month, day = parts
                                new_date_str = f"{month.zfill(2)}/{day.zfill(2)}/{year}"
                                fixed_dates.append(pd.to_datetime(new_date_str))
                            else:
                                fixed_dates.append(pd.NaT)
                        else:
                            fixed_dates.append(pd.NaT)
                    except:
                        fixed_dates.append(pd.NaT)
                
                # Update only the formerly NaT values that we could fix
                if fixed_dates:
                    fixed_series = pd.Series(fixed_dates, index=nat_dates.index)
                    valid_mask = ~fixed_series.isna()
                    if valid_mask.any():
                        print(f"Fixed {valid_mask.sum()} additional dates with manual parsing")
                        df.loc[fixed_series.index[valid_mask], 'date'] = fixed_series[valid_mask]
            
            # Drop rows with invalid dates
            original_count = len(df)
            df = df.dropna(subset=['date'])
            if len(df) < original_count:
                print(f"Dropped {original_count - len(df)} rows with invalid dates")
                
            print(f"Successfully parsed {len(df)} dates")
        
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
        
        # Clean up amount field - ensure it's a float
        if df['amount'].dtype == 'object':
            df['amount'] = df['amount'].astype(str).str.replace('$', '').str.replace(',', '').astype(float)
        
        # Select only the columns we need
        return df[['date', 'description', 'amount', 'source', 'category', 'original_category']]
    
    except Exception as e:
        raise Exception(f"Error importing file: {str(e)}")

def detect_source_from_header(filepath):
    """
    Try to automatically detect the source bank from CSV header
    
    Parameters:
        filepath (str): Path to the CSV file
    
    Returns:
        str: Detected source or None if not detected
    """
    try:
        # For CSV files, check the header
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
    except Exception as e:
        print(f"Error detecting source: {str(e)}")
        return None

def detect_file_type(filepath):
    """
    Detect if file is CSV or PDF
    
    Parameters:
        filepath (str): Path to the file
    
    Returns:
        str: 'csv', 'pdf', or 'unknown'
    """
    _, ext = os.path.splitext(filepath)
    if ext.lower() == '.csv':
        return 'csv'
    elif ext.lower() == '.pdf':
        return 'pdf'
    else:
        return 'unknown'

def read_file_to_preview(filepath, num_rows=5):
    """
    Read a CSV file and return a preview for displaying to the user
    
    Parameters:
        filepath (str): Path to the file
        num_rows (int): Number of rows to preview
    
    Returns:
        pandas.DataFrame: Preview of the file content
    """
    try:
        # For CSV files
        return pd.read_csv(filepath, nrows=num_rows)
    except Exception as e:
        # If we encounter an error, return an empty DataFrame with an error message
        print(f"Error generating preview: {str(e)}")
        return pd.DataFrame({'Error': [f"Could not preview file: {str(e)}"]})
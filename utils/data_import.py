import pandas as pd
import numpy as np
import os
import io
from datetime import datetime
import pdfplumber
import PyPDF2
import tabula
import re

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
        # Detect file type (CSV or PDF)
        file_type = detect_file_type(filepath)
        
        if file_type == 'csv':
            # Handle CSV files
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
        
        elif file_type == 'pdf':
            # Handle PDF files
            df = extract_tables_from_pdf(filepath, source)
            if df.empty:
                raise ValueError(f"Could not extract transactions from the PDF file for {source}")
        
        else:
            raise ValueError(f"Unsupported file format: {file_type}. Please use CSV or PDF.")
        
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
        
        # Clean up amount field - ensure it's a float
        if df['amount'].dtype == 'object':
            df['amount'] = df['amount'].astype(str).str.replace('$', '').str.replace(',', '').astype(float)
        
        # Select only the columns we need
        return df[['date', 'description', 'amount', 'source', 'category', 'original_category']]
    
    except Exception as e:
        raise Exception(f"Error importing file: {str(e)}")

def detect_source_from_header(filepath):
    """
    Try to automatically detect the source bank from file content
    
    Parameters:
        filepath (str): Path to the file (CSV or PDF)
    
    Returns:
        str: Detected source or None if not detected
    """
    try:
        file_type = detect_file_type(filepath)
        
        if file_type == 'csv':
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
        
        elif file_type == 'pdf':
            # For PDF files, check text content for bank names
            try:
                # First try with PyPDF2
                with open(filepath, 'rb') as f:
                    try:
                        # Try with newer PyPDF2 version
                        pdf_reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page_num in range(min(3, len(pdf_reader.pages))):  # Just check first 3 pages
                            text += pdf_reader.pages[page_num].extract_text().lower()
                    except AttributeError:
                        # Fall back to older PyPDF2 version if needed
                        f.seek(0)  # Reset file pointer
                        pdf_reader = PyPDF2.PdfFileReader(f)
                        text = ""
                        for page_num in range(min(3, pdf_reader.numPages)):  # Just check first 3 pages
                            text += pdf_reader.getPage(page_num).extractText().lower()
            except:
                # If PyPDF2 fails, try with pdfplumber
                try:
                    with pdfplumber.open(filepath) as pdf:
                        text = ""
                        for page_num in range(min(3, len(pdf.pages))):
                            text += pdf.pages[page_num].extract_text().lower()
                except:
                    return None
                    
            # Check for bank names in the text
            if 'wells fargo' in text:
                return 'wells_fargo'
            elif 'chase' in text:
                return 'chase'
            elif 'bank of america' in text:
                return 'bank_of_america'
            elif 'apple' in text or 'apple pay' in text:
                return 'apple_pay'
            elif 'schwab' in text:
                return 'schwab'
                
        return None
    except Exception as e:
        print(f"Error detecting source: {str(e)}")
        return None

def extract_tables_from_pdf(filepath, source):
    """
    Extract tables from PDF statements
    
    Parameters:
        filepath (str): Path to the PDF file
        source (str): One of 'wells_fargo', 'chase', 'bank_of_america', 'apple_pay', 'schwab'
    
    Returns:
        pandas.DataFrame: Dataframe containing transaction data
    """
    try:
        # Try using tabula first (works well for most structured tables)
        tables = tabula.read_pdf(filepath, pages='all', multiple_tables=True)
        
        # Initialize an empty dataframe to store consolidated data
        all_data = pd.DataFrame()
        
        if tables and len(tables) > 0:
            # Combine all tables found
            for table in tables:
                if not table.empty:
                    # Try to identify if this table contains transaction data
                    columns = table.columns.tolist()
                    columns_str = ' '.join([str(col).lower() for col in columns])
                    
                    # Check if it looks like a transaction table
                    if any(keyword in columns_str for keyword in ['date', 'description', 'amount', 'transaction']):
                        # Append to our combined dataframe
                        all_data = pd.concat([all_data, table], ignore_index=True)
            
            if not all_data.empty:
                # Map columns based on source
                if source == 'wells_fargo':
                    # Try to identify the Wells Fargo specific columns
                    for col in all_data.columns:
                        if 'date' in str(col).lower():
                            all_data = all_data.rename(columns={col: 'date'})
                        elif any(desc in str(col).lower() for desc in ['description', 'payee']):
                            all_data = all_data.rename(columns={col: 'description'})
                        elif 'amount' in str(col).lower():
                            all_data = all_data.rename(columns={col: 'amount'})
                
                # Similar mapping for other banks...
                elif source == 'chase':
                    for col in all_data.columns:
                        if 'transaction date' in str(col).lower():
                            all_data = all_data.rename(columns={col: 'date'})
                        elif 'description' in str(col).lower():
                            all_data = all_data.rename(columns={col: 'description'})
                        elif 'amount' in str(col).lower():
                            all_data = all_data.rename(columns={col: 'amount'})
                
                # Add more mappings for other banks as needed
                
                # If we have the minimum required columns, return the data
                required_cols = ['date', 'description', 'amount']
                if all(col in all_data.columns for col in required_cols):
                    return all_data
        
        # If tabula didn't work well, try pdfplumber as a fallback
        with pdfplumber.open(filepath) as pdf:
            text_content = []
            for page in pdf.pages:
                text_content.append(page.extract_text())
            
            full_text = '\n'.join(text_content)
            
            # Attempt to parse based on bank format
            if source == 'wells_fargo':
                # Example pattern for Wells Fargo: Date, Description, Amount
                pattern = r'(\d{2}/\d{2}/\d{2,4})\s+(.+?)\s+([-+]?\$?\d+\.\d{2})'
                matches = re.findall(pattern, full_text)
                
                if matches:
                    data = []
                    for match in matches:
                        date, description, amount = match
                        # Remove $ sign and convert to float
                        amount = float(amount.replace('$', '').replace(',', ''))
                        data.append({'date': date, 'description': description, 'amount': amount})
                    
                    return pd.DataFrame(data)
            
            # Add similar patterns for other banks
        
        # If all else fails, return empty dataframe
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error extracting tables from PDF: {str(e)}")
        return pd.DataFrame()

def detect_file_type(filepath):
    """
    Detect if file is CSV or PDF
    
    Parameters:
        filepath (str): Path to the file
    
    Returns:
        str: 'csv' or 'pdf'
    """
    _, ext = os.path.splitext(filepath.lower())
    if ext == '.csv':
        return 'csv'
    elif ext == '.pdf':
        return 'pdf'
    else:
        return 'unknown'

def read_file_to_preview(filepath, num_rows=5):
    """
    Read a CSV or PDF file and return a preview for displaying to the user
    
    Parameters:
        filepath (str): Path to the file
        num_rows (int): Number of rows to preview
    
    Returns:
        pandas.DataFrame: Preview of the file content
    """
    try:
        file_type = detect_file_type(filepath)
        
        if file_type == 'csv':
            preview = pd.read_csv(filepath, nrows=num_rows)
            return preview
        elif file_type == 'pdf':
            # For PDF files, try to extract a table preview
            tables = tabula.read_pdf(filepath, pages='1', multiple_tables=True)
            if tables and len(tables) > 0:
                # Return the first table found
                return tables[0].head(num_rows)
            else:
                # If no tables found, return a preview of text content
                with pdfplumber.open(filepath) as pdf:
                    if len(pdf.pages) > 0:
                        text = pdf.pages[0].extract_text()
                        # Create a simple DataFrame with the first few lines of text
                        lines = text.split('\n')[:num_rows]
                        return pd.DataFrame({'PDF Content': lines})
            
            return pd.DataFrame({"Preview": ["PDF file detected. Import to process."]})
        else:
            return pd.DataFrame({"Error": ["Unsupported file format. Please use CSV or PDF."]})
    except Exception as e:
        return pd.DataFrame({"Error": [f"Could not read file: {str(e)}"]})

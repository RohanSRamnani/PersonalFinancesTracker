import pandas as pd
import numpy as np
import os
import io
from datetime import datetime
import re

def import_statement(filepath, source, page_numbers=None):
    """
    Import a statement from any source and standardize the format
    
    Parameters:
        filepath (str): Path to the statement file
        source (str): One of 'wells_fargo', 'chase', 'bank_of_america', 'apple_pay', 'schwab'
        page_numbers (list, optional): Specific pages to extract from PDF. Default is None (all pages).
    
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
            df = extract_tables_from_pdf(filepath, source, page_numbers)
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

def extract_tables_from_pdf(filepath, source, page_numbers=None):
    """
    Extract tables from PDF statements
    
    Parameters:
        filepath (str): Path to the PDF file
        source (str): One of 'wells_fargo', 'chase', 'bank_of_america', 'apple_pay', 'schwab'
        page_numbers (list, optional): Specific pages to extract. Default is None (all pages).
    
    Returns:
        pandas.DataFrame: Dataframe containing transaction data
    """
    # Initialize an empty dataframe to store consolidated data
    all_data = pd.DataFrame()
    
    # First try pdfplumber as it's more reliable
    try:
        # Initialize data variable to prevent "possibly unbound" error
        data = []
        
        with pdfplumber.open(filepath) as pdf:
            # Filter pages if specific page numbers were provided
            selected_pages = pdf.pages
            if page_numbers:
                # Convert from 1-based page numbers (user input) to 0-based indices
                page_indices = [p-1 for p in page_numbers if 0 < p <= len(pdf.pages)]
                if page_indices:  # Only use filtered pages if valid page numbers were provided
                    selected_pages = [pdf.pages[idx] for idx in page_indices]
                    print(f"Extracting from {len(selected_pages)} specific pages: {[i+1 for i in page_indices]}")
            
            # Try to extract tables using pdfplumber first
            found_tables = False
            for page in selected_pages:
                try:
                    tables = page.extract_tables()
                    if tables and len(tables) > 0:
                        found_tables = True
                        for table in tables:
                            # Convert list of lists to DataFrame
                            if table and len(table) > 1:  # Make sure there's a header row and data
                                df = pd.DataFrame(table[1:], columns=table[0])
                                
                                # Check if it looks like a transaction table
                                if df.shape[1] >= 3:  # At least 3 columns (date, description, amount)
                                    # Try to identify transaction-related columns
                                    for i, col in enumerate(df.columns):
                                        col_lower = str(col).lower()
                                        if 'date' in col_lower or any(month in col_lower for month in 
                                                                   ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                                                    'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                                            df = df.rename(columns={col: 'date'})
                                        elif any(desc in col_lower for desc in ['description', 'payee', 'merchant', 'transaction']):
                                            df = df.rename(columns={col: 'description'})
                                        elif any(amt in col_lower for amt in ['amount', 'sum', 'total', '$']):
                                            df = df.rename(columns={col: 'amount'})
                                    
                                    # Check if we identified key columns
                                    required_cols = ['date', 'description', 'amount']
                                    if all(col in df.columns for col in required_cols):
                                        all_data = pd.concat([all_data, df], ignore_index=True)
                except:
                    # Table extraction failed for this page, continue to next
                    continue
            
            # If we couldn't find tables, try text-based extraction
            if not found_tables or all_data.empty:
                text_content = []
                
                # Use the same page filtering as above for text extraction
                if page_numbers:
                    # Convert from 1-based page numbers (user input) to 0-based indices
                    page_indices = [p-1 for p in page_numbers if 0 < p <= len(pdf.pages)]
                    if page_indices:  # Only use filtered pages if valid page numbers were provided
                        text_pages = [pdf.pages[idx] for idx in page_indices]
                        print(f"Extracting text from {len(text_pages)} specific pages: {[i+1 for i in page_indices]}")
                    else:
                        text_pages = pdf.pages
                else:
                    text_pages = pdf.pages
                
                for page in text_pages:
                    extracted_text = page.extract_text()
                    if extracted_text:
                        text_content.append(extracted_text)
                
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
                        
                        all_data = pd.DataFrame(data)
                
                # Chase Credit Card statements - look for data under ACCOUNT ACTIVITY section
                elif source == 'chase':
                    # First try to find the "ACCOUNT ACTIVITY" section
                    account_activity_match = re.search(r'ACCOUNT\s+ACTIVITY(.*?)(?:INTEREST\s+CHARGED|FEES\s+CHARGED|TOTALS\s+YEAR-TO-DATE)', full_text, re.DOTALL)
                    
                    if account_activity_match:
                        # Extract the account activity section
                        activity_text = account_activity_match.group(1)
                        
                        # Based on the screenshot format, first look for sections like "PAYMENTS AND OTHER CREDITS", "PURCHASE", etc.
                        sections = []
                        
                        # Find all section headers and their content
                        section_headers = ["PAYMENTS AND OTHER CREDITS", "PURCHASE", "CASH ADVANCES", "FEES CHARGED", "INTEREST CHARGED"]
                        
                        for i, header in enumerate(section_headers):
                            start_pos = activity_text.find(header)
                            if start_pos >= 0:
                                # Find the end of this section (next section or end of activity text)
                                end_pos = len(activity_text)
                                for next_header in section_headers[i+1:]:
                                    next_pos = activity_text.find(next_header, start_pos + 1)
                                    if next_pos > start_pos:
                                        end_pos = next_pos
                                        break
                                
                                # Extract this section
                                section_text = activity_text[start_pos:end_pos]
                                sections.append((header, section_text))
                        
                        # Process each section
                        data = []
                        for section_name, section_text in sections:
                            # Pattern for Chase format from screenshot: Date (MM/DD) + Description + Amount
                            # We'll use a more specific pattern based on the Chase statement format
                            pattern = r'(\d{2}/\d{2})\s+(.*?)\s+([-+]?\d+\.\d{2})'
                            trans_matches = re.findall(pattern, section_text)
                            
                            for match in trans_matches:
                                date, description, amount = match
                                
                                # Skip header rows
                                if 'Date of Transaction' in description:
                                    continue
                                
                                # Clean up description and amount
                                description = re.sub(r'\s+', ' ', description).strip()
                                amount_float = float(amount.replace(',', ''))
                                
                                # Handle sign based on section context
                                if section_name == "PAYMENTS AND OTHER CREDITS":
                                    # These are payments or credits, should be positive (money in)
                                    amount_float = abs(amount_float)
                                elif section_name in ["PURCHASE", "CASH ADVANCES", "FEES CHARGED", "INTEREST CHARGED"]:
                                    # These are expenses, should be negative (money out)
                                    amount_float = -abs(amount_float)
                                
                                data.append({
                                    'date': date, 
                                    'description': description, 
                                    'amount': amount_float
                                })
                        
                        # If we found any transactions, create the dataframe
                        if data:
                            all_data = pd.DataFrame(data)
                    
                    # If section-based extraction didn't work, try a simpler pattern
                    if all_data.empty:
                        # Extract the date format MM/DD from the statement
                        date_pattern = r'(\d{2}/\d{2})'
                        
                        # Look for lines with date at beginning, merchant/description in middle, and amount at end
                        # Format matches what we see in the screenshot
                        pattern = r'(\d{2}/\d{2})\s+([A-Z0-9].*?)\s+([-+]?\d+\.\d{2})'
                        matches = re.findall(pattern, full_text)
                        
                        if matches:
                            data = []
                            for match in matches:
                                date, description, amount = match
                                
                                # Skip if this is a header row
                                if 'DATE OF TRANSACTION' in description.upper():
                                    continue
                                
                                # Convert amount to float
                                amount_float = float(amount.replace(',', ''))
                                
                                # Determine if this is a payment based on description
                                is_payment = ('PAYMENT' in description.upper() or 
                                              'CREDIT' in description.upper() or 
                                              'REFUND' in description.upper())
                                
                                # Set the sign convention
                                if is_payment:
                                    amount_float = abs(amount_float)  # Payments should be positive
                                else:
                                    amount_float = -abs(amount_float)  # Purchases should be negative
                                
                                data.append({
                                    'date': date, 
                                    'description': description.strip(), 
                                    'amount': amount_float
                                })
                            
                            all_data = pd.DataFrame(data)
                
                # Bank of America - look for data under "Transactions" section
                elif source == 'bank_of_america':
                    # Find the Transactions section - based on the screenshot format
                    transactions_match = re.search(r'Transactions(.*?)(?:Interest\s+Charged|Totals\s+Year-to-Date|^\s*$)', full_text, re.DOTALL | re.MULTILINE)
                    
                    if transactions_match:
                        # Extract the transactions section
                        transactions_text = transactions_match.group(1)
                        
                        # For Bank of America, the transaction and posting date pattern is very specific
                        # Based on the screenshot format MM/DD followed by MM/DD then description
                        pattern = r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+([^\n]+?)(?:\s+(\d+)\s+\d+\s+|)(-?\d+\.\d{2})'
                        trans_matches = re.findall(pattern, transactions_text)
                        
                        if trans_matches:
                            data = []
                            for match in trans_matches:
                                if len(match) == 5:  # Full pattern with reference number
                                    trans_date, post_date, description, ref_num, amount = match
                                    # Skip if this seems to be a header row
                                    if 'Transaction' in description and 'Date' in description:
                                        continue
                                else:  # Simplified pattern without reference number
                                    trans_date, post_date, description, amount = match
                                
                                # Clean the description - remove extra whitespace and fix formatting
                                description = re.sub(r'\s+', ' ', description).strip()
                                
                                try:
                                    # Convert amount to float, handling negative values correctly
                                    # If amount has a leading minus sign, it's already negative
                                    amount_clean = amount.replace(',', '')
                                    amount_float = float(amount_clean)
                                    
                                    # In Bank of America statements:
                                    # - Payments/Credits usually show with a minus sign preceding the amount
                                    # - Purchases/Debits usually show as positive amounts
                                    # We want payments as positive (money in) and purchases as negative (money out)
                                    
                                    # Check for payment/credit or purchase based on keywords and section headings
                                    is_payment = any(keyword in description.upper() for keyword in [
                                        'PAYMENT', 'CREDIT', 'DEPOSIT', 'REFUND', 'RETURN'
                                    ]) or amount_float < 0
                                    
                                    # For payments/credits, make sure they're positive
                                    if is_payment:
                                        amount_float = abs(amount_float)
                                    # For purchases/debits, make sure they're negative
                                    elif amount_float > 0:
                                        amount_float = -amount_float
                                    
                                    data.append({
                                        'date': trans_date, 
                                        'post_date': post_date,
                                        'description': description, 
                                        'amount': amount_float
                                    })
                                except ValueError:
                                    # Skip lines that can't be parsed correctly
                                    continue
                                    
                        # If we couldn't find transactions with the specific pattern, try a more generic approach
                        # This might catch the data from the screenshot format even if the section headers are different
                        if not data:
                            # Look for patterns that match date-date-description-amount
                            pattern = r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+(-?\d+\.\d{2})'
                            matches = re.findall(pattern, full_text)
                            
                            if matches:
                                data = []
                                for match in matches:
                                    trans_date, post_date, description, amount = match
                                    
                                    # Clean up and convert amount to float
                                    amount_float = float(amount.replace(',', ''))
                                    
                                    # Determine if this is a payment based on context
                                    is_payment = 'PAYMENT' in description.upper() or amount_float < 0
                                    
                                    # Standardize the sign convention
                                    if is_payment:
                                        amount_float = abs(amount_float)  # Payments are positive
                                    elif amount_float > 0:
                                        amount_float = -amount_float      # Purchases are negative
                                    
                                    data.append({
                                        'date': trans_date,
                                        'post_date': post_date,
                                        'description': description.strip(),
                                        'amount': amount_float
                                    })
                            
                            all_data = pd.DataFrame(data)
    except Exception as e:
        print(f"pdfplumber extraction failed: {str(e)}")
    
    # If pdfplumber didn't work well, try tabula as a fallback
    if all_data.empty:
        try:
            # Determine which pages to process
            pages_str = '1'  # Default to first page
            if page_numbers:
                # Format page numbers for tabula (comma-separated string)
                pages_str = ','.join([str(p) for p in page_numbers])
                print(f"Using specific pages with tabula: {pages_str}")
            
            # Use a more conservative approach with tabula
            try:
                tables = tabula.read_pdf(filepath, pages=pages_str, multiple_tables=True)
                
                # If successful and no specific pages were requested, try all pages
                if tables and len(tables) > 0 and not page_numbers:
                    # Try to get tables from all pages
                    tables = tabula.read_pdf(filepath, pages='all', multiple_tables=True)
            except:
                # Fallback to specific options if the generic approach fails
                tables = tabula.read_pdf(filepath, pages=pages_str, multiple_tables=True, 
                                         stream=True, guess=False, lattice=True)
            
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
        except Exception as e:
            print(f"tabula extraction failed: {str(e)}")
    
    # Final check if we have the necessary columns
    if not all_data.empty:
        required_cols = ['date', 'description', 'amount']
        missing_cols = [col for col in required_cols if col not in all_data.columns]
        
        if not missing_cols:
            return all_data
    
    # If all else fails, return empty dataframe
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
            # Start with pdfplumber for text extraction which is more reliable
            try:
                with pdfplumber.open(filepath) as pdf:
                    if len(pdf.pages) > 0:
                        # First try table extraction with pdfplumber
                        try:
                            tables = pdf.pages[0].extract_tables()
                            if tables and len(tables) > 0:
                                # Use the first table
                                table = tables[0]
                                if len(table) > 1:  # Has header and data
                                    df = pd.DataFrame(table[1:num_rows+1], columns=table[0])
                                    return df
                        except:
                            pass  # Fall back to text extraction if tables fail
                        
                        # If table extraction fails, use text
                        text = pdf.pages[0].extract_text()
                        if text:
                            lines = text.split('\n')[:num_rows]
                            return pd.DataFrame({'PDF Content': lines})
            except Exception as pdf_err:
                print(f"pdfplumber preview failed: {str(pdf_err)}")
            
            # Try tabula as a fallback with more conservative settings
            try:
                # Use safer settings to avoid CMYK color issues
                tables = tabula.read_pdf(filepath, pages='1', guess=False, 
                                         stream=True, multiple_tables=True)
                if tables and len(tables) > 0 and not tables[0].empty:
                    return tables[0].head(num_rows)
            except Exception as tabula_err:
                print(f"tabula preview failed: {str(tabula_err)}")
            
            # If both methods fail, just indicate it's a PDF
            return pd.DataFrame({"Preview": ["PDF file detected. Import to process."]})
        else:
            return pd.DataFrame({"Error": ["Unsupported file format. Please use CSV or PDF."]})
    except Exception as e:
        return pd.DataFrame({"Error": [f"Could not read file: {str(e)}"]})

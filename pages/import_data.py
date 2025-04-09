import streamlit as st
import pandas as pd
import os
from utils.data_import import import_statement, detect_source_from_header, read_file_to_preview, detect_file_type
from utils.categorization import categorize_transactions
from utils.database import save_to_database, load_from_database

st.set_page_config(
    page_title="Import Data - Personal Finance Tracker",
    page_icon="💰",
    layout="wide"
)

# Create temp_uploads directory if it doesn't exist
import os
if not os.path.exists('temp_uploads'):
    os.makedirs('temp_uploads', exist_ok=True)
    # Set permissions to ensure we can write files
    try:
        os.chmod('temp_uploads', 0o777)
    except:
        pass

st.title("Import Financial Data")

# Initialize database path in session state if not already there
if 'db_path' not in st.session_state:
    st.session_state.db_path = 'finance_data.db'

def main():
    # Instructions
    st.markdown("""
    Upload your financial statements to import them into the system. 
    The app supports statements from:
    - Wells Fargo
    - Chase
    - Bank of America
    - Apple Pay
    - Schwab
    
    **Supported format:** CSV files only
    """)
    
    # File upload - CSV only
    uploaded_file = st.file_uploader("Upload statement file", type=["csv"])
    
    # Initialize temp_file_path outside of try/except blocks to avoid unbound variable issues
    temp_file_path = None
    
    if uploaded_file is not None:
        try:
            # Save uploaded file temporarily
            import uuid
            # Generate a unique ID to avoid name conflicts
            unique_id = uuid.uuid4().hex
            temp_file_path = f"temp_uploads/{unique_id}_{uploaded_file.name}"
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(uploaded_file.getvalue())
            
            # Verify it's a CSV file
            file_type = detect_file_type(temp_file_path)
            
            if file_type != 'csv':
                st.error("Unsupported file format. Please upload a CSV file.")
                return
                
            # Show file type information
            st.info("CSV file detected. The system will extract transactions from the CSV data.")
            
            # Try to detect source from content
            detected_source = detect_source_from_header(temp_file_path)
            
            # Source selection
            source_options = ['wells_fargo', 'chase', 'bank_of_america', 'apple_pay', 'schwab']
            selected_source = st.selectbox(
                "Select financial institution", 
                source_options,
                index=source_options.index(detected_source) if detected_source in source_options else 0
            )
            
            # Show preview of the file
            st.subheader("File Preview")
            with st.spinner("Generating preview..."):
                preview = read_file_to_preview(temp_file_path)
                st.dataframe(preview)
                
            # Always set confirm_import to True for CSV files
            confirm_import = True
            
            # No need for page_numbers with CSV files
            page_numbers = None
            
            # Import button
            if st.button("Import Data") and confirm_import:
                with st.spinner("Importing and processing data..."):
                    try:
                        # Import, categorize, and save to database
                        df = import_statement(temp_file_path, selected_source, page_numbers=page_numbers)
                        
                        if df.empty:
                            st.error("No transactions were found in the file. Please check the file format and try again.")
                        else:
                            # Show import results
                            st.subheader("Import Results")
                            st.write(f"Imported {len(df)} transactions from {selected_source}")
                            
                            # Auto-categorize transactions
                            df = categorize_transactions(df)
                            
                            # Preview categorized data
                            st.subheader("Categorized Transactions")
                            # Format date for display
                            display_df = df.copy()
                            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                            display_df['amount'] = display_df['amount'].map('${:,.2f}'.format)
                            st.dataframe(display_df[['date', 'description', 'amount', 'category']])
                            
                            # Save to database
                            success = save_to_database(df, st.session_state.db_path)
                            
                            if success:
                                st.success("Data successfully imported and saved to database")
                                # Update transactions in session state
                                st.session_state.transactions = load_from_database(st.session_state.db_path)
                            else:
                                st.error("Error saving data to database")
                    except Exception as e:
                        st.error(f"Error during import: {str(e)}")
            elif st.button("Import Data") and not confirm_import:
                st.warning("Please confirm before importing.")
            
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    # Option to view existing data
    st.markdown("---")
    st.subheader("View Existing Data")
    
    if st.button("Show All Transactions"):
        transactions = load_from_database(st.session_state.db_path)
        
        if not transactions.empty:
            st.write(f"Total transactions: {len(transactions)}")
            
            # Format for display
            display_df = transactions.copy()
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            display_df['amount'] = display_df['amount'].map('${:,.2f}'.format)
            
            st.dataframe(display_df[['id', 'date', 'description', 'amount', 'category', 'source']])
        else:
            st.info("No transactions found in the database")

if __name__ == "__main__":
    main()

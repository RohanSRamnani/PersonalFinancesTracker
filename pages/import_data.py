import streamlit as st
import pandas as pd
import os
from utils.data_import import import_statement, detect_source_from_header, read_file_to_preview
from utils.categorization import categorize_transactions
from utils.database import save_to_database, load_from_database

st.set_page_config(
    page_title="Import Data - Personal Finance Tracker",
    page_icon="💰",
    layout="wide"
)

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
    """)
    
    # File upload
    uploaded_file = st.file_uploader("Upload statement CSV file", type=["csv"])
    
    if uploaded_file is not None:
        try:
            # Save uploaded file temporarily
            temp_file_path = f"temp_{uploaded_file.name}"
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(uploaded_file.getvalue())
            
            # Try to detect source from file headers
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
            preview = read_file_to_preview(temp_file_path)
            st.dataframe(preview)
            
            # Import button
            if st.button("Import Data"):
                with st.spinner("Importing and processing data..."):
                    # Import, categorize, and save to database
                    df = import_statement(temp_file_path, selected_source)
                    
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
            
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            if os.path.exists(temp_file_path):
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

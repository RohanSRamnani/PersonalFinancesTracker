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
    
    **Supported formats:** CSV and PDF files
    """)
    
    # File upload
    uploaded_file = st.file_uploader("Upload statement file", type=["csv", "pdf"])
    
    if uploaded_file is not None:
        try:
            # Save uploaded file temporarily
            temp_file_path = f"temp_{uploaded_file.name}"
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(uploaded_file.getvalue())
            
            # Detect file type
            file_type = detect_file_type(temp_file_path)
            
            if file_type == 'unknown':
                st.error("Unsupported file format. Please upload a CSV or PDF file.")
                return
                
            # Show file type information
            if file_type == 'csv':
                st.info("CSV file detected. The system will extract transactions from the CSV data.")
            elif file_type == 'pdf':
                st.info("PDF file detected. The system will attempt to extract tables and transaction data from the PDF.")
            
            # Try to detect source from file content
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
                
            # Add additional notes for PDF files
            if file_type == 'pdf':
                st.markdown("""
                **Note about PDF imports:** 
                - The system will attempt to automatically extract transaction tables from the PDF
                - The quality of extraction depends on the PDF's structure
                - For best results, use CSV files when available
                """)
                
            # Add option to confirm PDF parsing looks correct
            if file_type == 'pdf':
                st.warning("Please review the preview above. If it doesn't look like transaction data, try a different file format.")
                confirm_import = st.checkbox("The preview looks good, continue with import", value=True)
            else:
                confirm_import = True
            
            # Import button
            if st.button("Import Data") and confirm_import:
                with st.spinner("Importing and processing data..."):
                    try:
                        # Import, categorize, and save to database
                        df = import_statement(temp_file_path, selected_source)
                        
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
                        if file_type == 'pdf':
                            st.error("PDF extraction failed. The PDF format may not be compatible with our extraction tools. Try exporting to CSV instead.")
            elif st.button("Import Data") and not confirm_import:
                st.warning("Please confirm that the preview looks good by checking the box above.")
            
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

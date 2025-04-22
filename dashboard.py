import streamlit as st
import pandas as pd
import os
import uuid
from utils.database import load_from_database, check_db_exists, initialize_database, save_to_database
from utils.account_balance import get_account_balances, update_account_balance, get_total_balance
from utils.data_import import import_statement, detect_source_from_header, read_file_to_preview, detect_file_type
from utils.categorization import categorize_transactions, normalize_transaction_signs

st.set_page_config(
    page_title="Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Initialize session state for storing data across pages
    if 'transactions' not in st.session_state:
        st.session_state.transactions = None
    
    if 'db_path' not in st.session_state:
        st.session_state.db_path = 'finance_data.db'
    
    # Initialize database if it doesn't exist
    if not check_db_exists(st.session_state.db_path):
        initialize_database(st.session_state.db_path)
    
    # Title only, no subtitle text
    st.title("Dashboard")
    
    # Load transactions from database
    transactions = load_from_database(st.session_state.db_path)
    st.session_state.transactions = transactions
    
    # Display key financial metrics at the top
    # Get account balances
    account_balances = get_account_balances(st.session_state.db_path)
    
    # Calculate financial metrics
    if not transactions.empty:
        total_income = transactions[transactions['amount'] > 0]['amount'].sum()
        # Fix for numpy float64 objects not having abs() method
        total_expenses = abs(transactions[transactions['amount'] < 0]['amount'].sum())
        net_worth = total_income - total_expenses
        
        # Get the Wells Fargo balance from the account_balances table if it exists
        wells_fargo_balance = 0
        if not account_balances.empty:
            wells_fargo_row = account_balances[account_balances['account_name'] == 'Wells Fargo']
            if not wells_fargo_row.empty:
                wells_fargo_balance = wells_fargo_row.iloc[0]['balance']
            
        # If Wells Fargo balance is 0, approximate from transactions
        if wells_fargo_balance == 0:
            # Get bank account transactions (deposits/withdrawals) - approximating as non-credit card transactions
            bank_transactions = transactions[~transactions['description'].str.contains('card|credit|payment', case=False, na=False)]
            wells_fargo_balance = bank_transactions['amount'].sum()
        
        # Credit card related transactions - approximating based on descriptions
        credit_transactions = transactions[transactions['description'].str.contains('card|credit|payment', case=False, na=False)]
        credit_card_due = abs(credit_transactions[credit_transactions['amount'] < 0]['amount'].sum())
        
        # Calculate monthly change
        # Get current and previous month data
        current_month = pd.Timestamp.now().strftime('%Y-%m')
        current_month_mask = transactions['date'].dt.strftime('%Y-%m') == current_month
        current_month_net = transactions[current_month_mask]['amount'].sum()
        
        # Get previous month - approximating as 1 month before current
        prev_month = (pd.Timestamp.now() - pd.DateOffset(months=1)).strftime('%Y-%m')
        prev_month_mask = transactions['date'].dt.strftime('%Y-%m') == prev_month
        prev_month_net = transactions[prev_month_mask]['amount'].sum()
        
        # Calculate percent change if previous month had transactions
        if prev_month_net != 0:
            monthly_change_pct = ((current_month_net - prev_month_net) / abs(prev_month_net)) * 100
            monthly_change_str = f"{monthly_change_pct:.1f}%"
            
            # Determine if it's an increase or decrease for the delta color
            # Streamlit only accepts 'normal', 'inverse', or 'off' for delta_color
            delta_color = "normal"
            # We'll use 'normal' for positive changes and 'inverse' for negative
            if monthly_change_pct < 0:
                delta_color = "inverse"
        else:
            monthly_change_str = "N/A"
            delta_color = "normal"
        
        # Create a dashboard with key metrics
        st.subheader("Key Financial Metrics")
        
        # Top row for primary metrics
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        metric_col1.metric(
            "Net Worth", 
            f"${net_worth:,.2f}",
            monthly_change_str,
            delta_color=delta_color
        )
        
        # Get total balance from all accounts if available, otherwise show Wells Fargo balance
        if not account_balances.empty:
            total_account_balance = account_balances['balance'].sum()
            metric_col2.metric(
                "Bank Account Balance",
                f"${total_account_balance:,.2f}"
            )
        else:
            metric_col2.metric(
                "Wells Fargo Balance",
                f"${wells_fargo_balance:,.2f}"
            )
        
        metric_col3.metric(
            "Credit Card Payment Due",
            f"${credit_card_due:,.2f}"
        )
        
        metric_col4.metric(
            "Monthly Change",
            monthly_change_str,
            delta_color=delta_color
        )
        
        # Add a small section to edit Wells Fargo balance directly
        with st.expander("Update Balance"):
            st.caption("Update your Wells Fargo balance without going to the Accounts page")
            quick_balance_col1, quick_balance_col2 = st.columns([3, 1])
            with quick_balance_col1:
                new_wells_balance = st.number_input(
                    "Wells Fargo Balance", 
                    value=float(wells_fargo_balance), 
                    step=10.0,
                    format="%.2f"
                )
            with quick_balance_col2:
                if st.button("Update"):
                    if update_account_balance("Wells Fargo", new_wells_balance, st.session_state.db_path):
                        st.success("Wells Fargo balance updated!")
                        st.rerun()
                    else:
                        st.error("Failed to update balance")
    else:
        st.info("Import your financial data to see your financial metrics and insights.")
        
    # Recent transactions and financial overview in two columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Transactions")
        if not transactions.empty:
            recent = transactions.sort_values('date', ascending=False).head(5)
            # Format the dataframe for display - using .loc to avoid SettingWithCopyWarning
            recent_display = recent[['date', 'description', 'amount', 'category']].copy()
            recent_display.loc[:, 'date'] = recent_display['date'].dt.strftime('%Y-%m-%d')
            recent_display.loc[:, 'amount'] = recent_display['amount'].map('${:,.2f}'.format)
            st.dataframe(recent_display, use_container_width=True)
        else:
            st.info("No transactions found. Import your financial data to get started.")
    
    with col2:
        st.subheader("Financial Overview")
        if not transactions.empty:
            # Calculate more detailed metrics
            total_income = transactions[transactions['amount'] > 0]['amount'].sum()
            total_expenses = abs(transactions[transactions['amount'] < 0]['amount'].sum())
            balance = total_income - total_expenses
            
            # Current month stats
            current_month = pd.Timestamp.now().strftime('%Y-%m')
            current_month_mask = transactions['date'].dt.strftime('%Y-%m') == current_month
            current_month_expenses = abs(transactions[current_month_mask & (transactions['amount'] < 0)]['amount'].sum())
            current_month_income = transactions[current_month_mask & (transactions['amount'] > 0)]['amount'].sum()
            
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            
            metrics_col1.metric("Total Income", f"${total_income:,.2f}")
            metrics_col2.metric("Total Expenses", f"${total_expenses:,.2f}")
            metrics_col3.metric("Balance", f"${balance:,.2f}")
            
            # Monthly metrics
            month_col1, month_col2 = st.columns(2)
            month_col1.metric("Current Month Income", f"${current_month_income:,.2f}")
            month_col2.metric("Current Month Expenses", f"${current_month_expenses:,.2f}")
        else:
            st.info("Import your financial data to see an overview of your finances.")
    
    # No welcome message or instructions as requested
    
    # Import Data section
    st.subheader("Import Data")
    
    # Create temp_uploads directory if it doesn't exist
    if not os.path.exists('temp_uploads'):
        os.makedirs('temp_uploads', exist_ok=True)
        # Set permissions to ensure we can write files
        try:
            os.chmod('temp_uploads', 0o777)
        except:
            pass
    
    # Import Data functionality
    with st.expander("Import your financial statements"):
        # Instructions
        st.markdown("""
        Upload your financial statements to import them into the system. 
        The app supports statements from:
        - Wells Fargo
        - Chase
        - Bank of America
        - Apple Pay
        - Schwab
        
        **Supported formats:** Excel (XLSX) files
        """)
        
        # File upload - Excel only
        uploaded_file = st.file_uploader("Upload statement file", type=["xlsx", "xls"])
        
        # Initialize temp_file_path outside of try/except blocks to avoid unbound variable issues
        temp_file_path = None
        
        if uploaded_file is not None:
            try:
                # Save uploaded file temporarily
                # Generate a unique ID to avoid name conflicts
                unique_id = uuid.uuid4().hex
                temp_file_path = f"temp_uploads/{unique_id}_{uploaded_file.name}"
                with open(temp_file_path, "wb") as temp_file:
                    temp_file.write(uploaded_file.getvalue())
                
                # Verify it's an Excel file
                file_type = detect_file_type(temp_file_path)
                
                if file_type not in ['xlsx', 'xls']:
                    st.error("Unsupported file format. Please upload an Excel (XLSX/XLS) file.")
                else:
                    # Show file type information
                    st.info("Excel file detected. The system will extract transactions from the Excel data.")
                    
                    # Try to detect source from content
                    detected_source = detect_source_from_header(temp_file_path)
                    
                    # Source selection
                    source_options = ['wells_fargo', 'chase', 'bank_of_america', 'apple_pay', 'schwab']
                    selected_source = st.selectbox(
                        "Select financial institution", 
                        source_options,
                        index=source_options.index(detected_source) if detected_source in source_options else 0
                    )
                    
                    # Add support for selecting Excel sheets
                    sheet_name = None
                    
                    try:
                        # Get list of sheet names
                        excel_file = pd.ExcelFile(temp_file_path)
                        all_sheets = excel_file.sheet_names
                        
                        if len(all_sheets) > 1:
                            sheet_name = st.selectbox("Select sheet with transaction data:", all_sheets)
                        else:
                            # Use the first sheet if there's only one
                            sheet_name = all_sheets[0] if all_sheets else None
                            
                        # Show preview of the file with selected sheet
                        st.subheader("File Preview")
                        with st.spinner("Generating preview..."):
                            preview = read_file_to_preview(temp_file_path, sheet_name=sheet_name)
                            st.dataframe(preview)
                    except Exception as e:
                        st.error(f"Error reading Excel file: {str(e)}")
                        
                    # Import button
                    if st.button("Import Data"):
                        with st.spinner("Importing and processing data..."):
                            try:
                                # Import, categorize, and save to database
                                df = import_statement(temp_file_path, selected_source, sheet_name=sheet_name)
                                
                                if df.empty:
                                    st.error("No transactions were found in the file. Please check the file format and try again.")
                                else:
                                    # Show import results
                                    st.subheader("Import Results")
                                    st.write(f"Imported {len(df)} transactions from {selected_source}")
                                    
                                    # Auto-categorize transactions
                                    df = categorize_transactions(df)
                                    
                                    # Normalize transaction signs (income positive, expenses negative)
                                    df = normalize_transaction_signs(df)
                                    
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
                                        st.rerun()  # Refresh the page to show updated data
                                    else:
                                        st.error("Error saving data to database")
                            except Exception as e:
                                st.error(f"Error during import: {str(e)}")
                
                # Clean up temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
    # Option to view existing data
    with st.expander("View All Transactions"):
        if st.button("Show All Transactions"):
            transactions = load_from_database(st.session_state.db_path)
            
            if not transactions.empty:
                st.write(f"Total transactions: {len(transactions)}")
                
                # Format for display
                display_df = transactions.copy()
                display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                display_df['amount'] = display_df['amount'].map('${:,.2f}'.format)
                
                st.dataframe(display_df[['id', 'date', 'description', 'amount', 'category', 'source']])

if __name__ == "__main__":
    main()

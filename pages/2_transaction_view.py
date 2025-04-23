import streamlit as st
import pandas as pd
from utils.database import load_from_database, delete_transaction, update_transaction, delete_transactions_by_source, reindex_transactions_by_date
from utils.categorization import get_category_list
import datetime
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(
    page_title="Transactions - Personal Finance Tracker",
    page_icon="💰",
    layout="wide"
)

st.title("Transaction View")

# Initialize database path in session state if not already there
if 'db_path' not in st.session_state:
    st.session_state.db_path = 'finance_data.db'

def main():
    # Load all transactions
    transactions = load_from_database(st.session_state.db_path)
    
    if transactions.empty:
        st.info("No transactions found. Import your financial data first.")
        return
    
    # Date filter
    st.sidebar.header("Filter Options")
    
    # Get min and max dates from transactions
    min_date = transactions['date'].min().date()
    max_date = transactions['date'].max().date()
    
    # Date range selector
    start_date = st.sidebar.date_input("Start Date", min_date)
    end_date = st.sidebar.date_input("End Date", max_date)
    
    # Convert to pandas datetime
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)
    
    # Filter by date
    filtered_transactions = transactions[(transactions['date'] >= start_date) & 
                                       (transactions['date'] <= end_date)]
    
    # Category filter
    categories = ['All Categories'] + sorted(filtered_transactions['category'].unique().tolist())
    selected_category = st.sidebar.selectbox("Category", categories)
    
    if selected_category != 'All Categories':
        filtered_transactions = filtered_transactions[filtered_transactions['category'] == selected_category]
    
    # Source filter
    sources = ['All Sources'] + sorted(filtered_transactions['source'].unique().tolist())
    selected_source = st.sidebar.selectbox("Source", sources)
    
    if selected_source != 'All Sources':
        filtered_transactions = filtered_transactions[filtered_transactions['source'] == selected_source]
    
    # Amount filter
    min_amount = float(transactions['amount'].min())
    max_amount = float(transactions['amount'].max())
    
    # Calculate an appropriate step size based on the range
    range_size = max_amount - min_amount
    # Make step size proportional to the range, with a minimum of 0.01
    step_size = max(0.01, range_size / 100.0) 
    # Round to a nice value, but ensure it's a float
    if step_size > 1:
        step_size = float(round(step_size))
    else:
        step_size = round(step_size * 100) / 100.0  # Round to 2 decimal places, explicitly as float
    
    amount_range = st.sidebar.slider(
        "Amount Range", 
        min_value=min_amount,
        max_value=max_amount,
        value=(min_amount, max_amount),
        step=step_size
    )
    
    filtered_transactions = filtered_transactions[
        (filtered_transactions['amount'] >= amount_range[0]) & 
        (filtered_transactions['amount'] <= amount_range[1])
    ]
    
    # Description search
    search_term = st.sidebar.text_input("Search Description")
    
    if search_term:
        filtered_transactions = filtered_transactions[
            filtered_transactions['description'].str.contains(search_term, case=False)
        ]
    
    # Display filtered transactions
    st.markdown(f"### Transactions ({len(filtered_transactions)} records)")
    
    # Sort by date
    filtered_transactions = filtered_transactions.sort_values('date', ascending=False)
    
    # Create a copy of the dataframe for display with formatted columns
    display_df = filtered_transactions.copy()
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
    display_df['amount'] = display_df['amount'].map('${:,.2f}'.format)
    
    # Pagination
    # Convert all values to float to ensure type consistency
    rows_per_page = st.slider("Rows per page", 
                           min_value=float(10), 
                           max_value=float(100), 
                           value=float(20), 
                           step=float(10))  # All values must be the same type
    total_pages = (len(filtered_transactions) - 1) // rows_per_page + 1
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    def set_page(page_num):
        st.session_state.current_page = page_num
    
    # Pagination controls
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("Previous"):
            if st.session_state.current_page > 1:
                set_page(st.session_state.current_page - 1)
    
    with col2:
        if total_pages > 1:
            # Create page numbers that are valid with the slider constraints
            # Instead of using options, use min_value, max_value, and value directly
            # Convert all values to float to ensure type consistency
            page_num = st.slider("Page", 
                              min_value=float(1), 
                              max_value=float(total_pages), 
                              value=float(st.session_state.current_page), 
                              step=1.0)  # Use float for step
            if page_num != st.session_state.current_page:
                set_page(page_num)
    
    with col3:
        if st.button("Next"):
            if st.session_state.current_page < total_pages:
                set_page(st.session_state.current_page + 1)
    
    # Calculate start and end indices for pagination
    start_idx = (st.session_state.current_page - 1) * rows_per_page
    end_idx = min(start_idx + rows_per_page, len(filtered_transactions))
    
    # Display paginated transactions
    # Set the ID as the index but don't show it as a column
    display_subset = display_df.iloc[start_idx:end_idx].copy()
    
    # Format amount with dollar sign for display if it's not already a string
    if not pd.api.types.is_string_dtype(display_subset['amount']):
        display_subset['amount'] = display_subset['amount'].apply(lambda x: f"${x:,.2f}")
    
    # Set index to ID
    display_subset = display_subset.set_index('id')
    display_subset.index.name = 'ID'  # Rename the index
    
    # Format date as string to avoid data type compatibility issues
    display_subset_formatted = display_subset.copy()
    # Convert date column to string if it's a datetime
    if pd.api.types.is_datetime64_any_dtype(display_subset_formatted['date']):
        display_subset_formatted['date'] = display_subset_formatted['date'].dt.strftime('%Y-%m-%d')
    
    # Reset index to make ID a column for AgGrid
    display_subset = display_subset.reset_index()
    
    # Configure AgGrid options
    gb = GridOptionsBuilder.from_dataframe(display_subset[['ID', 'date', 'description', 'amount', 'category', 'source']])
    
    # Enable filtering for all columns
    gb.configure_default_column(
        filterable=True,
        resizable=True,
        sorteable=True,
        editable=False
    )
    
    # Customize specific columns
    gb.configure_column('ID', width=70)
    gb.configure_column('date', width=110)
    gb.configure_column('description', width=250, filter=True)
    gb.configure_column('amount', width=110)
    gb.configure_column('category', width=150, filter=True)
    gb.configure_column('source', width=150, filter=True)
    
    # Configure pagination
    gb.configure_pagination(enabled=True, paginationPageSize=rows_per_page)
    
    # Configure grid options
    gridOptions = gb.build()
    
    # No info text as requested
    
    # Create the AgGrid component
    AgGrid(
        display_subset,
        gridOptions=gridOptions,
        fit_columns_on_grid_load=False,
        height=400,
        enable_enterprise_modules=False,
        theme="streamlit",
        allow_unsafe_jscode=True
    )
    
    # Edit transaction section
    st.markdown("---")
    
    # Create columns for edit and delete sections
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Edit Transaction")
        
        # Create tabs for different ways to find transactions to edit
        edit_tabs = st.tabs(["Edit by ID", "Search and Edit"])
        
        with edit_tabs[0]:
            # EDIT BY ID TAB
            edit_id = st.number_input("Enter Transaction ID to Edit", min_value=1, step=1)
        
            if edit_id:
                # Find transaction in dataframe
                transaction = transactions[transactions['id'] == edit_id]
                
                if not transaction.empty:
                    transaction = transaction.iloc[0]
                    
                    st.write("**Current Values:**")
                    st.write(f"Date: {transaction['date'].strftime('%Y-%m-%d')}")
                    st.write(f"Description: {transaction['description']}")
                    st.write(f"Amount: ${transaction['amount']:.2f}")
                    st.write(f"Category: {transaction['category']}")
                    st.write(f"Source: {transaction['source']}")
                    
                    # Edit form
                    edit_category = st.selectbox("New Category", get_category_list(), 
                                                index=get_category_list().index(transaction['category']) 
                                                if transaction['category'] in get_category_list() else 0)
                    edit_description = st.text_input("New Description", transaction['description'])
                    
                    # Amount section with sign toggle
                    amount_col1, amount_col2 = st.columns([3, 1])
                    with amount_col1:
                        # Always show the absolute value in the input field for easier editing
                        abs_amount = abs(float(transaction['amount']))
                        edit_amount = st.number_input("New Amount", value=abs_amount, min_value=0.0, step=0.01)
                    
                    with amount_col2:
                        # Determine if current value is income, payment or expense
                        is_positive = transaction['amount'] > 0
                        # Default to Income for positive amounts, Expense for negative
                        transaction_type = st.radio(
                            "Type",
                            ["Income", "Payment", "Expense"],
                            index=0 if is_positive else 2,
                            help="Income and Payment will be stored as positive values, expenses as negative"
                        )
                        # Apply sign based on transaction type
                        if transaction_type == "Expense":
                            final_amount = -edit_amount
                        else:
                            # Both Income and Payment are positive
                            final_amount = edit_amount
                    
                    edit_date = st.date_input("New Date", transaction['date'])
                    
                    # Display the final amount with sign
                    st.info(f"Final amount: ${final_amount:.2f} ({'positive' if final_amount > 0 else 'negative'})")
                    
                    if st.button("Update Transaction", key="update_by_id"):
                        # Update each field if changed
                        if edit_category != transaction['category']:
                            update_transaction(edit_id, 'category', edit_category, st.session_state.db_path)
                        
                        if edit_description != transaction['description']:
                            update_transaction(edit_id, 'description', edit_description, st.session_state.db_path)
                        
                        if final_amount != float(transaction['amount']):
                            update_transaction(edit_id, 'amount', final_amount, st.session_state.db_path)
                        
                        if pd.Timestamp(edit_date) != transaction['date'].date():
                            update_transaction(edit_id, 'date', edit_date.strftime('%Y-%m-%d'), st.session_state.db_path)
                        
                        st.success(f"Transaction {edit_id} updated successfully")
                        st.rerun()
                else:
                    st.error(f"No transaction found with ID {edit_id}")
        
        with edit_tabs[1]:
            # SEARCH AND EDIT TAB
            st.subheader("Search for Transactions to Edit")
            
            # Search options
            search_col1, search_col2 = st.columns(2)
            
            with search_col1:
                search_description = st.text_input("Search by Description", 
                                                placeholder="Enter keywords (e.g., 'Amazon', 'Coffee')")
                
            with search_col2:
                search_category = st.selectbox("Filter by Category", 
                                            ["All Categories"] + sorted(transactions['category'].unique().tolist()))
                
            # Additional search filters if needed
            search_col3, search_col4 = st.columns(2)
            
            with search_col3:
                search_source = st.selectbox("Filter by Source", 
                                           ["All Sources"] + sorted(transactions['source'].unique().tolist()))
                
            with search_col4:
                search_type = st.selectbox("Filter by Type", 
                                         ["All Types", "Income/Payment (Positive)", "Expense (Negative)"])
            
            # Apply filters to find matching transactions
            search_results = transactions.copy()
            
            # Filter by description if provided
            if search_description:
                search_results = search_results[
                    search_results['description'].str.contains(search_description, case=False)
                ]
                
            # Filter by category if selected
            if search_category != "All Categories":
                search_results = search_results[search_results['category'] == search_category]
                
            # Filter by source if selected
            if search_source != "All Sources":
                search_results = search_results[search_results['source'] == search_source]
                
            # Filter by transaction type (positive/negative) if selected
            if search_type == "Income/Payment (Positive)":
                search_results = search_results[search_results['amount'] > 0]
            elif search_type == "Expense (Negative)":
                search_results = search_results[search_results['amount'] < 0]
            
            # Display search results
            if len(search_results) > 0:
                st.write(f"Found {len(search_results)} matching transactions")
                
                # Create a copy for display formatting
                display_results = search_results.copy()
                display_results['date'] = display_results['date'].dt.strftime('%Y-%m-%d')
                
                # Format amount with dollar sign for display if it's not already a string
                if not pd.api.types.is_string_dtype(display_results['amount']):
                    display_results['amount'] = display_results['amount'].apply(lambda x: f"${x:,.2f}")
                
                # Rename id column to ID for AgGrid
                display_results = display_results.rename(columns={'id': 'ID'})
                
                # Configure AgGrid options for search results
                gb_search = GridOptionsBuilder.from_dataframe(display_results[['ID', 'date', 'description', 'amount', 'category', 'source']])
                
                # Enable filtering for all columns
                gb_search.configure_default_column(
                    filterable=True,
                    resizable=True,
                    sorteable=True,
                    editable=False
                )
                
                # Customize specific columns
                gb_search.configure_column('ID', width=70)
                gb_search.configure_column('date', width=110)
                gb_search.configure_column('description', width=250, filter=True)
                gb_search.configure_column('amount', width=110)
                gb_search.configure_column('category', width=150, filter=True)
                gb_search.configure_column('source', width=150, filter=True)
                
                # Configure pagination
                gb_search.configure_pagination(enabled=True, paginationPageSize=10)
                
                # Configure grid options
                gridOptions_search = gb_search.build()
                
                # No info text as requested
                
                # Create the AgGrid component for search results
                AgGrid(
                    display_results,
                    gridOptions=gridOptions_search,
                    fit_columns_on_grid_load=False,
                    height=300,
                    enable_enterprise_modules=False,
                    theme="streamlit",
                    allow_unsafe_jscode=True
                )
                
                # Selection for which transaction to edit
                selected_id = st.selectbox("Select Transaction ID to Edit", 
                                         options=search_results['id'].tolist(),
                                         format_func=lambda x: f"ID {x} - {search_results[search_results['id'] == x]['description'].values[0][:40]}")
                
                if selected_id:
                    # Get the selected transaction
                    transaction = transactions[transactions['id'] == selected_id].iloc[0]
                    
                    st.write("**Edit Selected Transaction:**")
                    st.write(f"Date: {transaction['date'].strftime('%Y-%m-%d')}")
                    st.write(f"Description: {transaction['description']}")
                    st.write(f"Amount: ${transaction['amount']:.2f}")
                    
                    # Edit form for the selected transaction
                    edit_category = st.selectbox("New Category", get_category_list(), 
                                               index=get_category_list().index(transaction['category']) 
                                               if transaction['category'] in get_category_list() else 0,
                                               key="search_edit_category")
                    edit_description = st.text_input("New Description", transaction['description'], key="search_edit_desc")
                    
                    # Amount section with sign toggle
                    amount_col1, amount_col2 = st.columns([3, 1])
                    with amount_col1:
                        abs_amount = abs(float(transaction['amount']))
                        edit_amount = st.number_input("New Amount", value=abs_amount, min_value=0.0, step=0.01, 
                                                    key="search_edit_amount")
                    
                    with amount_col2:
                        is_positive = transaction['amount'] > 0
                        transaction_type = st.radio(
                            "Type",
                            ["Income", "Payment", "Expense"],
                            index=0 if is_positive else 2,
                            help="Income and Payment will be stored as positive values, expenses as negative",
                            key="search_edit_type"
                        )
                        # Apply sign based on transaction type
                        if transaction_type == "Expense":
                            final_amount = -edit_amount
                        else:
                            # Both Income and Payment are positive
                            final_amount = edit_amount
                    
                    edit_date = st.date_input("New Date", transaction['date'], key="search_edit_date")
                    
                    # Display the final amount with sign
                    st.info(f"Final amount: ${final_amount:.2f} ({'positive' if final_amount > 0 else 'negative'})")
                    
                    if st.button("Update Transaction", key="update_from_search"):
                        # Update each field if changed
                        if edit_category != transaction['category']:
                            update_transaction(selected_id, 'category', edit_category, st.session_state.db_path)
                        
                        if edit_description != transaction['description']:
                            update_transaction(selected_id, 'description', edit_description, st.session_state.db_path)
                        
                        if final_amount != float(transaction['amount']):
                            update_transaction(selected_id, 'amount', final_amount, st.session_state.db_path)
                        
                        if pd.Timestamp(edit_date) != transaction['date'].date():
                            update_transaction(selected_id, 'date', edit_date.strftime('%Y-%m-%d'), st.session_state.db_path)
                        
                        st.success(f"Transaction {selected_id} updated successfully")
                        st.rerun()
            else:
                st.info("No transactions found matching your search criteria")
    
    with col2:
        # Delete transaction section
        st.subheader("Delete Transaction")
        
        delete_id = st.number_input("Enter Transaction ID to Delete", min_value=1, step=1, key="delete_id")
        
        if delete_id:
            # Find transaction in dataframe
            transaction = transactions[transactions['id'] == delete_id]
            
            if not transaction.empty:
                transaction = transaction.iloc[0]
                
                st.write("**Transaction to Delete:**")
                st.write(f"Date: {transaction['date'].strftime('%Y-%m-%d')}")
                st.write(f"Description: {transaction['description']}")
                st.write(f"Amount: ${transaction['amount']:.2f}")
                st.write(f"Category: {transaction['category']}")
                
                if st.button("Delete Transaction", key="delete_button"):
                    if delete_transaction(delete_id, st.session_state.db_path):
                        st.success(f"Transaction {delete_id} deleted successfully")
                        st.rerun()
                    else:
                        st.error("Error deleting transaction")
            else:
                st.error(f"No transaction found with ID {delete_id}")
        
        # Add a section for bulk deletion by source
        st.markdown("---")
        st.subheader("Bulk Delete by Source")
        
        # Get unique sources for the dropdown
        all_sources = sorted(transactions['source'].unique().tolist())
        
        if all_sources:
            bulk_delete_source = st.selectbox(
                "Select Source to Delete All Transactions From", 
                all_sources,
                key="bulk_delete_source"
            )
            
            # Show information about how many transactions will be deleted
            source_count = len(transactions[transactions['source'] == bulk_delete_source])
            st.warning(f"This will delete ALL {source_count} transactions from '{bulk_delete_source}'.")
            
            # Require confirmation
            confirm_delete = st.checkbox("I understand this action cannot be undone")
            
            if st.button("Delete All Transactions from Source", key="bulk_delete_button") and confirm_delete:
                count = delete_transactions_by_source(bulk_delete_source, st.session_state.db_path)
                if count > 0:
                    st.success(f"Successfully deleted {count} transactions from {bulk_delete_source}")
                    st.rerun()
                else:
                    st.error(f"Error deleting transactions from {bulk_delete_source}")
            elif st.button("Delete All Transactions from Source", key="bulk_delete_button_no_confirm") and not confirm_delete:
                st.error("Please confirm the deletion by checking the box above")
                
        # Add a section for reindexing transactions by date
        st.markdown("---")
        st.subheader("Reindex Transactions by Date")
        
        st.info("""
        This will reorder all transactions by date (oldest first) and reset transaction IDs 
        to be sequential, starting from 1. This is useful if you want transaction IDs to match
        the chronological order of your transactions.
        """)
        
        # Require confirmation for reindexing
        confirm_reindex = st.checkbox("I understand this will change all transaction IDs", key="confirm_reindex")
        
        if st.button("Reindex All Transactions by Date") and confirm_reindex:
            if reindex_transactions_by_date(st.session_state.db_path):
                st.success("Successfully reindexed all transactions by date")
                st.rerun()
            else:
                st.error("Error reindexing transactions")

if __name__ == "__main__":
    main()

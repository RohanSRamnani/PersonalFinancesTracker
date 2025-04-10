import streamlit as st
import pandas as pd
from utils.database import load_from_database, delete_transaction, update_transaction, delete_transactions_by_source, reindex_transactions_by_date
from utils.categorization import get_category_list
import datetime

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
    
    amount_range = st.sidebar.slider(
        "Amount Range", 
        min_value=min_amount,
        max_value=max_amount,
        value=(min_amount, max_amount),
        step=10.0
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
    rows_per_page = st.slider("Rows per page", min_value=10, max_value=100, value=20, step=10)
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
        page_nums = [i+1 for i in range(total_pages)]
        if total_pages > 1:
            page_num = st.select_slider("Page", options=page_nums, value=st.session_state.current_page)
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
    display_subset = display_subset.set_index('id')
    display_subset.index.name = 'ID'  # Rename the index
    st.dataframe(display_subset[['date', 'description', 'amount', 'category', 'source']], use_container_width=True)
    
    # Edit transaction section
    st.markdown("---")
    st.subheader("Edit Transaction")
    
    col1, col2 = st.columns(2)
    
    with col1:
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
                edit_category = st.selectbox("New Category", get_category_list(), index=get_category_list().index(transaction['category']) if transaction['category'] in get_category_list() else 0)
                edit_description = st.text_input("New Description", transaction['description'])
                edit_amount = st.number_input("New Amount", value=float(transaction['amount']), step=0.01)
                edit_date = st.date_input("New Date", transaction['date'])
                
                if st.button("Update Transaction"):
                    # Update each field if changed
                    if edit_category != transaction['category']:
                        update_transaction(edit_id, 'category', edit_category, st.session_state.db_path)
                    
                    if edit_description != transaction['description']:
                        update_transaction(edit_id, 'description', edit_description, st.session_state.db_path)
                    
                    if edit_amount != transaction['amount']:
                        update_transaction(edit_id, 'amount', edit_amount, st.session_state.db_path)
                    
                    if pd.Timestamp(edit_date) != transaction['date'].date():
                        update_transaction(edit_id, 'date', edit_date.strftime('%Y-%m-%d'), st.session_state.db_path)
                    
                    st.success(f"Transaction {edit_id} updated successfully")
                    st.rerun()
            else:
                st.error(f"No transaction found with ID {edit_id}")
    
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

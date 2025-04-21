import streamlit as st
import pandas as pd
from utils.categorization import (
    get_category_list, get_custom_categories, add_custom_category, 
    delete_custom_category
)
from utils.database import load_from_database, update_transaction

st.set_page_config(
    page_title="Manage Categories - Personal Finance Tracker",
    page_icon="🏷️",
    layout="wide"
)

st.title("Manage Categories")

# Initialize database path in session state if not already there
if 'db_path' not in st.session_state:
    st.session_state.db_path = 'finance_data.db'

def main():
    # Get all categories and separate standard from custom
    all_categories = get_category_list(st.session_state.db_path)
    custom_categories = get_custom_categories(st.session_state.db_path)
    
    # Standard categories are those in all_categories but not in custom_categories
    standard_categories = [cat for cat in all_categories if cat not in custom_categories]
    
    # Create two columns layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Add New Category")
        
        # Form for adding a new category
        with st.form("add_category_form"):
            new_category = st.text_input("New Category Name", placeholder="e.g., 'Hobbies', 'Pet Expenses'")
            submit_button = st.form_submit_button("Add Category")
            
            if submit_button and new_category:
                if add_custom_category(new_category, st.session_state.db_path):
                    st.success(f"Category '{new_category}' added successfully!")
                    st.rerun()
                else:
                    if new_category in all_categories:
                        st.error(f"Category '{new_category}' already exists.")
                    else:
                        st.error("Failed to add category. Please try again.")
        
        # Show statistics about category usage
        st.subheader("Category Statistics")
        
        # Load transactions to analyze category distribution
        transactions = load_from_database(st.session_state.db_path)
        
        if not transactions.empty:
            # Count transactions per category
            category_counts = transactions['category'].value_counts()
            
            # Create DataFrame for display
            category_stats = pd.DataFrame({
                'Category': category_counts.index,
                'Transactions': category_counts.values
            })
            
            # Display as a table
            st.dataframe(category_stats, use_container_width=True)
            
            # Show percentage of transactions without categories
            uncategorized = transactions[transactions['category'].isin(['Uncategorized', 'Miscellaneous'])].shape[0]
            total = transactions.shape[0]
            
            if total > 0:
                st.caption(f"**{uncategorized / total * 100:.1f}%** of transactions are uncategorized or miscellaneous.")
        else:
            st.info("No transactions found in the database.")
    
    with col2:
        st.subheader("Manage Existing Categories")
        
        # Display standard categories (read-only)
        st.write("**Standard Categories:**")
        standard_cats_df = pd.DataFrame({'Category': standard_categories})
        st.dataframe(standard_cats_df, use_container_width=True)
        
        # Display custom categories with delete option
        if custom_categories:
            st.write("**Custom Categories:**")
            
            # Create a DataFrame with custom categories
            custom_cats_df = pd.DataFrame({'Category': custom_categories})
            st.dataframe(custom_cats_df, use_container_width=True)
            
            # Option to delete a custom category
            category_to_delete = st.selectbox(
                "Select Category to Delete", 
                options=custom_categories
            )
            
            if st.button("Delete Selected Category"):
                # Check if this category is used in any transaction
                category_used = False
                if not transactions.empty:
                    category_used = transactions[transactions['category'] == category_to_delete].shape[0] > 0
                
                if category_used:
                    st.warning(f"Category '{category_to_delete}' is currently used in transactions. Deleting will change these transactions to 'Miscellaneous'.")
                    
                    # Option to proceed with reclassification
                    if st.button("Proceed with Deletion and Reclassify Transactions"):
                        # First update all transactions with this category to Miscellaneous
                        transactions_to_update = transactions[transactions['category'] == category_to_delete]
                        
                        for idx, transaction in transactions_to_update.iterrows():
                            update_transaction(transaction['id'], 'category', 'Miscellaneous', st.session_state.db_path)
                        
                        # Then delete the category
                        if delete_custom_category(category_to_delete, st.session_state.db_path):
                            st.success(f"Category '{category_to_delete}' deleted and {len(transactions_to_update)} transactions reclassified.")
                            st.rerun()
                        else:
                            st.error("Failed to delete category. Please try again.")
                else:
                    # Not used in any transaction, can delete directly
                    if delete_custom_category(category_to_delete, st.session_state.db_path):
                        st.success(f"Category '{category_to_delete}' deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete category. Please try again.")
        else:
            st.info("No custom categories have been added yet.")
        
        # Bulk category replacement tool
        st.subheader("Bulk Category Replacement")
        st.write("Change all transactions from one category to another.")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            old_category = st.selectbox("From Category", all_categories, key="old_cat")
        
        with col_b:
            new_category = st.selectbox("To Category", all_categories, key="new_cat")
        
        if st.button("Replace Categories"):
            if old_category == new_category:
                st.error("The source and destination categories must be different.")
            else:
                # Count how many transactions will be affected
                if not transactions.empty:
                    affected_transactions = transactions[transactions['category'] == old_category]
                    count = len(affected_transactions)
                    
                    if count > 0:
                        # Confirm the replacement
                        st.warning(f"This will change {count} transactions from '{old_category}' to '{new_category}'.")
                        
                        if st.button("Confirm Replacement"):
                            # Update each transaction
                            for idx, transaction in affected_transactions.iterrows():
                                update_transaction(transaction['id'], 'category', new_category, st.session_state.db_path)
                            
                            st.success(f"Successfully replaced {count} transactions from '{old_category}' to '{new_category}'.")
                            st.rerun()
                    else:
                        st.info(f"No transactions found with category '{old_category}'.")

if __name__ == "__main__":
    main()
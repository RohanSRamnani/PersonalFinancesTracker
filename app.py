import streamlit as st
import pandas as pd
import os
from utils.database import load_from_database, check_db_exists, initialize_database

st.set_page_config(
    page_title="Personal Finance Tracker",
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
    
    # Title and description
    st.title("Personal Finance Tracker")
    st.markdown("""
    Analyze your spending habits, create budgets, and visualize your financial journey all in one place.
    """)
    
    # Load transactions from database
    transactions = load_from_database(st.session_state.db_path)
    st.session_state.transactions = transactions
    
    # Display summary dashboard
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Transactions")
        if not transactions.empty:
            recent = transactions.sort_values('date', ascending=False).head(5)
            # Format the dataframe for display
            recent_display = recent[['date', 'description', 'amount', 'category']]
            recent_display['date'] = recent_display['date'].dt.strftime('%Y-%m-%d')
            recent_display['amount'] = recent_display['amount'].map('${:,.2f}'.format)
            st.dataframe(recent_display, use_container_width=True)
        else:
            st.info("No transactions found. Import your financial data to get started.")
    
    with col2:
        st.subheader("Financial Overview")
        if not transactions.empty:
            # Calculate key financial metrics
            total_income = transactions[transactions['amount'] > 0]['amount'].sum()
            total_expenses = transactions[transactions['amount'] < 0]['amount'].sum().abs()
            balance = total_income - total_expenses
            
            # Current month stats
            current_month = pd.Timestamp.now().strftime('%Y-%m')
            current_month_mask = transactions['date'].dt.strftime('%Y-%m') == current_month
            current_month_expenses = transactions[current_month_mask & (transactions['amount'] < 0)]['amount'].sum().abs()
            
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            
            metrics_col1.metric("Total Income", f"${total_income:,.2f}")
            metrics_col2.metric("Total Expenses", f"${total_expenses:,.2f}")
            metrics_col3.metric("Balance", f"${balance:,.2f}")
            
            st.metric("Current Month Expenses", f"${current_month_expenses:,.2f}")
        else:
            st.info("Import your financial data to see an overview of your finances.")
    
    # Navigation instructions
    if transactions.empty:
        # Display welcome message for new users
        st.markdown("""
        ## How to Use This App
        
        1. **Import Data**: Upload financial statements from Wells Fargo, Chase, Bank of America, Apple Pay, or Schwab
        2. **Categorize Transactions**: The app will automatically categorize your transactions based on descriptions
        3. **Analyze Spending**: Visualize your spending patterns by category and over time
        4. **Create Budgets**: Set up budgets and track your actual spending against them
        """)
    
    st.markdown("""
    ## Get Started
    
    Use the sidebar navigation to:
    - Import financial statements
    - View and edit transactions
    - Analyze your spending patterns
    - Create and track budgets
    """)

if __name__ == "__main__":
    main()

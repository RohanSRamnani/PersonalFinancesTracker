import streamlit as st
import pandas as pd
import os
from utils.database import load_from_database, check_db_exists, initialize_database
from utils.account_balance import get_account_balances, update_account_balance, get_total_balance

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
    
    # Title and description
    st.title("Dashboard")
    st.markdown("""
    Your complete financial picture in one place. Track spending, budget, and measure progress over time.
    """)
    
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
    
    # Quick links for easy navigation
    st.subheader("Quick Navigation")
    
    # Create a horizontal layout for the links
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Spending Analysis", use_container_width=True):
            st.switch_page("pages/1_spending_analysis.py")
        if st.button("🏦 Manage Accounts", use_container_width=True):
            st.switch_page("pages/4_accounts.py")
    
    with col2:
        if st.button("📝 View Transactions", use_container_width=True):
            st.switch_page("pages/2_transaction_view.py")
        if st.button("📥 Import Data", use_container_width=True):
            st.switch_page("pages/5_import_data.py")
    
    with col3:
        if st.button("💰 Budgeting", use_container_width=True):
            st.switch_page("pages/3_budgeting.py")
        if st.button("🏷️ Manage Categories", use_container_width=True):
            st.switch_page("pages/6_manage_categories.py")
    
    st.markdown("""
    ## Get Started
    
    Use the sidebar navigation to:
    - Import financial statements
    - View and edit transactions
    - Analyze your spending patterns
    - Create and track budgets
    - Manage custom categories
    """)

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
from utils.account_balance import get_account_balances, update_account_balance, delete_account

st.set_page_config(
    page_title="Accounts - Personal Finance Tracker",
    page_icon="💰",
    layout="wide"
)

st.title("Manage Account Balances")

# Initialize database path in session state if not already there
if 'db_path' not in st.session_state:
    st.session_state.db_path = 'finance_data.db'

def main():
    # Create columns layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Current Account Balances")
        
        # Get account balances
        balances_df = get_account_balances(st.session_state.db_path)
        
        if balances_df.empty:
            st.info("No accounts found. Add an account balance using the form.")
        else:
            # Format display dataframe
            display_df = balances_df.copy()
            display_df['balance'] = display_df['balance'].map('${:,.2f}'.format)
            display_df['last_updated'] = display_df['last_updated'].dt.strftime('%Y-%m-%d %H:%M')
            display_df = display_df.rename(columns={
                'account_name': 'Account',
                'balance': 'Balance',
                'last_updated': 'Last Updated'
            })
            
            # Display account balances
            st.dataframe(display_df, use_container_width=True)
            
            # Total all balances
            total_balance = balances_df['balance'].sum()
            st.markdown(f"### Total Balance: **${total_balance:,.2f}**")
    
    with col2:
        st.subheader("Update Balance")
        
        # Add form for updating account balance
        with st.form("update_balance_form"):
            # If we have existing accounts, let user select one or create new
            existing_accounts = balances_df['account_name'].tolist() if not balances_df.empty else []
            
            # Add "New Account" option
            account_options = ["New Account"] + existing_accounts if existing_accounts else ["New Account"]
            selected_account = st.selectbox("Select Account", account_options)
            
            # If user selects "New Account", show text field for name
            if selected_account == "New Account":
                new_account_name = st.text_input("Account Name (e.g., Wells Fargo)")
                account_name = new_account_name
            else:
                account_name = selected_account
                
                # Get current balance for the selected account
                current_balance = balances_df[balances_df['account_name'] == account_name]['balance'].iloc[0]
                st.info(f"Current balance: ${current_balance:,.2f}")
            
            # Balance input
            balance = st.number_input("Balance", value=0.0, step=1.0)
            
            # Submit button
            submit_button = st.form_submit_button("Update Balance")
            
            if submit_button:
                if selected_account == "New Account" and not new_account_name:
                    st.error("Please enter an account name")
                elif balance < 0:
                    st.warning("Are you sure you want to enter a negative balance?")
                    confirm = st.checkbox("Yes, I confirm this is correct")
                    if confirm:
                        if update_account_balance(account_name, balance, st.session_state.db_path):
                            st.success(f"Balance for {account_name} updated successfully")
                            st.rerun()
                else:
                    if update_account_balance(account_name, balance, st.session_state.db_path):
                        st.success(f"Balance for {account_name} updated successfully")
                        st.rerun()
        
        # Section for deleting accounts
        st.subheader("Delete Account")
        
        if not balances_df.empty:
            account_to_delete = st.selectbox("Select Account to Delete", balances_df['account_name'].tolist(), key="delete_account")
            
            # First ask for confirmation with a checkbox
            confirm_delete = st.checkbox("I understand this will permanently delete the account", key="confirm_delete")
            
            # Only show delete button if checkbox is checked
            if confirm_delete:
                if st.button("Delete Account", type="primary", use_container_width=True):
                    if delete_account(account_to_delete, st.session_state.db_path):
                        st.success(f"Account {account_to_delete} deleted successfully")
                        st.rerun()
                    else:
                        st.error(f"Error deleting account {account_to_delete}")
            else:
                st.button("Delete Account", disabled=True, use_container_width=True)
        else:
            st.info("No accounts to delete")

if __name__ == "__main__":
    main()
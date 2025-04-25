import streamlit as st
import pandas as pd
import os
from utils.database import load_from_database
from utils.categorization import get_category_list
from utils.budgeting import (
    create_budget, save_budget, load_budget, get_budget_months,
    compare_budget_vs_actual, plot_budget_comparison,
    calculate_budget_progress, plot_budget_progress
)
import datetime

st.set_page_config(
    page_title="Budgeting - Personal Finance Tracker",
    page_icon="💰",
    layout="wide"
)

st.title("Budget Planning and Tracking")

# Initialize database path in session state if not already there
if 'db_path' not in st.session_state:
    st.session_state.db_path = 'finance_data.db'

def main():
    # Load all transactions
    transactions = load_from_database(st.session_state.db_path)
    
    if transactions.empty:
        st.info("No transactions found. Import your financial data first.")
        return
    
    # Set up tabs for different budget functions
    tab1, tab2 = st.tabs(["Budget Overview", "Create/Edit Budget"])
    
    with tab1:
        show_budget_overview(transactions)
    
    with tab2:
        create_edit_budget()

def show_budget_overview(transactions):
    # Get all available months with budgets
    budget_months = get_budget_months(st.session_state.db_path)
    
    # Get months from transactions
    transaction_months = sorted(transactions['date'].dt.strftime('%Y-%m').unique().tolist())
    current_month = datetime.datetime.now().strftime('%Y-%m')
    
    # Sidebar controls
    st.sidebar.header("Budget Controls")
    
    if not budget_months:
        st.info("No budget has been created yet. Use the 'Create/Edit Budget' tab to set up your budget.")
        
        # Still allow selecting a month for potential budget creation
        default_month_index = transaction_months.index(current_month) if current_month in transaction_months else len(transaction_months) - 1
        selected_month = st.sidebar.selectbox(
            "Select Month for Budget Creation",
            transaction_months,
            index=default_month_index
        )
        return
    
    # Month selector - combine budget months and transaction months
    all_months = sorted(list(set(budget_months + transaction_months)))
    
    # Default to current month if available, otherwise most recent
    default_month_index = all_months.index(current_month) if current_month in all_months else len(all_months) - 1
    selected_month = st.sidebar.selectbox(
        "Select Month for Budget Comparison",
        all_months,
        index=default_month_index
    )
    
    # Load budget for the selected month
    budget_df = load_budget(selected_month, st.session_state.db_path)
    
    # Budget overview
    st.header(f"Budget Overview for {selected_month}")
    
    # Compare budget with actual spending
    comparison = compare_budget_vs_actual(transactions, budget_df, selected_month)
    
    if comparison.empty:
        st.info(f"No budget comparison data available for {selected_month}.")
        return
    
    # Calculate budget progress metrics
    budget_progress = calculate_budget_progress(comparison)
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Total Budget", f"${budget_progress['total_budget']:,.2f}")
    col2.metric("Total Spent", f"${budget_progress['total_spent']:,.2f}")
    col3.metric("Remaining", f"${budget_progress['remaining']:,.2f}")
    col4.metric("Budget Used", f"{budget_progress['percentage_used']}%")
    
    # Budget progress gauge
    st.subheader("Overall Budget Progress")
    progress_fig = plot_budget_progress(budget_progress)
    
    if progress_fig:
        st.plotly_chart(progress_fig, use_container_width=True)
    
    # Budget comparison chart
    st.subheader("Budget vs. Actual Spending by Category")
    comparison_fig = plot_budget_comparison(comparison)
    
    if comparison_fig:
        st.plotly_chart(comparison_fig, use_container_width=True)
    
    # Budget alerts
    st.subheader("Budget Alerts")
    
    # Over budget categories
    if budget_progress['categories_over_budget']:
        st.error("Categories Over Budget:")
        over_budget_df = pd.DataFrame(budget_progress['categories_over_budget'])
        over_budget_df['budget_amount'] = over_budget_df['budget_amount'].map('${:,.2f}'.format)
        over_budget_df['actual_amount'] = over_budget_df['actual_amount'].map('${:,.2f}'.format)
        over_budget_df['percentage_used'] = over_budget_df['percentage_used'].map('{:.2f}%'.format)
        st.dataframe(over_budget_df, use_container_width=True)
    else:
        st.success("No categories are over budget!")
    
    # Near limit categories
    if budget_progress['categories_near_limit']:
        st.warning("Categories Approaching Budget Limit:")
        near_limit_df = pd.DataFrame(budget_progress['categories_near_limit'])
        near_limit_df['budget_amount'] = near_limit_df['budget_amount'].map('${:,.2f}'.format)
        near_limit_df['actual_amount'] = near_limit_df['actual_amount'].map('${:,.2f}'.format)
        near_limit_df['percentage_used'] = near_limit_df['percentage_used'].map('{:.2f}%'.format)
        st.dataframe(near_limit_df, use_container_width=True)
    
    # Detailed budget comparison table
    st.subheader("Detailed Budget Comparison")
    
    # Format table for display
    display_comparison = comparison.copy()
    display_comparison['budget_amount'] = display_comparison['budget_amount'].map('${:,.2f}'.format)
    display_comparison['actual_amount'] = display_comparison['actual_amount'].map('${:,.2f}'.format)
    display_comparison['difference'] = display_comparison['difference'].map('${:,.2f}'.format)
    display_comparison['percentage_used'] = display_comparison['percentage_used'].map('{:.2f}%'.format)
    
    st.dataframe(display_comparison, use_container_width=True)

def create_edit_budget():
    # Get the list of categories
    categories = get_category_list()
    
    # Get transaction months for selection
    transactions = load_from_database(st.session_state.db_path)
    all_months = sorted(transactions['date'].dt.strftime('%Y-%m').unique().tolist())
    current_month = datetime.datetime.now().strftime('%Y-%m')
    
    # Default to current month if available, otherwise most recent
    if all_months:
        default_month_index = all_months.index(current_month) if current_month in all_months else len(all_months) - 1
    else:
        default_month_index = 0
        all_months = [current_month]  # Use current month if no transaction data
    
    # Add month selector for budget
    selected_month = st.selectbox(
        "Select Month for Budget",
        all_months,
        index=default_month_index
    )
    
    # Get budget months to check if one exists for the selected month
    budget_months = get_budget_months(st.session_state.db_path)
    
    # Check if budget already exists for the selected month
    if selected_month in budget_months:
        existing_budget = load_budget(selected_month, st.session_state.db_path)
        st.header(f"Edit Budget for {selected_month}")
        
        # Convert existing budget to dictionary for easier handling
        existing_budget_dict = dict(zip(existing_budget['category'], existing_budget['budget_amount']))
        
        # Create input fields for each category
        budget_amounts = {}
        
        st.markdown("Enter budget amounts for each category:")
        
        # Use columns to make the form more compact
        cols = st.columns(3)
        for i, category in enumerate(categories):
            # Get existing budget amount or default to 0
            default_value = existing_budget_dict.get(category, 0.0)
            
            # Create input field in the appropriate column
            budget_amounts[category] = cols[i % 3].number_input(
                f"{category}",
                min_value=0.0,
                value=float(default_value),
                step=10.0,
                format="%.2f"
            )
        
        if st.button("Update Budget"):
            # Create new budget dataframe
            new_budget = create_budget(list(budget_amounts.keys()), list(budget_amounts.values()))
            
            # Save to database
            if save_budget(new_budget, selected_month, st.session_state.db_path):
                st.success(f"Budget for {selected_month} updated successfully!")
            else:
                st.error("Failed to save budget.")
    else:
        st.header(f"Create New Budget for {selected_month}")
        
        # Create input fields for each category
        budget_amounts = {}
        
        st.markdown("Enter budget amounts for each category:")
        
        # Use columns to make the form more compact
        cols = st.columns(3)
        for i, category in enumerate(categories):
            budget_amounts[category] = cols[i % 3].number_input(
                f"{category}",
                min_value=0.0,
                value=0.0,
                step=10.0,
                format="%.2f"
            )
        
        if st.button("Create Budget"):
            # Create new budget dataframe
            new_budget = create_budget(list(budget_amounts.keys()), list(budget_amounts.values()))
            
            # Save to database
            if save_budget(new_budget, selected_month, st.session_state.db_path):
                st.success(f"Budget for {selected_month} created successfully!")
            else:
                st.error("Failed to save budget.")
    
    # Show existing budgets
    budget_months = get_budget_months(st.session_state.db_path)
    if budget_months:
        st.markdown("---")
        st.subheader("Existing Budgets")
        st.write("You have budgets for the following months:")
        for month in budget_months:
            st.write(f"- {month}")
    
    # Option to delete a specific budget
    if budget_months:
        st.markdown("---")
        st.subheader("Delete Budget")
        delete_month = st.selectbox(
            "Select Month to Delete",
            budget_months
        )
        
        if st.button(f"Delete Budget for {delete_month}"):
            # This will delete the budget for the selected month
            import sqlite3
            try:
                conn = sqlite3.connect(st.session_state.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM budgets WHERE month = ?", (delete_month,))
                conn.commit()
                conn.close()
                st.success(f"Budget for {delete_month} has been deleted.")
                # Refresh the page to show the changes
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete budget: {str(e)}")

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import os
from utils.database import load_from_database
from utils.categorization import get_category_list
from utils.budgeting import (
    create_budget, save_budget, load_budget,
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

# Budget file path
budget_file = 'budget.csv'

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
    # Load current budget
    budget_df = load_budget(budget_file)
    
    if budget_df.empty:
        st.info("No budget has been created yet. Use the 'Create/Edit Budget' tab to set up your budget.")
        return
    
    # Sidebar controls
    st.sidebar.header("Budget Controls")
    
    # Month selector
    all_months = sorted(transactions['date'].dt.strftime('%Y-%m').unique().tolist())
    current_month = datetime.datetime.now().strftime('%Y-%m')
    
    # Default to current month if available, otherwise most recent
    default_month_index = all_months.index(current_month) if current_month in all_months else len(all_months) - 1
    selected_month = st.sidebar.selectbox(
        "Select Month for Budget Comparison",
        all_months,
        index=default_month_index
    )
    
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
    
    # Check if budget already exists
    existing_budget = load_budget(budget_file)
    
    if not existing_budget.empty:
        st.header("Edit Existing Budget")
        
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
            
            # Save to file
            if save_budget(new_budget, budget_file):
                st.success("Budget updated successfully!")
            else:
                st.error("Failed to save budget.")
    else:
        st.header("Create New Budget")
        
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
            
            # Save to file
            if save_budget(new_budget, budget_file):
                st.success("Budget created successfully!")
            else:
                st.error("Failed to save budget.")
    
    # Option to reset budget
    st.markdown("---")
    if st.button("Reset Budget (Delete All)"):
        if os.path.exists(budget_file):
            try:
                os.remove(budget_file)
                st.success("Budget has been reset. Create a new budget above.")
            except:
                st.error("Failed to reset budget.")
        else:
            st.info("No budget file exists to reset.")

if __name__ == "__main__":
    main()

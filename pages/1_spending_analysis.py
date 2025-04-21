import streamlit as st
import pandas as pd
import numpy as np
from utils.database import load_from_database
from utils.visualization import (
    monthly_spending_by_category, plot_monthly_spending,
    plot_category_distribution, income_vs_expenses,
    plot_spending_trend, plot_top_merchants,
    spending_by_source, get_category_transactions
)
import datetime
import plotly.express as px

st.set_page_config(
    page_title="Spending Analysis - Personal Finance Tracker",
    page_icon="💰",
    layout="wide"
)

st.title("Spending Analysis")

# Initialize database path in session state if not already there
if 'db_path' not in st.session_state:
    st.session_state.db_path = 'finance_data.db'

def main():
    # Load all transactions
    transactions = load_from_database(st.session_state.db_path)
    
    if transactions.empty:
        st.info("No transactions found. Import your financial data first.")
        return
    
    # Sidebar controls
    st.sidebar.header("Analysis Controls")
    
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
    
    # Add month selector for specific analyses
    all_months = sorted(filtered_transactions['date'].dt.strftime('%Y-%m').unique().tolist())
    selected_month = st.sidebar.selectbox(
        "Select Month for Category Distribution",
        ['All Time'] + all_months
    )
    
    # Get categories
    categories = ['All Categories'] + sorted(filtered_transactions['category'].unique().tolist())
    selected_category = st.sidebar.selectbox(
        "Category for Trend Analysis",
        categories
    )
    
    # Monthly Spending Overview
    st.header("Monthly Spending Overview")
    
    # Calculate monthly spending by category
    monthly_spending = monthly_spending_by_category(filtered_transactions)
    
    if not monthly_spending.empty:
        # Show spending by category chart
        monthly_fig = plot_monthly_spending(monthly_spending)
        st.plotly_chart(monthly_fig, use_container_width=True)
        
        # Add Credit Card breakdown (next to the category breakdown)
        col1, col2 = st.columns(2)
        
        with col1:
            # Show spending by category distribution
            st.subheader("Spending Distribution by Category")
            cat_fig = plot_category_distribution(filtered_transactions)
            if cat_fig:
                st.plotly_chart(cat_fig, use_container_width=True)
            else:
                st.info("No expense data available.")
                
        with col2:
            # Show breakdown by source (credit card)
            st.subheader("Spending by Credit Card")
            source_fig = spending_by_source(filtered_transactions)
            if source_fig:
                st.plotly_chart(source_fig, use_container_width=True)
            else:
                st.info("No data available for credit card breakdown.")
                
        # Interactive Category Explorer - with expandable sections
        st.subheader("Category Explorer")
        st.markdown("Click on a category to see detailed transactions")
        
        # Get unique categories from transactions with expenses
        expense_categories = filtered_transactions[filtered_transactions['amount'] < 0]['category'].unique().tolist()
        expense_categories.sort()
        
        # Create multiple expandable sections for each category
        for category in expense_categories:
            with st.expander(f"{category} Transactions"):
                # Get transactions for this category
                cat_transactions = get_category_transactions(filtered_transactions, category)
                
                if not cat_transactions.empty:
                    # Get total for this category
                    cat_total = np.abs(cat_transactions['amount'].sum())
                    st.markdown(f"**Total: ${cat_total:,.2f}**")
                    
                    # Format for display
                    display_df = cat_transactions.copy()
                    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                    display_df['amount'] = display_df['amount'].map('${:,.2f}'.format)
                    
                    # Further breakdown by credit card source
                    sources = cat_transactions['source'].unique()
                    if len(sources) > 1:
                        st.markdown("**Breakdown by Credit Card:**")
                        source_breakdown = cat_transactions.groupby('source')['amount'].sum()
                        source_abs = np.abs(source_breakdown)
                        
                        for source, amount in source_abs.items():
                            st.markdown(f"- {source}: ${amount:,.2f}")
                    
                    # Display transactions table
                    st.markdown("**Transactions:**")
                    st.dataframe(display_df[['date', 'description', 'amount', 'source']], use_container_width=True)
                else:
                    st.info(f"No transactions found for {category}")
    else:
        st.info("No expenses found in the selected date range.")
    
    # Two charts side by side: Category Distribution and Income vs Expenses
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Spending by Category")
        
        # Category distribution chart
        if selected_month != 'All Time':
            cat_fig = plot_category_distribution(filtered_transactions, selected_month)
        else:
            cat_fig = plot_category_distribution(filtered_transactions)
            
        if cat_fig:
            st.plotly_chart(cat_fig, use_container_width=True)
        else:
            st.info("No expenses found for this selection.")
    
    with col2:
        st.header("Income vs Expenses")
        
        # Income vs Expenses chart
        inc_exp_fig = income_vs_expenses(filtered_transactions)
        
        if inc_exp_fig:
            st.plotly_chart(inc_exp_fig, use_container_width=True)
        else:
            st.info("No data available for income vs expenses comparison.")
    
    # Two more charts: Spending Trend and Top Merchants
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Spending Trend Over Time")
        
        # Spending trend chart for selected category
        trend_fig = plot_spending_trend(filtered_transactions, selected_category)
        
        if trend_fig:
            st.plotly_chart(trend_fig, use_container_width=True)
        else:
            st.info("No trend data available for the selected category.")
    
    with col2:
        st.header("Top Merchants by Spending")
        
        # Number of merchants to show
        n_merchants = st.slider("Number of merchants to display", 5, 20, 10)
        
        # Top merchants chart
        merchants_fig = plot_top_merchants(filtered_transactions, n_merchants)
        
        if merchants_fig:
            st.plotly_chart(merchants_fig, use_container_width=True)
        else:
            st.info("No merchant data available.")
    
    # Summary statistics
    st.header("Summary Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    # Calculate statistics
    total_income = filtered_transactions[filtered_transactions['amount'] > 0]['amount'].sum()
    expenses_sum = filtered_transactions[filtered_transactions['amount'] < 0]['amount'].sum()
    total_expenses = np.abs(expenses_sum)
    net_cashflow = total_income - total_expenses
    
    # Display statistics
    col1.metric("Total Income", f"${total_income:,.2f}")
    col2.metric("Total Expenses", f"${total_expenses:,.2f}")
    col3.metric("Net Cashflow", f"${net_cashflow:,.2f}", delta=f"${net_cashflow:,.2f}")
    
    # Category breakdown table
    st.header("Category Breakdown")
    
    # Group expenses by category
    category_sums = filtered_transactions[filtered_transactions['amount'] < 0].groupby('category')['amount'].sum()
    category_abs = np.abs(category_sums)
    category_expenses = category_abs.sort_values(ascending=False).reset_index()
    
    # Calculate percentage of total
    category_expenses['percentage'] = (category_expenses['amount'] / total_expenses * 100).round(2)
    category_expenses['amount'] = category_expenses['amount'].map('${:,.2f}'.format)
    category_expenses['percentage'] = category_expenses['percentage'].map('{:.2f}%'.format)
    
    # Display table
    st.dataframe(category_expenses, use_container_width=True)

if __name__ == "__main__":
    main()

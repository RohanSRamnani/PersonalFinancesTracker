import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import io
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

def monthly_spending_by_category(df):
    """
    Group spending by month and category
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions
        
    Returns:
        pandas.DataFrame: Pivot table with months as rows and categories as columns
    """
    if df.empty:
        return pd.DataFrame()
        
    # Extract month and year from date
    df = df.copy()
    df['month_year'] = df['date'].dt.to_period('M')
    
    # Group by month and category, sum the amounts (only expenses)
    monthly_cat = df[df['amount'] < 0].groupby(['month_year', 'category'])['amount'].sum()
    monthly_cat = np.abs(monthly_cat)
    monthly_cat = monthly_cat.reset_index()
    
    # Pivot to get categories as columns
    pivot_table = monthly_cat.pivot_table(
        index='month_year', 
        columns='category', 
        values='amount', 
        fill_value=0
    )
    
    return pivot_table

def plot_monthly_spending(monthly_spending):
    """
    Create a plotly bar chart of monthly spending by category
    
    Parameters:
        monthly_spending (pandas.DataFrame): Output from monthly_spending_by_category
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure object
    """
    if monthly_spending.empty:
        return None
        
    # Convert period index to datetime for plotting
    monthly_spending = monthly_spending.copy()
    monthly_spending.index = monthly_spending.index.to_timestamp()
    
    # Create a melted version of the data for plotly
    melted_df = monthly_spending.reset_index().melt(
        id_vars='month_year',
        var_name='Category',
        value_name='Amount'
    )
    
    # Create the plotly figure
    fig = px.bar(
        melted_df, 
        x='month_year', 
        y='Amount', 
        color='Category',
        title='Monthly Spending by Category',
        labels={'month_year': 'Month', 'Amount': 'Amount ($)'},
        height=500
    )
    
    # Customize layout
    fig.update_layout(
        xaxis_title='Month',
        yaxis_title='Amount ($)',
        legend_title='Category',
        barmode='stack'
    )
    
    return fig

def plot_category_distribution(df, month=None):
    """
    Create a plotly pie chart showing distribution of spending across categories
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions
        month (str): Optional month period (e.g., '2023-04') to filter data
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure object
    """
    if df.empty:
        return None
        
    df = df.copy()
    
    if month:
        # Convert month string to period
        month_period = pd.Period(month)
        df['month_year'] = df['date'].dt.to_period('M')
        mask = (df['month_year'] == month_period) & (df['amount'] < 0)
        title_suffix = f' for {month}'
    else:
        # Use all data
        mask = df['amount'] < 0  # Only expenses
        title_suffix = ' (All Time)'
    
    # Group by category and sum
    if not df[mask].empty:
        category_sums = df[mask].groupby('category')['amount'].sum()
        category_totals = np.abs(category_sums).sort_values(ascending=False)
        
        # Create plotly pie chart
        fig = px.pie(
            values=category_totals.values,
            names=category_totals.index,
            title=f'Spending Distribution by Category{title_suffix}',
            height=500
        )
        
        # Customize layout
        fig.update_traces(textposition='inside', textinfo='percent+label')
        
        return fig
    else:
        return None

def income_vs_expenses(df):
    """
    Create a plotly figure showing income vs expenses by month
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure object
    """
    if df.empty:
        return None
        
    df = df.copy()
    
    # Extract month and year
    df['month_year'] = df['date'].dt.to_period('M')
    
    # Group by month, separate income and expenses
    monthly = df.groupby(['month_year']).apply(
        lambda x: pd.Series({
            'Income': x[x['amount'] > 0]['amount'].sum(),
            'Expenses': np.abs(x[x['amount'] < 0]['amount'].sum()),
            'Net': x['amount'].sum()
        })
    ).reset_index()
    
    # Convert period to datetime for plotting
    monthly['month_year'] = monthly['month_year'].dt.to_timestamp()
    
    # Create plotly figure
    fig = go.Figure()
    
    # Add bars for income and expenses
    fig.add_trace(go.Bar(
        x=monthly['month_year'],
        y=monthly['Income'],
        name='Income',
        marker_color='green'
    ))
    
    fig.add_trace(go.Bar(
        x=monthly['month_year'],
        y=monthly['Expenses'],
        name='Expenses',
        marker_color='red'
    ))
    
    # Add line for net
    fig.add_trace(go.Scatter(
        x=monthly['month_year'],
        y=monthly['Net'],
        mode='lines+markers',
        name='Net',
        line=dict(color='blue', width=3)
    ))
    
    # Update layout
    fig.update_layout(
        title='Monthly Income vs Expenses',
        xaxis_title='Month',
        yaxis_title='Amount ($)',
        barmode='group',
        height=500
    )
    
    return fig

def plot_spending_trend(df, category=None):
    """
    Create a plotly line chart showing spending trend over time
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions
        category (str): Optional category to filter by
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure object
    """
    if df.empty:
        return None
        
    df = df.copy()
    
    # Filter for expenses only
    expenses = df[df['amount'] < 0].copy()
    
    # Filter by category if specified
    if category and category != 'All Categories':
        expenses = expenses[expenses['category'] == category]
        title = f'Monthly Spending Trend - {category}'
    else:
        title = 'Monthly Spending Trend - All Categories'
    
    if expenses.empty:
        return None
    
    # Group by month and sum expenses
    expenses['month_year'] = expenses['date'].dt.to_period('M')
    monthly_sums = expenses.groupby('month_year')['amount'].sum()
    monthly_abs = np.abs(monthly_sums)
    monthly_expenses = monthly_abs.reset_index()
    monthly_expenses['month_year'] = monthly_expenses['month_year'].dt.to_timestamp()
    
    # Create plotly line chart
    fig = px.line(
        monthly_expenses,
        x='month_year',
        y='amount',
        title=title,
        labels={'month_year': 'Month', 'amount': 'Amount ($)'},
        height=400
    )
    
    # Add markers and customize line
    fig.update_traces(mode='lines+markers', line=dict(width=3))
    
    # Update layout
    fig.update_layout(
        xaxis_title='Month',
        yaxis_title='Amount ($)',
        showlegend=False
    )
    
    return fig

def plot_top_merchants(df, n=10):
    """
    Create a plotly bar chart showing top merchants by spending
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions
        n (int): Number of top merchants to show
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure object
    """
    if df.empty:
        return None
        
    df = df.copy()
    
    # Filter for expenses only
    expenses = df[df['amount'] < 0].copy()
    
    if expenses.empty:
        return None
    
    # Group by description and sum expenses
    merchant_sums = expenses.groupby('description')['amount'].sum()
    merchant_totals = np.abs(merchant_sums)
    
    # Get top n merchants
    top_merchants = merchant_totals.nlargest(n).sort_values(ascending=True)
    
    # Create plotly horizontal bar chart
    fig = px.bar(
        x=top_merchants.values,
        y=top_merchants.index,
        orientation='h',
        title=f'Top {n} Merchants by Spending',
        labels={'x': 'Amount ($)', 'y': 'Merchant'},
        height=500
    )
    
    # Add amount labels
    fig.update_traces(texttemplate='$%{x:.2f}', textposition='outside')
    
    # Update layout
    fig.update_layout(
        xaxis_title='Amount ($)',
        yaxis_title='',
        showlegend=False
    )
    
    return fig

def get_category_transactions(df, category):
    """
    Filter transactions to show only those from a specific category
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions
        category (str): Category to filter by
        
    Returns:
        pandas.DataFrame: Filtered DataFrame with transactions from the selected category
    """
    if df.empty or category is None:
        return pd.DataFrame()
        
    # Filter transactions by category
    filtered_df = df[df['category'] == category].copy()
    
    # Sort by date and amount (largest expense first)
    filtered_df = filtered_df.sort_values(by=['date', 'amount'], ascending=[False, True])
    
    return filtered_df

def spending_by_source(df):
    """
    Create a plotly pie chart showing distribution of spending across sources (credit cards)
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing transactions
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure object
    """
    if df.empty:
        return None
        
    df = df.copy()
    
    # Filter for expenses only
    expenses = df[df['amount'] < 0].copy()
    
    if expenses.empty:
        return None
    
    # Group by source and sum expenses
    source_sums = expenses.groupby('source')['amount'].sum()
    source_totals = np.abs(source_sums)
    source_totals = source_totals.sort_values(ascending=False)
    
    # Create plotly pie chart
    fig = px.pie(
        values=source_totals.values,
        names=source_totals.index,
        title='Spending by Source',
        height=400
    )
    
    # Customize layout
    fig.update_traces(textposition='inside', textinfo='percent+label+value')
    fig.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')
    
    return fig

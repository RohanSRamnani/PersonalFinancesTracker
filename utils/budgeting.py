import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

def create_budget(categories, amounts):
    """
    Create a monthly budget
    
    Parameters:
        categories (list): List of spending categories
        amounts (list): List of budget amounts corresponding to categories
    
    Returns:
        pandas.DataFrame: Budget dataframe
    """
    budget_df = pd.DataFrame({
        'category': categories,
        'budget_amount': amounts
    })
    
    return budget_df

def save_budget(budget_df, filepath='budget.csv'):
    """
    Save budget to CSV file
    
    Parameters:
        budget_df (pandas.DataFrame): Budget dataframe
        filepath (str): Path to save the budget CSV
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        budget_df.to_csv(filepath, index=False)
        return True
    except Exception as e:
        print(f"Error saving budget: {str(e)}")
        return False

def load_budget(filepath='budget.csv'):
    """
    Load budget from CSV file
    
    Parameters:
        filepath (str): Path to the budget CSV file
    
    Returns:
        pandas.DataFrame: Budget dataframe or empty dataframe if file not found
    """
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError:
        return pd.DataFrame(columns=['category', 'budget_amount'])
    except Exception as e:
        print(f"Error loading budget: {str(e)}")
        return pd.DataFrame(columns=['category', 'budget_amount'])

def compare_budget_vs_actual(transactions_df, budget_df, month=None):
    """
    Compare actual spending with budget
    
    Parameters:
        transactions_df (pandas.DataFrame): Transaction data
        budget_df (pandas.DataFrame): Budget data
        month (str, optional): Month to analyze in 'YYYY-MM' format
    
    Returns:
        pandas.DataFrame: Comparison of budget vs. actual spending
    """
    if transactions_df.empty or budget_df.empty:
        return pd.DataFrame()
    
    transactions_df = transactions_df.copy()
    
    # Filter transactions for the specified month
    if month:
        month_period = pd.Period(month)
        transactions_df['month_year'] = transactions_df['date'].dt.to_period('M')
        mask = transactions_df['month_year'] == month_period
    else:
        # Use current month if not specified
        current_month = pd.Period(datetime.now(), freq='M')
        transactions_df['month_year'] = transactions_df['date'].dt.to_period('M')
        mask = transactions_df['month_year'] == current_month
    
    # Get actual spending by category (expenses only)
    filtered_transactions = transactions_df[mask & (transactions_df['amount'] < 0)]
    
    if filtered_transactions.empty:
        comparison = budget_df.copy()
        comparison['actual_amount'] = 0
        comparison['difference'] = comparison['budget_amount']
        comparison['percentage_used'] = 0
        return comparison
    
    actual_spending = filtered_transactions.groupby('category')['amount'].sum().abs()
    
    # Create comparison dataframe
    comparison = budget_df.set_index('category').copy()
    
    # Add actual spending for categories in the budget
    comparison['actual_amount'] = actual_spending
    comparison.fillna(0, inplace=True)
    
    # Calculate difference and percentage
    comparison['difference'] = comparison['budget_amount'] - comparison['actual_amount']
    comparison['percentage_used'] = (comparison['actual_amount'] / comparison['budget_amount'] * 100).round(2)
    
    # Handle division by zero
    comparison['percentage_used'] = comparison['percentage_used'].replace([np.inf, -np.inf], 0)
    
    # Add spending in categories not in the budget
    missing_categories = actual_spending.index.difference(comparison.index)
    if not missing_categories.empty:
        missing_df = pd.DataFrame({
            'budget_amount': 0,
            'actual_amount': actual_spending[missing_categories],
            'difference': -actual_spending[missing_categories],
            'percentage_used': np.inf
        }, index=missing_categories)
        
        # Replace infinity with a large number for display purposes
        missing_df['percentage_used'] = missing_df['percentage_used'].replace([np.inf, -np.inf], 999)
        
        comparison = pd.concat([comparison, missing_df])
    
    return comparison.reset_index()

def plot_budget_comparison(comparison_df):
    """
    Create a plotly bar chart comparing budget vs actual spending
    
    Parameters:
        comparison_df (pandas.DataFrame): Output from compare_budget_vs_actual
    
    Returns:
        plotly.graph_objects.Figure: Plotly figure object
    """
    if comparison_df.empty:
        return None
    
    # Sort by budget amount for better visualization
    comparison_df = comparison_df.sort_values('budget_amount', ascending=False)
    
    fig = go.Figure()
    
    # Add bars for budget and actual spending
    fig.add_trace(go.Bar(
        x=comparison_df['category'],
        y=comparison_df['budget_amount'],
        name='Budget',
        marker_color='rgba(58, 71, 80, 0.6)'
    ))
    
    fig.add_trace(go.Bar(
        x=comparison_df['category'],
        y=comparison_df['actual_amount'],
        name='Actual',
        marker_color='rgba(246, 78, 139, 0.6)'
    ))
    
    # Update layout
    fig.update_layout(
        title='Budget vs. Actual Spending',
        xaxis_title='Category',
        yaxis_title='Amount ($)',
        barmode='group',
        height=500
    )
    
    # Add percentage labels
    for i, row in enumerate(comparison_df.itertuples()):
        percentage = row.percentage_used
        
        # Determine color based on percentage
        if percentage <= 75:
            color = 'green'
        elif percentage <= 100:
            color = 'orange'
        else:
            color = 'red'
        
        # Format the percentage text
        if percentage >= 999:  # For categories without a budget
            text = 'No Budget'
        else:
            text = f"{percentage:.1f}%"
            
        # Add the annotation
        fig.add_annotation(
            x=row.category,
            y=row.actual_amount,
            text=text,
            showarrow=False,
            font=dict(
                family="Arial",
                size=12,
                color=color
            ),
            yshift=10
        )
    
    return fig

def calculate_budget_progress(comparison_df):
    """
    Calculate budget progress metrics
    
    Parameters:
        comparison_df (pandas.DataFrame): Output from compare_budget_vs_actual
    
    Returns:
        dict: Dictionary containing budget progress metrics
    """
    if comparison_df.empty:
        return {
            'total_budget': 0,
            'total_spent': 0,
            'remaining': 0,
            'percentage_used': 0,
            'categories_over_budget': [],
            'categories_near_limit': []
        }
    
    # Calculate totals
    total_budget = comparison_df['budget_amount'].sum()
    total_spent = comparison_df['actual_amount'].sum()
    remaining = total_budget - total_spent
    
    if total_budget > 0:
        percentage_used = (total_spent / total_budget * 100).round(2)
    else:
        percentage_used = 0
    
    # Find categories over budget
    over_budget = comparison_df[comparison_df['percentage_used'] > 100]
    over_budget_list = over_budget[['category', 'budget_amount', 'actual_amount', 'percentage_used']].to_dict('records')
    
    # Find categories nearing budget limit (75-100%)
    near_limit = comparison_df[(comparison_df['percentage_used'] >= 75) & (comparison_df['percentage_used'] <= 100)]
    near_limit_list = near_limit[['category', 'budget_amount', 'actual_amount', 'percentage_used']].to_dict('records')
    
    return {
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining': remaining,
        'percentage_used': percentage_used,
        'categories_over_budget': over_budget_list,
        'categories_near_limit': near_limit_list
    }

def plot_budget_progress(budget_progress):
    """
    Create a plotly gauge chart showing overall budget progress
    
    Parameters:
        budget_progress (dict): Output from calculate_budget_progress
    
    Returns:
        plotly.graph_objects.Figure: Plotly figure object
    """
    percentage = budget_progress['percentage_used']
    
    # Define colors based on percentage
    if percentage <= 75:
        color = "green"
    elif percentage <= 100:
        color = "orange"
    else:
        color = "red"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=percentage,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Budget Utilization", 'font': {'size': 24}},
        gauge={
            'axis': {'range': [0, 120], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 75], 'color': 'lightgreen'},
                {'range': [75, 100], 'color': 'lightyellow'},
                {'range': [100, 120], 'color': 'lightcoral'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 100
            }
        }
    ))
    
    fig.update_layout(height=300)
    
    return fig

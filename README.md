Personal Finance Tracker
--- Project Overview ---
This Personal Finance Tracker is a comprehensive financial management application built with Streamlit and Python that helps you gain control over your finances by offering detailed insights into spending patterns, account balances, and budgeting tools.

The system transforms complex financial data from multiple sources (Wells Fargo, Chase, Bank of America, Apple Pay, and Schwab) into actionable insights through interactive visualizations and detailed analytics.

Key Features
1. Multi-Source Data Import
Import financial statements from major banks and credit card providers
Support for Excel (.xlsx) file imports
Automatic source detection and standardization
Smart categorization of transactions
2. Dashboard Overview
Dashboard
The dashboard provides a quick overview of your financial health with key metrics like net worth, monthly spending trends, and recent transactions.

3. Comprehensive Spending Analysis
Spending Analysis
The spending analysis page offers detailed breakdowns of your spending by category and source, with interactive charts and filters.

Key components:

Monthly spending charts broken down by category
Spending distribution pie charts
Income vs. Expenses analysis
Spending trends over time
Interactive category explorer with detailed transaction lists
Credit card spending distribution

4. Transaction Management
Transaction View
The transaction view provides powerful tools to search, filter, and edit your financial transactions.

Features:

Advanced filtering capabilities with AgGrid component
Excel-like checkbox filtering for categories, sources, and descriptions
Date range filtering
Amount range filtering
Edit transaction details like category and description
Delete individual transactions
5. Budgeting Tools
Budgeting
Create and track monthly budgets across different spending categories.

Capabilities:

Set budget amounts by category
Compare actual spending to budget
Visual progress indicators for each category
Monthly budget selection and comparison
6. Account Management
Accounts
Track balances across all your financial accounts in one place.

Features:

Add and update account balances manually
Track total net worth
Remove accounts when needed
View total assets and liabilities

7. Category Management
Category Management
Customize transaction categories to fit your personal finance needs.

Options:

Create custom spending categories
Delete unused categories
Apply bulk categorization to similar transactions
Technical Highlights
Data Processing: Advanced pandas data manipulation for financial metrics
Database: SQLite backend for persistent storage of transactions and settings
Visualization: Interactive Plotly charts for data exploration
User Interface: Streamlit framework for an intuitive, responsive interface
Transaction Categorization: Smart algorithm that matches transaction descriptions to appropriate categories
Error Handling: Robust date parsing and data validation
Getting Started
Clone the repository


Enable Debug Mode in the sidebar to access additional diagnostic tools
Use Database Path Info to verify correct database connection
View categorization debugging information when needed
This application securely processes your financial data locally, with no data sent to external servers. Your financial information remains private and under your control at all times.
Install dependencies:
pip install -r requirements.txt
Run the application:
streamlit run dashboard.py
Import your financial data from the dashboard
Explore your finances!
Local Development
For local development on VSCode or other environments:

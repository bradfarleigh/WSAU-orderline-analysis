import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from plotly import graph_objects as go
from io import StringIO

def load_data(uploaded_file):
    df = pd.read_csv(uploaded_file)
    df['Date placed'] = pd.to_datetime(df['Date placed'])
    df['Date Completed'] = pd.to_datetime(df['Date Completed'])
    return df

def analyse_data(df):
    # Calculate revenue per order line
    df['Revenue'] = df['QTY'] * df['Unit Price']
    
    # Group by Order ID to get unique orders and their total revenue
    order_data = df.groupby('Order ID').agg({
        'Email': 'first',
        'Date placed': 'first',
        'Revenue': 'sum',
        'Unit Cost': lambda x: (x * df.loc[x.index, 'QTY']).sum()  # Total cost per order
    }).reset_index()
    
    # Add shipping fee to revenue and calculate profit
    order_data['Revenue'] += 15  # Add $15 shipping fee to each order's revenue
    order_data['Profit'] = order_data['Revenue'] - order_data['Unit Cost']
    
    # Sort orders by date
    order_data = order_data.sort_values('Date placed')
    
    # Identify first purchase date for each email
    first_purchase_dates = order_data.groupby('Email')['Date placed'].min()
    
    # Identify repeat customers
    order_data['Customer Type'] = order_data.apply(
        lambda row: 'Repeat' if row['Date placed'] > first_purchase_dates[row['Email']] else 'First-time',
        axis=1
    )
    
    # Create month-year column
    order_data['Month-Year'] = order_data['Date placed'].dt.to_period('M')
    
    # Calculate count of customers
    count_data = order_data.groupby(['Month-Year', 'Customer Type']).size().unstack(fill_value=0).reset_index()
    count_data['Month-Year'] = count_data['Month-Year'].astype(str)
    
    # Calculate revenue
    revenue_data = order_data.groupby(['Month-Year', 'Customer Type'])['Revenue'].sum().unstack(fill_value=0).reset_index()
    revenue_data['Month-Year'] = revenue_data['Month-Year'].astype(str)
    
    # Ensure both 'First-time' and 'Repeat' columns exist in both dataframes
    for df in [count_data, revenue_data]:
        for col in ['First-time', 'Repeat']:
            if col not in df.columns:
                df[col] = 0
    
    return count_data, revenue_data, order_data

def analyse_product_sales(df):
    # Calculate revenue and profit for each order line
    df['Revenue'] = df['QTY'] * df['Unit Price']
    df['Profit'] = (df['Unit Price'] - df['Unit Cost']) * df['QTY']
    
    # Add shipping fee to the first line item of each order
    df['Is_First_Item'] = ~df['Order ID'].duplicated(keep='first')
    df.loc[df['Is_First_Item'], 'Revenue'] += 15
    df.loc[df['Is_First_Item'], 'Profit'] += 15
    
    # Group by SKU
    product_analysis = df.groupby('SKU').agg({
        'QTY': 'sum',
        'Revenue': 'sum',
        'Profit': 'sum',
        'Unit Price': 'mean',
        'Unit Cost': 'mean'
    }).reset_index()
    
    # Calculate profit margin
    product_analysis['Profit Margin'] = product_analysis['Profit'] / product_analysis['Revenue']
    
    # Sort by revenue (descending)
    product_analysis = product_analysis.sort_values('Revenue', ascending=False)
    
    return product_analysis

def analyse_profitability_over_time(df):
    # Calculate profit for each order line
    df['Profit'] = (df['Unit Price'] - df['Unit Cost']) * df['QTY']
    
    # Add shipping fee to the first line item of each order
    df['Is_First_Item'] = ~df['Order ID'].duplicated(keep='first')
    df.loc[df['Is_First_Item'], 'Profit'] += 15
    df.loc[df['Is_First_Item'], 'Revenue'] += 15
    
    # Group by month and calculate total profit and revenue
    profitability = df.groupby(df['Date placed'].dt.to_period('M')).agg({
        'Profit': 'sum',
        'Revenue': 'sum'
    }).reset_index()
    profitability['Date placed'] = profitability['Date placed'].dt.to_timestamp()
    profitability = profitability.sort_values('Date placed')
    
    # Calculate cumulative profit
    profitability['Cumulative Profit'] = profitability['Profit'].cumsum()
    
    return profitability

def analyse_first_and_repeat_purchases(df):
    # Sort the dataframe by Email and Date placed
    df_sorted = df.sort_values(['Email', 'Date placed'])
    
    # Identify first purchases for each customer
    df_sorted['is_first_purchase'] = ~df_sorted['Email'].duplicated(keep='first')
    
    # Get first purchase products
    first_purchases = df_sorted[df_sorted['is_first_purchase']]
    
    # Get repeat purchase products
    repeat_purchases = df_sorted[~df_sorted['is_first_purchase']]
    
    # Count occurrences of each product in first purchases
    first_purchase_counts = first_purchases['SKU'].value_counts().reset_index()
    first_purchase_counts.columns = ['SKU', 'First Purchase Count']
    
    # Count occurrences of each product in repeat purchases
    repeat_purchase_counts = repeat_purchases['SKU'].value_counts().reset_index()
    repeat_purchase_counts.columns = ['SKU', 'Repeat Purchase Count']
    
    # Merge the counts
    purchase_analysis = pd.merge(first_purchase_counts, repeat_purchase_counts, on='SKU', how='outer').fillna(0)
    
    # Calculate the ratio of repeat purchases to first purchases
    purchase_analysis['Repeat to First Ratio'] = purchase_analysis['Repeat Purchase Count'] / purchase_analysis['First Purchase Count']
    
    # Sort by First Purchase Count descending
    purchase_analysis = purchase_analysis.sort_values('First Purchase Count', ascending=False)
    
    return purchase_analysis

def main():
    st.title("WatchStraps.com.au Order Analysis")
    
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        df = load_data(uploaded_file)
        count_data, revenue_data, order_data = analyse_data(df)
        product_analysis = analyse_product_sales(df)
        profitability_data = analyse_profitability_over_time(df)
        first_repeat_analysis = analyse_first_and_repeat_purchases(df)
        
        st.header("Repeat vs First-time Purchasers Analysis")
        
        # Count plot
        st.subheader("Count of Unique Orders per Month")
        fig_count = go.Figure()
        for col in ['First-time', 'Repeat']:
            fig_count.add_trace(
                go.Bar(
                    x=count_data['Month-Year'],
                    y=count_data[col],
                    name=col,
                    text=count_data[col],
                    textposition='auto',
                )
            )
        
        fig_count.update_layout(
            title="Repeat vs First-time Purchasers per Month (Count)",
            xaxis_title="Month-Year",
            yaxis_title="Number of Orders",
            barmode='stack'
        )
        st.plotly_chart(fig_count)
        
        # Revenue plot
        st.subheader("Revenue from Orders per Month")
        fig_revenue = go.Figure()
        for col in ['First-time', 'Repeat']:
            fig_revenue.add_trace(
                go.Bar(
                    x=revenue_data['Month-Year'],
                    y=revenue_data[col],
                    name=col,
                    text=revenue_data[col].apply(lambda x: f'${x:,.0f}'),
                    textposition='auto',
                )
            )
        
        fig_revenue.update_layout(
            title="Repeat vs First-time Purchasers per Month (Revenue)",
            xaxis_title="Month-Year",
            yaxis_title="Revenue (AUD)",
            barmode='stack'
        )
        st.plotly_chart(fig_revenue)
        
        st.header("Product Sales Analysis")
        
        # Top 10 products by revenue
        st.subheader("Top 10 Products by Revenue")
        fig_top_revenue = px.bar(product_analysis.head(10), x='SKU', y='Revenue',
                                 text='Revenue', title="Top 10 Products by Revenue")
        fig_top_revenue.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
        st.plotly_chart(fig_top_revenue)
        
        # Top 10 products by profit
        st.subheader("Top 10 Products by Profit")
        fig_top_profit = px.bar(product_analysis.sort_values('Profit', ascending=False).head(10), 
                                x='SKU', y='Profit', text='Profit', title="Top 10 Products by Profit")
        fig_top_profit.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
        st.plotly_chart(fig_top_profit)
        
        # Profit margin by product
        st.subheader("Profit Margin by Product")
        fig_profit_margin = px.scatter(product_analysis, x='Revenue', y='Profit Margin', 
                                       size='QTY', hover_name='SKU', 
                                       title="Profit Margin vs Revenue (Size represents Quantity Sold)")
        st.plotly_chart(fig_profit_margin)
        
        st.header("Profitability Over Time")
        
        # Monthly revenue and profit
        st.subheader("Monthly Revenue and Profit")
        fig_monthly = go.Figure()
        fig_monthly.add_trace(go.Bar(
            x=profitability_data['Date placed'],
            y=profitability_data['Revenue'],
            name='Revenue',
            text=profitability_data['Revenue'].apply(lambda x: f'${x:,.0f}'),
            textposition='auto'
        ))
        fig_monthly.add_trace(go.Bar(
            x=profitability_data['Date placed'],
            y=profitability_data['Profit'],
            name='Profit',
            text=profitability_data['Profit'].apply(lambda x: f'${x:,.0f}'),
            textposition='auto'
        ))
        fig_monthly.update_layout(
            title="Monthly Revenue and Profit",
            xaxis_title="Month",
            yaxis_title="Amount (AUD)",
            barmode='group',
            xaxis_tickformat='%b %Y'
        )
        st.plotly_chart(fig_monthly)
        
        # Cumulative profit over time
        fig_cumulative_profit = px.line(profitability_data, x='Date placed', y='Cumulative Profit',
                                        title="Cumulative Profit Over Time")
        fig_cumulative_profit.update_traces(mode='lines+markers')
        fig_cumulative_profit.update_layout(
            yaxis_title="Cumulative Profit (AUD)",
            xaxis_title="Month",
            xaxis_tickformat='%b %Y'
        )
        st.plotly_chart(fig_cumulative_profit)
        
        st.header("First Purchase and Repeat Purchase Analysis")
        
        # Top 10 products by first purchase count
        st.subheader("Top 10 Products by First Purchase Count")
        fig_first_purchase = px.bar(first_repeat_analysis.head(10), x='SKU', y='First Purchase Count',
                                    text='First Purchase Count', title="Top 10 Products by First Purchase Count")
        fig_first_purchase.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        st.plotly_chart(fig_first_purchase)
        
        # Top 10 products by repeat to first ratio
        st.subheader("Top 10 Products by Repeat to First Purchase Ratio")
        top_repeat_ratio = first_repeat_analysis.sort_values('Repeat to First Ratio', ascending=False).head(10)
        fig_repeat_ratio = px.bar(top_repeat_ratio, x='SKU', y='Repeat to First Ratio',
                                  text='Repeat to First Ratio', title="Top 10 Products by Repeat to First Purchase Ratio")
        fig_repeat_ratio.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        st.plotly_chart(fig_repeat_ratio)
        
        # Display first and repeat purchase analysis data
        st.subheader("First and Repeat Purchase Analysis Data")
        st.write(first_repeat_analysis)
        
        # Display product analysis data
        st.subheader("Product Analysis Data")
        st.write(product_analysis)
        
        # Display raw data
        st.subheader("Raw Data")
        st.write(df)

if __name__ == "__main__":
    main()
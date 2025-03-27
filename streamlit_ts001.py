import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Set page config
st.set_page_config(
    page_title="Bolivia Growth Accounting Visualizer",
    page_icon="📈",
    layout="wide"
)

# App title
st.title("Bolivia Growth Accounting Time Series Visualizer")

# File uploader
uploaded_file = st.file_uploader("Upload the growth accounting CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        # Load data
        df = pd.read_csv(uploaded_file)
        
        # Display data sample
        with st.expander("Preview Raw Data"):
            st.dataframe(df.head())
        
        # Filter for Bolivia
        df_bolivia = df[df['Country'] == 'Bolivia (Plurinational State of)']
        
        # Define year columns
        year_columns = [str(year) for year in range(1950, 2020)]
        
        # Get unique variables
        variable_names = df_bolivia['Variable name'].unique()
        
        # Visualization options
        st.subheader("Visualization Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Variable filter
            variable_filter = st.text_input("Filter variables (type to search):")
            if variable_filter:
                filtered_variables = [v for v in variable_names if variable_filter.lower() in v.lower()]
            else:
                filtered_variables = variable_names
        
        with col2:
            # Select variables
            selected_variables = st.multiselect(
                "Select variables to visualize (leave empty to show all):",
                options=filtered_variables,
                default=[]
            )
            
            if not selected_variables:
                selected_variables = filtered_variables
        
        with col3:
            # Layout options
            cols_per_row = st.slider("Plots per row:", 1, 3, 2)
            plot_height = st.slider("Plot height (pixels):", 200, 500, 300)
        
        # Create visualization
        st.subheader("Time Series Plots for Bolivia")
        
        # Calculate rows needed
        num_rows = (len(selected_variables) + cols_per_row - 1) // cols_per_row
        
        # Create subplot grid
        fig = make_subplots(
            rows=num_rows, 
            cols=cols_per_row,
            subplot_titles=selected_variables,
            vertical_spacing=0.1
        )
        
        # Create time series plots
        row_num = 1
        col_num = 1
        
        for variable_name in selected_variables:
            df_variable = df_bolivia[df_bolivia['Variable name'] == variable_name]
            
            if not df_variable.empty:
                # Extract data for the variable
                variable_data = df_variable.iloc[0][year_columns]
                
                # Convert to numeric and handle missing values
                variable_data = pd.to_numeric(variable_data, errors='coerce')
                
                # Filter out years with missing data
                valid_mask = ~np.isnan(variable_data)
                valid_years = [year_columns[i] for i in range(len(year_columns)) if valid_mask[i]]
                valid_data = variable_data[valid_mask]
                
                # Skip if no valid data
                if len(valid_data) == 0:
                    continue
                
                # Add trace to subplot
                fig.add_trace(
                    go.Scatter(
                        x=valid_years, 
                        y=valid_data, 
                        mode='lines+markers',
                        name=variable_name,
                        line=dict(width=2),
                        marker=dict(size=6),
                        hovertemplate='Year: %{x}<br>Value: %{y:.4f}<extra></extra>'
                    ),
                    row=row_num, 
                    col=col_num
                )
                
                # Update axes labels
                fig.update_xaxes(title_text="Year", row=row_num, col=col_num)
                fig.update_yaxes(title_text="Value", row=row_num, col=col_num)
                
                # Move to next subplot position
                if col_num == cols_per_row:
                    col_num = 1
                    row_num += 1
                else:
                    col_num += 1
        
        # Update layout
        fig.update_layout(
            height=plot_height * num_rows,
            showlegend=False,
            title_text='Bolivia Time Series Plots',
            template='plotly_white',
            margin=dict(l=50, r=50, t=100, b=50)
        )
        
        # Show the plot
        st.plotly_chart(fig, use_container_width=True)
        
        # Individual variable analysis
        st.subheader("Detailed Variable Analysis")
        
        # Select variable for detailed view
        selected_var_detail = st.selectbox("Select a variable to analyze in detail:", selected_variables)
        
        # Get data for selected variable
        df_var_detail = df_bolivia[df_bolivia['Variable name'] == selected_var_detail]
        
        if not df_var_detail.empty:
            # Extract data
            var_data = pd.to_numeric(df_var_detail.iloc[0][year_columns], errors='coerce')
            
            # Filter out missing values
            valid_mask = ~np.isnan(var_data)
            valid_years = [year_columns[i] for i in range(len(year_columns)) if valid_mask[i]]
            valid_data = var_data[valid_mask]
            
            if len(valid_data) > 0:
                # Create tabs for different analyses
                tab1, tab2 = st.tabs(["Time Series", "Statistics"])
                
                with tab1:
                    # Detailed time series plot
                    fig_detail = px.line(
                        x=valid_years, 
                        y=valid_data, 
                        title=f"{selected_var_detail} Time Series",
                        labels={"x": "Year", "y": "Value"},
                        markers=True
                    )
                    
                    fig_detail.update_layout(
                        height=500,
                        hovermode='x unified',
                        template='plotly_white'
                    )
                    
                    # Add range slider
                    fig_detail.update_xaxes(
                        rangeslider_visible=True
                    )
                    
                    st.plotly_chart(fig_detail, use_container_width=True)
                    
                    # Calculate growth rates
                    if len(valid_data) > 1:
                        # Create a pandas Series for valid data
                        valid_series = pd.Series(valid_data.values, index=valid_years)
                        growth_rates = valid_series.pct_change() * 100
                        # Remove NaN growth rate
                        growth_rates = growth_rates.dropna()
                        
                        fig_growth = px.bar(
                            x=growth_rates.index,
                            y=growth_rates.values,
                            title=f"Annual Growth Rate (%) for {selected_var_detail}",
                            labels={"x": "Year", "y": "Growth Rate (%)"}
                        )
                        
                        # Color bars based on value
                        fig_growth.update_traces(
                            marker_color=["green" if x > 0 else "red" for x in growth_rates.values],
                            hovertemplate='Year: %{x}<br>Growth Rate: %{y:.2f}%<extra></extra>'
                        )
                        
                        fig_growth.update_layout(
                            height=400,
                            template='plotly_white'
                        )
                        
                        st.plotly_chart(fig_growth, use_container_width=True)
                
                with tab2:
                    # Statistics
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    with col1:
                        st.metric("Mean", f"{valid_data.mean():.2f}")
                    
                    with col2:
                        st.metric("Median", f"{valid_data.median():.2f}")
                    
                    with col3:
                        st.metric("Min", f"{valid_data.min():.2f}")
                    
                    with col4:
                        st.metric("Max", f"{valid_data.max():.2f}")
                    
                    with col5:
                        st.metric("Std Dev", f"{valid_data.std():.2f}")
                    
                    # Moving average analysis
                    st.subheader("Trend Analysis")
                    
                    # Add moving average
                    if len(valid_data) > 2:
                        # Create a pandas Series for valid data
                        valid_series = pd.Series(valid_data.values, index=valid_years)
                        
                        window_size = st.slider("Moving average window (years):", 2, min(15, len(valid_data)-1), 5)
                        
                        # Calculate moving average
                        rolling_avg = valid_series.rolling(window=window_size, min_periods=1).mean()
                        
                        # Plot original data with moving average
                        fig_ma = go.Figure()
                        
                        # Add original data
                        fig_ma.add_trace(
                            go.Scatter(
                                x=valid_years,
                                y=valid_data,
                                mode='lines+markers',
                                name='Original Data',
                                line=dict(color='rgba(0,0,255,0.5)', width=1)
                            )
                        )
                        
                        # Add moving average
                        fig_ma.add_trace(
                            go.Scatter(
                                x=valid_years,
                                y=rolling_avg,
                                mode='lines',
                                name=f'{window_size}-year Moving Average',
                                line=dict(color='red', width=3)
                            )
                        )
                        
                        fig_ma.update_layout(
                            title=f"{selected_var_detail} with {window_size}-year Moving Average",
                            xaxis_title="Year",
                            yaxis_title="Value",
                            height=500,
                            template='plotly_white',
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig_ma, use_container_width=True)
            else:
                st.warning(f"No valid data available for {selected_var_detail}")
        
        # Download option
        st.subheader("Download Data")
        
        # Prepare data for selected variables
        download_data = pd.DataFrame({'Year': year_columns})
        
        for variable_name in selected_variables:
            df_variable = df_bolivia[df_bolivia['Variable name'] == variable_name]
            if not df_variable.empty:
                download_data[variable_name] = pd.to_numeric(df_variable.iloc[0][year_columns], errors='coerce')
        
        # Download button
        csv = download_data.to_csv(index=False)
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name="Bolivia_time_series_data.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Error processing the file: {str(e)}")
else:
    # Display instructions when no file is uploaded
    st.info("Please upload the growthAccounting.csv file to begin visualization.")
    
    st.markdown("""
    ### Expected CSV format
    
    The CSV should contain:
    - 'Country' column: Country names (the app will filter for Bolivia)
    - 'Variable name' column: Names of economic variables
    - Year columns: Years from 1950 to 2019
    
    This app is designed based on the reference code to visualize Bolivia's growth accounting data.
    """)
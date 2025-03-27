import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os # To check if file exists

# --- Configuration ---
DATA_FILE = 'growthAccounting.csv'
DEFAULT_COUNTRY = 'Bolivia (Plurinational State of)'

st.set_page_config(layout="wide")
st.title("Interactive Time Series Visualization")

# --- Load Data ---
@st.cache_data # Cache data loading for performance
def load_data(file_path):
    if not os.path.exists(file_path):
        st.error(f"Error: Data file '{file_path}' not found in the current directory.")
        st.stop() # Stop execution if file not found
    try:
        df = pd.read_csv(file_path)
        # Identify and sort year columns
        year_columns = sorted([col for col in df.columns if col.isdigit() and len(col) == 4])
        return df, year_columns
    except Exception as e:
        st.error(f"Error loading or processing the CSV file: {e}")
        st.stop()

df, all_year_columns = load_data(DATA_FILE)

# --- Sidebar for User Input ---
st.sidebar.header("Filters")

# Country Selection
country_list = sorted(df['Country'].unique())
try:
    default_index = country_list.index(DEFAULT_COUNTRY)
except ValueError:
    default_index = 0 # Default to the first country if Bolivia isn't found
selected_country = st.sidebar.selectbox(
    "Select Country",
    country_list,
    index=default_index
)

# Filter dataframe for the selected country
df_country = df[df['Country'] == selected_country].copy()

# Time Period Selection
min_year = int(all_year_columns[0])
max_year = int(all_year_columns[-1])

selected_years = st.sidebar.slider(
    "Select Time Period (Year)",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year) # Default to full range
)
start_year, end_year = selected_years
# Filter year columns based on selection
year_columns_filtered = [str(yr) for yr in range(start_year, end_year + 1) if str(yr) in all_year_columns]

# Transformation Selection
transformation = st.sidebar.radio(
    "Select Transformation",
    ('Raw Values', 'Logarithm', 'Annual Growth Rate (%)'),
    key='transformation'
)

# Variable Selection
available_variables = sorted(df_country['Variable name'].unique())
selected_variables = st.sidebar.multiselect(
    "Select Variables to Plot",
    available_variables,
    default=available_variables # Default to all variables
)

# --- Data Processing & Plotting ---
# Main header remains
st.header(f"Individual Plots for {selected_country} ({start_year}-{end_year})")

if not year_columns_filtered:
    st.warning("Selected time period does not contain any data.")
elif not selected_variables:
    st.warning("Please select at least one variable to plot.")
else:
    charts_plotted = 0
    warnings = []

    for var_name in selected_variables:
        # REMOVED: st.subheader(f"{var_name}") # Removed subheader

        df_variable = df_country[df_country['Variable name'] == var_name]
        if not df_variable.empty:
            # Extract the specific row for the variable, focusing on selected years
            data_row = df_variable.iloc[0]
            time_series_raw = data_row[year_columns_filtered]

            # Convert to numeric, coercing errors, but DO NOT fillna yet for transformations
            time_series_numeric = pd.to_numeric(time_series_raw, errors='coerce')

            # Apply Transformation
            processed_values = None
            plot_title = f"{var_name} ({transformation})" # Keep variable in plot title

            if transformation == 'Raw Values':
                processed_values = time_series_numeric.fillna(0)
                plot_title = f"{var_name}" # Simpler title for raw values

            elif transformation == 'Logarithm':
                positive_values = time_series_numeric.where(time_series_numeric > 0)
                if time_series_numeric.le(0).any():
                     warnings.append(f"Warning: Non-positive values found for '{var_name}' cannot be plotted on log scale.")
                processed_values = np.log(positive_values)
                plot_title = f"Log({var_name})"

            elif transformation == 'Annual Growth Rate (%)':
                processed_values = time_series_numeric.pct_change() * 100
                plot_title = f"{var_name} (Annual Growth %)"

            if processed_values is not None:
                # Create a temporary dataframe for this variable
                temp_df = pd.DataFrame({
                    'Year': pd.to_datetime([yr for yr in year_columns_filtered], format='%Y'),
                    'Value': processed_values.values,
                }).dropna(subset=['Value'])

                if not temp_df.empty:
                    # Create the plot for this specific variable
                    fig_variable = px.line(
                        temp_df,
                        x='Year',
                        y='Value',
                        title=plot_title, # Use the generated plot title
                        markers=True
                    )

                    fig_variable.update_layout(
                        xaxis_title="Year",
                        yaxis_title="", # REMOVED Y-axis title
                        height=400
                    )

                    # Display the plot in Streamlit
                    st.plotly_chart(fig_variable, use_container_width=True)
                    charts_plotted += 1
                else:
                     warnings.append(f"No valid data points to plot for '{var_name}' after transformation and filtering.")
            else:
                 warnings.append(f"Could not process data for '{var_name}' with selected transformation.")
        else:
             warnings.append(f"Could not find data for variable '{var_name}' for {selected_country}.")

    # Display Warnings (only unique ones)
    for warning in set(warnings):
        st.warning(warning)

    if charts_plotted == 0 and selected_variables:
         st.warning("No charts could be generated based on the current selections and data.")
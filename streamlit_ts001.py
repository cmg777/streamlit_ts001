import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os # To check if file exists
import io # For in-memory file handling for download

# --- Configuration ---
DATA_FILE = 'growthAccounting.csv'
DEFAULT_COUNTRY = 'Bolivia (Plurinational State of)'

# --- Define Fixed Variable Order ---
VARIABLE_ORDER = [
    'Real GDP at constant 2017 national prices (in mil. 2017US$)',
    'Capital services at constant 2017 national prices (2017=1)',
    'Number of persons engaged (in millions)',
    'Average annual hours worked by persons engaged',
    'Human capital index, based on years of schooling and returns to education; see Human capital in PWT9.',
    'Share of labour compensation in GDP at current national prices',
    'TFP at constant national prices (2017=1)'
]

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

# Variable Selection - Allow user to select any available, but display order will be fixed
available_variables = sorted(df_country['Variable name'].unique())
selected_variables = st.sidebar.multiselect(
    "Select Variables to Plot",
    available_variables,
    default=available_variables # Default to all available variables initially
)

# --- Data Processing & Plotting ---
st.header(f"Individual Plots for {selected_country} ({start_year}-{end_year})")

# List to store dataframes for download
download_data_list = []

if not year_columns_filtered:
    st.warning("Selected time period does not contain any data.")
elif not selected_variables:
    st.warning("Please select at least one variable to plot.")
else:
    charts_plotted = 0
    warnings = []

    # --- Iterate through the FIXED order ---
    for var_name in VARIABLE_ORDER:
        # --- Check if this variable was actually selected by the user ---
        if var_name in selected_variables:

            df_variable = df_country[df_country['Variable name'] == var_name]
            if not df_variable.empty:
                # Extract the specific row for the variable, focusing on selected years
                data_row = df_variable.iloc[0]
                time_series_raw = data_row[year_columns_filtered]

                # Convert to numeric, coercing errors, but DO NOT fillna yet for transformations
                time_series_numeric = pd.to_numeric(time_series_raw, errors='coerce')

                # Apply Transformation
                processed_values = None
                plot_title = f"{var_name} ({transformation})" # Default plot title

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
                        'Year': [int(yr) for yr in year_columns_filtered], # Store year as integer
                        # 'Year_dt': pd.to_datetime([yr for yr in year_columns_filtered], format='%Y'), # Keep datetime for plotting
                        'Variable': var_name,
                        'Value': processed_values.values,
                    }).dropna(subset=['Value']) # Drop rows where Value is NaN

                    if not temp_df.empty:
                         # Add data to list for final download dataframe
                        download_data_list.append(temp_df.copy())

                        # Create the plot for this specific variable using datetime years
                        plot_df_display = temp_df.assign(Year_dt=pd.to_datetime(temp_df['Year'], format='%Y'))
                        fig_variable = px.line(
                            plot_df_display,
                            x='Year_dt', # Plot against datetime axis
                            y='Value',
                            title=plot_title,
                            markers=True
                        )

                        fig_variable.update_layout(
                            xaxis_title="Year",
                            yaxis_title="", # No Y-axis title
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
                 warnings.append(f"Data for '{var_name}' not found for {selected_country}.")

    # Display Warnings (only unique ones)
    for warning in set(warnings):
        st.warning(warning)

    if charts_plotted == 0 and selected_variables:
         st.warning("No charts could be generated based on the current selections and data.")

    # --- Download Section ---
    if download_data_list:
        st.markdown("---") # Separator line
        st.header("Download Visualized Data")

        # Combine all collected data into one DataFrame
        final_df_for_download = pd.concat(download_data_list, ignore_index=True)
        # Pivot for a potentially wider format (optional, long is often better)
        # final_df_wide = final_df_for_download.pivot(index='Year', columns='Variable', values='Value').reset_index()

        # Prepare filenames
        country_short = selected_country.split(" ")[0].replace(",", "").replace("(", "").replace(")", "") # Basic cleaning for filename
        filename_base = f"{country_short}_{transformation.replace(' (%)','_pct').replace(' ','_')}_{start_year}_{end_year}"

        col1, col2 = st.columns(2) # Layout buttons side-by-side

        with col1:
            # CSV Download Button
            csv_data = final_df_for_download.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Data as CSV",
                data=csv_data,
                file_name=f"{filename_base}.csv",
                mime='text/csv',
            )

        with col2:
            # Stata Download Button
            # Use BytesIO buffer to hold the Stata file data in memory
            stata_buffer = io.BytesIO()
            try:
                # Need to handle potential Stata variable name length limits if variable names are very long
                # For simplicity, we assume pandas handles basic conversion well enough
                final_df_for_download.to_stata(stata_buffer, write_index=False, version=118) # Specify a common Stata version
                stata_buffer.seek(0) # Rewind buffer to the beginning
                st.download_button(
                    label="Download Data as Stata (.dta)",
                    data=stata_buffer,
                    file_name=f"{filename_base}.dta",
                    mime='application/octet-stream', # Generic binary mime type
                 )
            except Exception as e:
                 st.error(f"Could not generate Stata file: {e}")
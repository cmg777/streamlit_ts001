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

# List to store dataframes (long format) for processing
processed_data_list = []

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
                    # Create a temporary dataframe (long format) for this variable
                    temp_df = pd.DataFrame({
                        'Year': [int(yr) for yr in year_columns_filtered],
                        'Variable': var_name,
                        'Value': processed_values.values,
                    }).dropna(subset=['Value'])

                    if not temp_df.empty:
                         # Add data to list for final processing
                        processed_data_list.append(temp_df.copy())

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
    if processed_data_list: # Check if there's any data collected
        st.markdown("---") # Separator line
        st.header("Download Visualized Data")

        # 1. Combine all collected data (long format)
        final_df_long = pd.concat(processed_data_list, ignore_index=True)

        # 2. Pivot to wide format
        try:
            df_wide = final_df_long.pivot(index='Year', columns='Variable', values='Value')
        except Exception as e:
            # Handle potential duplicate Year-Variable pairs if logic upstream changes
            st.error(f"Error pivoting data for download: {e}. Using long format instead.")
            df_wide = final_df_long # Fallback to long format if pivot fails

        if 'Year' not in df_wide.columns: # If pivot was successful, Year is the index
             df_wide = df_wide.reset_index() # Make Year a column

        # 3. Add Country column
        df_wide['Country'] = selected_country

        # 4. Reorder columns: Year, Country, then variables in the specified order
        # Get the variable columns actually present after pivoting and filtering
        present_vars_in_order = [var for var in VARIABLE_ORDER if var in df_wide.columns]
        # Define final column order
        final_column_order = ['Year', 'Country'] + present_vars_in_order
        # Select and reorder
        df_wide_download = df_wide[final_column_order]


        # Prepare filenames
        country_short = selected_country.split(" ")[0].replace(",", "").replace("(", "").replace(")", "")
        filename_base = f"{country_short}_{transformation.replace(' (%)','_pct').replace(' ','_')}_{start_year}_{end_year}_wide"

        col1, col2 = st.columns(2)

        with col1:
            # CSV Download Button
            csv_data = df_wide_download.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Data as CSV (Wide)",
                data=csv_data,
                file_name=f"{filename_base}.csv",
                mime='text/csv',
            )

        with col2:
            # Stata Download Button
            stata_buffer = io.BytesIO()
            try:
                # Clean column names for Stata compatibility (basic cleaning)
                clean_columns = {col: col.replace('(','').replace(')','').replace('.','').replace('$','').replace('%','pct').replace(' ','_')[:32] for col in df_wide_download.columns}
                df_stata_download = df_wide_download.rename(columns=clean_columns)

                df_stata_download.to_stata(stata_buffer, write_index=False, version=118)
                stata_buffer.seek(0)
                st.download_button(
                    label="Download Data as Stata (Wide, .dta)",
                    data=stata_buffer,
                    file_name=f"{filename_base}.dta",
                    mime='application/octet-stream',
                 )
            except Exception as e:
                 st.error(f"Could not generate Stata file: {e}")
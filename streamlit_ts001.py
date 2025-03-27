import streamlit as st
import pandas as pd
import plotly.express as px
import io # Needed for reading uploaded file

st.set_page_config(layout="wide")
st.title("Interactive Time Series Visualization")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload your 'growthAccounting.csv' file", type=["csv"])

if uploaded_file is not None:
    try:
        # Read the uploaded CSV data
        # Use io.StringIO to treat the byte string as a text file
        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        df = pd.read_csv(stringio)

        st.header("Data Preview")
        st.dataframe(df.head())

        # --- Data Preparation ---

        # Get unique countries for selection
        country_list = df['Country'].unique()

        # --- Sidebar for User Input ---
        st.sidebar.header("Filters")
        selected_country = st.sidebar.selectbox(
            "Select Country",
            country_list,
            index=list(country_list).index('Bolivia (Plurinational State of)') if 'Bolivia (Plurinational State of)' in country_list else 0 # Default to Bolivia if exists
        )

        # Filter dataframe for the selected country
        df_country = df[df['Country'] == selected_country].copy() # Use .copy() to avoid SettingWithCopyWarning

        # Identify year columns (assuming they start from 1950 or similar)
        year_columns = [col for col in df.columns if col.isdigit() and len(col) == 4]
        # Make sure they are sorted correctly as strings
        year_columns.sort()

        # Get available variables for the selected country
        available_variables = df_country['Variable name'].unique()

        # Select variables to plot
        selected_variables = st.sidebar.multiselect(
            "Select Variables to Plot",
            available_variables,
            default=available_variables # Default to all variables
        )

        # --- Plotting ---
        st.header(f"Time Series Data for {selected_country}")

        if selected_variables:
            # Prepare data for plotting: Melt the dataframe for Plotly Express
            plot_data_list = []
            for var_name in selected_variables:
                df_variable = df_country[df_country['Variable name'] == var_name]
                if not df_variable.empty:
                    # Extract the specific row for the variable
                    data_row = df_variable.iloc[0]
                    # Convert year columns to numeric, coercing errors, fill NaNs
                    time_series = pd.to_numeric(data_row[year_columns], errors='coerce').fillna(0)
                    # Create a temporary dataframe for this variable
                    temp_df = pd.DataFrame({
                        'Year': pd.to_datetime(year_columns, format='%Y'), # Convert years to datetime objects for better axis handling
                        'Value': time_series.values,
                        'Variable': var_name # Add variable name for coloring/legend
                    })
                    plot_data_list.append(temp_df)

            if plot_data_list:
                # Combine data for all selected variables
                plot_df = pd.concat(plot_data_list)

                # Create the plot using Plotly Express
                fig = px.line(
                    plot_df,
                    x='Year',
                    y='Value',
                    color='Variable', # Color lines by variable name
                    title=f"Selected Variables for {selected_country}",
                    markers=True # Optional: Add markers to points
                )

                fig.update_layout(
                    xaxis_title="Year",
                    yaxis_title="Value",
                    legend_title="Variable",
                    height=600 # Adjust height as needed
                )

                # Display the plot in Streamlit
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No data available for the selected variables.")

        else:
            st.warning("Please select at least one variable to plot.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.error("Please ensure the uploaded file is a correctly formatted CSV with the expected columns (ISO code, Country, Variable code, Variable name, Year columns).")

else:
    st.info("Please upload the 'growthAccounting.csv' file to begin.")
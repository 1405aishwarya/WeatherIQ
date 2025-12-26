import streamlit as st
import pandas as pd
import s3fs
import plotly.express as px

# -----------------------------
# S3 / MinIO Connection Setup
# -----------------------------
fs = s3fs.S3FileSystem(
    client_kwargs={'endpoint_url': 'http://localhost:9000'},
    key='minioadmin',
    secret='minioadmin'
)

# -----------------------------
# Discover Parquet Files
# -----------------------------
all_files = fs.find("climate-lakehouse/gold/daily")
all_files = [f for f in all_files if f.endswith(".parquet")]

# -----------------------------
# Load Data
# -----------------------------
dfs = []
for file_path in all_files:
    try:
        df_part = pd.read_parquet(file_path, filesystem=fs)
        dfs.append(df_part)
    except Exception as e:
        st.error(f"Error reading {file_path}: {e}")

if not dfs:
    st.error("No data found in the gold layer!")
else:
    df = pd.concat(dfs, ignore_index=True)

    # Ensure date column is datetime and sort
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # -----------------------------
    # Streamlit Dashboard
    # -----------------------------
    st.set_page_config(page_title="ClimateSense Weather Dashboard", layout="wide")
    
    st.title("ClimateSense Weather Dashboard - Delhi")
    
    # Two-column layout for charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Daily Average Temperature (°C)")
        fig_temp = px.line(
            df, x="date", y="avg_temp",
            title="Daily Average Temperature",
            color_discrete_sequence=["#FF5733"]  # professional orange/red
        )
        fig_temp.update_layout(
            xaxis_title="Date",
            yaxis_title="Temperature (°C)",
            template="plotly_white"
        )
        st.plotly_chart(fig_temp, use_container_width=True)
    
    with col2:
        st.subheader("Daily Average Humidity (%)")
        fig_humidity = px.line(
            df, x="date", y="avg_humidity",
            title="Daily Average Humidity",
            color_discrete_sequence=["#1F77B4"]  # professional blue
        )
        fig_humidity.update_layout(
            xaxis_title="Date",
            yaxis_title="Humidity (%)",
            template="plotly_white"
        )
        st.plotly_chart(fig_humidity, use_container_width=True)
    
    # Metrics Table
    st.subheader("Daily Metrics Table (Last 30 Days)")
    st.dataframe(df.tail(30), use_container_width=True)
    
    st.success(f"Loaded {len(df)} daily records successfully.")

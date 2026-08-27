import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from storage_utils import read_parquet_dataset


st.set_page_config(page_title="WeatherIQ | Weather Intelligence", page_icon="W", layout="wide")
st.markdown("""
<style>
.stApp { background: #f6f8fc; color: #16243a; }
[data-testid="stSidebar"] { background: #10233f; }
[data-testid="stSidebar"] * { color: #f7faff; }
.hero { padding: 0.5rem 0 1.25rem; }
.brand { color: #1261c9; font-size: 2.45rem; font-weight: 750; letter-spacing: -0.08rem; margin: 0; }
.tagline { color: #65758b; font-size: 1rem; }
.eyebrow { color: #1261c9; font-size: 0.74rem; font-weight: 700; letter-spacing: 0.11rem; text-transform: uppercase; }
div[data-testid="stMetric"] { background: white; border: 1px solid #e4eaf2; border-radius: 13px; padding: 1rem; box-shadow: 0 3px 12px rgba(29, 53, 87, 0.05); }
div[data-testid="stMetricLabel"] { color: #64748b; }
div[data-testid="stMetricValue"] { color: #142b4a; }
.section-title { margin: 1.55rem 0 0.55rem; color: #142b4a; font-size: 1.18rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data(prefix: str) -> pd.DataFrame:
    return read_parquet_dataset(prefix)


def load_optional_data(prefix: str) -> pd.DataFrame:
    try:
        return load_data(prefix)
    except FileNotFoundError:
        return pd.DataFrame()


try:
    weather = load_data("gold/daily")
except FileNotFoundError:
    st.error("No Gold data found. Run ingestion, Bronze to Silver, then Silver to Gold first.")
    st.stop()

weather["date"] = pd.to_datetime(weather["date"])
weather = weather.dropna(subset=["city", "date"]).sort_values("date")
if weather.empty:
    st.warning("Gold data exists, but it has no usable city and date records.")
    st.stop()

anomalies = load_optional_data("anomalies")
if not anomalies.empty:
    anomalies["date"] = pd.to_datetime(anomalies["date"])
forecasts = load_optional_data("forecasts")
if not forecasts.empty:
    forecasts["forecast_date"] = pd.to_datetime(forecasts["forecast_date"])

with st.sidebar:
    st.markdown("## WeatherIQ")
    st.caption("WEATHER INTELLIGENCE PLATFORM")
    st.divider()
    cities = sorted(weather["city"].unique())
    selected_city = st.selectbox("Location", cities)
    min_date = weather["date"].min().date()
    max_date = weather["date"].max().date()
    selected_dates = st.date_input("Analysis period", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    st.divider()
    st.caption("DATA STATUS")
    st.success(f"{len(cities)} locations connected")
    st.caption(f"Last observation: {max_date:%d %b %Y}")
    if st.button("Refresh data", width="stretch"):
        st.cache_data.clear()
        st.rerun()

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = map(pd.Timestamp, selected_dates)
else:
    start_date = end_date = pd.Timestamp(selected_dates)

city_weather = weather.loc[
    (weather["city"] == selected_city)
    & (weather["date"] >= start_date)
    & (weather["date"] <= end_date)
].sort_values("date")
if city_weather.empty:
    st.warning("No observations exist for this location in the selected period.")
    st.stop()

latest = city_weather.iloc[-1]
city_anomalies = anomalies.loc[(anomalies["city"] == selected_city) & anomalies["is_anomaly"]] if not anomalies.empty else pd.DataFrame()
city_forecasts = forecasts.loc[forecasts["city"] == selected_city].sort_values("forecast_date") if not forecasts.empty else pd.DataFrame()
freshness_days = max((pd.Timestamp.now().normalize() - weather["date"].max().normalize()).days, 0)

st.markdown(f"""<div class="hero"><div class="eyebrow">Operational weather analytics</div><p class="brand">WeatherIQ</p><div class="tagline">{selected_city} performance overview | {start_date:%d %b %Y} to {end_date:%d %b %Y}</div></div>""", unsafe_allow_html=True)

kpi_1, kpi_2, kpi_3, kpi_4, kpi_5 = st.columns(5)
kpi_1.metric("Temperature", f"{latest['avg_temp']:.1f} C")
kpi_2.metric("Humidity", f"{latest['avg_humidity']:.0f}%")
kpi_3.metric("Pressure", f"{latest['avg_pressure']:.0f} hPa")
kpi_4.metric("Wind speed", f"{latest['avg_wind_speed']:.1f} km/h")
kpi_5.metric("Data freshness", "Current" if freshness_days == 0 else f"{freshness_days}d old")

chart_layout = {"template": "plotly_white", "margin": {"l": 12, "r": 12, "t": 46, "b": 12}, "paper_bgcolor": "white", "plot_bgcolor": "white", "font": {"color": "#30445f"}, "hovermode": "x unified"}
st.markdown('<div class="section-title">Weather trends</div>', unsafe_allow_html=True)
left, right = st.columns(2)
with left:
    temperature = go.Figure()
    temperature.add_scatter(x=city_weather["date"], y=city_weather["avg_temp"], mode="lines+markers", name="Observed", line={"color": "#1261c9", "width": 3}, marker={"size": 7})
    if not city_anomalies.empty:
        temperature.add_scatter(x=city_anomalies["date"], y=city_anomalies["avg_temp"], mode="markers", name="Anomaly", marker={"color": "#e65252", "size": 11, "symbol": "diamond"})
    if not city_forecasts.empty:
        temperature.add_scatter(x=city_forecasts["forecast_date"], y=city_forecasts["forecast_temp"], mode="lines+markers", name="Forecast", line={"color": "#8d5cf6", "width": 2, "dash": "dash"}, marker={"size": 6})
    temperature.update_layout(title="Average temperature", yaxis_title="Celsius", **chart_layout)
    st.plotly_chart(temperature, width="stretch")
with right:
    humidity = go.Figure()
    humidity.add_scatter(x=city_weather["date"], y=city_weather["avg_humidity"], mode="lines+markers", name="Humidity", fill="tozeroy", line={"color": "#17a2a4", "width": 3}, marker={"size": 7}, fillcolor="rgba(23,162,164,0.13)")
    humidity.update_layout(title="Average humidity", yaxis_title="Percent", yaxis={"range": [0, 100]}, **chart_layout)
    st.plotly_chart(humidity, width="stretch")

left, right = st.columns(2)
with left:
    pressure_wind = go.Figure()
    pressure_wind.add_scatter(x=city_weather["date"], y=city_weather["avg_pressure"], mode="lines+markers", name="Pressure", line={"color": "#f59e0b", "width": 3})
    pressure_wind.add_scatter(x=city_weather["date"], y=city_weather["avg_wind_speed"], mode="lines+markers", name="Wind speed", yaxis="y2", line={"color": "#52677f", "width": 3})
    pressure_wind.update_layout(title="Pressure and wind", yaxis_title="hPa", yaxis2={"title": "km/h", "overlaying": "y", "side": "right"}, **chart_layout)
    st.plotly_chart(pressure_wind, width="stretch")
with right:
    latest_by_city = weather.sort_values("date").groupby("city", as_index=False).tail(1).sort_values("avg_temp")
    comparison = px.bar(latest_by_city, x="avg_temp", y="city", orientation="h", color="avg_temp", color_continuous_scale=["#9ec5fe", "#1261c9"], labels={"avg_temp": "Temperature (Celsius)", "city": ""})
    comparison.update_layout(title="Latest temperature by location", coloraxis_showscale=False, showlegend=False, **chart_layout)
    st.plotly_chart(comparison, width="stretch")

st.markdown('<div class="section-title">Latest observations</div>', unsafe_allow_html=True)
display_columns = ["date", "city", "avg_temp", "avg_humidity", "avg_pressure", "avg_wind_speed"]
table = city_weather[display_columns].sort_values("date", ascending=False).rename(columns={"avg_temp": "Temperature (Celsius)", "avg_humidity": "Humidity (%)", "avg_pressure": "Pressure (hPa)", "avg_wind_speed": "Wind speed (km/h)"})
st.dataframe(table, width="stretch", hide_index=True)
export_data = table.to_csv(index=False).encode("utf-8")
export_left, export_right = st.columns([1, 3])
with export_left:
    st.download_button("Export CSV", data=export_data, file_name=f"weatheriq_{selected_city.lower().replace(' ', '_')}.csv", mime="text/csv", width="stretch")
with export_right:
    if len(city_anomalies):
        st.warning(f"{len(city_anomalies)} anomaly record(s) detected for {selected_city} in the selected period.")
    else:
        st.success("No anomaly records detected for this location and period.")

if len(city_weather) < 7:
    st.info(f"WeatherIQ has {len(city_weather)} daily observation(s) for {selected_city}. Seven days are needed to produce a forecast.")
elif len(city_weather) < 10:
    st.info("Seven-day history is available for forecasting; collect 10 days to enable anomaly detection.")

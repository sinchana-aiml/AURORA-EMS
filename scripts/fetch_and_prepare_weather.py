import requests
import pandas as pd


# NASA POWER API endpoint
url = "https://power.larc.nasa.gov/api/temporal/hourly/point"


# Request parameters
params = {
    "parameters": "T2M,WS10M,ALLSKY_SFC_SW_DWN,PRECTOTCORR,PS",
    "community": "RE",
    "longitude": 76.1956,
    "latitude": -69.4069,
    "start": "20150101",
    "end": "20150107",
    "format": "JSON",
    "time-standard": "UTC",
}


# Request data from NASA POWER
response = requests.get(url, params=params)

print("Status:", response.status_code)

# Stop if the API request failed
response.raise_for_status()

# Convert API response to JSON
data = response.json()

print("NASA POWER API connection successful!")


# Extract weather parameters
parameters = data["properties"]["parameter"]


# Convert NASA response into a Pandas DataFrame
df = pd.DataFrame(parameters)


# Convert NASA timestamps into proper UTC datetime values
df.index = pd.to_datetime(
    df.index,
    format="%Y%m%d%H",
    utc=True
)


# Rename NASA parameter codes
df = df.rename(columns={
    "T2M": "temperature_c",
    "WS10M": "wind_speed_mps",
    "ALLSKY_SFC_SW_DWN": "solar_irradiance_wm2",
    "PRECTOTCORR": "precipitation_mm",
    "PS": "surface_pressure_kpa",
})


# Give the timestamp index a name
df.index.name = "timestamp_utc"


# -----------------------------
# Data validation
# -----------------------------

print("\n--- Data Validation ---")


# 1. Check for duplicate timestamps
duplicate_count = df.index.duplicated().sum()

print("Duplicate timestamps:", duplicate_count)


# 2. Check for missing values
print("\nMissing values:")
print(df.isna().sum())


# 3. Check for physically invalid values
invalid_temperature = (
    (df["temperature_c"] < -100)
    | (df["temperature_c"] > 60)
)

invalid_wind = (
    df["wind_speed_mps"] < 0
)

invalid_solar = (
    df["solar_irradiance_wm2"] < 0
)

invalid_precipitation = (
    df["precipitation_mm"] < 0
)

invalid_pressure = (
    df["surface_pressure_kpa"] <= 0
)


print("\nInvalid values:")
print("Temperature:", invalid_temperature.sum())
print("Wind speed:", invalid_wind.sum())
print("Solar irradiance:", invalid_solar.sum())
print("Precipitation:", invalid_precipitation.sum())
print("Surface pressure:", invalid_pressure.sum())


# 4. Check whether timestamps are hourly
time_difference = df.index.to_series().diff().dropna()

non_hourly = (
    time_difference != pd.Timedelta(hours=1)
).sum()

print("\nNon-hourly timestamp gaps:", non_hourly)


# -----------------------------
# Weather quality flag
# -----------------------------

df["weather_quality_flag"] = "good"


# Mark rows with missing values
missing_rows = df[
    [
        "temperature_c",
        "wind_speed_mps",
        "solar_irradiance_wm2",
        "precipitation_mm",
        "surface_pressure_kpa",
    ]
].isna().any(axis=1)

df.loc[missing_rows, "weather_quality_flag"] = "missing"


# Mark rows with physically invalid values
invalid_rows = (
    invalid_temperature
    | invalid_wind
    | invalid_solar
    | invalid_precipitation
    | invalid_pressure
)

df.loc[
    invalid_rows & ~missing_rows,
    "weather_quality_flag"
] = "review"


# Display quality summary
print("\nWeather quality summary:")
print(df["weather_quality_flag"].value_counts())


# -----------------------------
# Display final test DataFrame
# -----------------------------

print("\nDataFrame created successfully!")

print("\nFirst 5 rows:")
print(df.head())

print("\nShape:")
print(df.shape)

print("\nColumns:")
print(df.columns.tolist())
import requests

url = "https://power.larc.nasa.gov/api/temporal/hourly/point"

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

response = requests.get(url, params=params)

print("Status:", response.status_code)

data = response.json()

print("NASA POWER API connection successful!")

parameters = data["properties"]["parameter"]

for parameter, values in parameters.items():
    print(f"\n{parameter}")
    print(list(values.items())[:3])
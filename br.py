# -*- coding: utf-8 -*-

#https://github.com/mjj4791/python-buienradar
#sudo pip3 install buienradar --break-system-packages

from buienradar.buienradar import get_data, parse_data

# Coordinates for Best
lat, lon = 51.5078, 5.3978
# Coordinates for Leticia, Brazil 
#lat, lon = -5.811, -71.570

# Fetch and parse data
result = get_data(latitude=lat, longitude=lon)
data = parse_data(result['content'], result['raincontent'], lat, lon)

# Access current values
current = data['data']
print(f"Stationname: {current['stationname']}")
print(f"Temperature: {current['temperature']} C")
print(f"Wind Speed: {current['windspeed']} m/s")
print(f"Wind Direction: {current['winddirection']}")
print(f"Wind Direction: {current['windazimuth']} degrees")
print(f"Precipitation: {current['precipitation']} mm/h")
print(f"Forecast: {current['forecast'][0]['condition']['condition']}")

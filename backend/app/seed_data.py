"""
ILLUSTRATIVE SAMPLE DATA — see db.py docstring.

Airport identity/geography/hub class: real.
Traffic, capacity, delay, gate/runway counts: approximations shaped like the
BTS T-100 / On-Time and FAA ASPM/ATADS series, rounded and not audited.
Route flight counts: illustrative. Route distances are computed (haversine).
"""

# (code, name, city, state, region, lat, lon, hub_size)
_A = [
    ("BOS", "Logan International", "Boston", "MA", "New England", 42.3656, -71.0096, "large"),
    ("PVD", "T. F. Green International", "Providence", "RI", "New England", 41.7240, -71.4283, "small"),
    ("BDL", "Bradley International", "Hartford", "CT", "New England", 41.9389, -72.6832, "medium"),
    ("MHT", "Manchester-Boston Regional", "Manchester", "NH", "New England", 42.9326, -71.4357, "small"),
    ("PWM", "Portland International Jetport", "Portland", "ME", "New England", 43.6462, -70.3093, "small"),
    ("BTV", "Burlington International", "Burlington", "VT", "New England", 44.4719, -73.1533, "small"),
    ("JFK", "John F. Kennedy International", "New York", "NY", "Mid-Atlantic", 40.6413, -73.7781, "large"),
    ("EWR", "Newark Liberty International", "Newark", "NJ", "Mid-Atlantic", 40.6895, -74.1745, "large"),
    ("LAX", "Los Angeles International", "Los Angeles", "CA", "West Coast", 33.9416, -118.4085, "large"),
    ("SNA", "John Wayne Airport", "Santa Ana", "CA", "West Coast", 33.6757, -117.8682, "medium"),
    ("SFO", "San Francisco International", "San Francisco", "CA", "West Coast", 37.6213, -122.3790, "large"),
    ("OAK", "Oakland International", "Oakland", "CA", "West Coast", 37.7126, -122.2197, "medium"),
    ("SJC", "San Jose Mineta International", "San Jose", "CA", "West Coast", 37.3639, -121.9289, "medium"),
    ("SEA", "Seattle-Tacoma International", "Seattle", "WA", "West Coast", 47.4502, -122.3088, "large"),
    ("ANC", "Ted Stevens Anchorage International", "Anchorage", "AK", "Alaska", 61.1743, -149.9982, "medium"),
    ("ORD", "O'Hare International", "Chicago", "IL", "Midwest", 41.9742, -87.9073, "large"),
    ("DFW", "Dallas/Fort Worth International", "Dallas", "TX", "South", 32.8998, -97.0403, "large"),
    ("DEN", "Denver International", "Denver", "CO", "Mountain", 39.8561, -104.6737, "large"),
    ("ATL", "Hartsfield-Jackson Atlanta", "Atlanta", "GA", "South", 33.6407, -84.4277, "large"),
    ("MIA", "Miami International", "Miami", "FL", "South", 25.7959, -80.2870, "large"),
]
AIRPORTS = [
    dict(code=c, name=n, city=ci, state=st, region=r, lat=la, lon=lo, hub_size=h)
    for c, n, ci, st, r, la, lo, h in _A
]

# Destinations that are not themselves in AIRPORTS (for route distance calc).
DEST_COORDS = {
    "MSP": (44.8848, -93.2223), "HNL": (21.3187, -157.9225), "FRA": (50.0379, 8.5622),
    "FAI": (64.8151, -147.8563), "JNU": (58.3550, -134.5763), "LHR": (51.4700, -0.4543),
    "CDG": (49.0097, 2.5479), "NRT": (35.7720, 140.3929), "ICN": (37.4602, 126.4407),
    "SYD": (-33.9399, 151.1753), "DCA": (38.8512, -77.0402), "MCO": (28.4312, -81.3081),
    "LAS": (36.0840, -115.1537), "PHX": (33.4373, -112.0078), "PHL": (39.8729, -75.2437),
    "CLT": (35.2144, -80.9473), "IAD": (38.9531, -77.4565), "MEX": (19.4363, -99.0721),
    "CUN": (21.0365, -86.8771), "GRU": (-23.4356, -46.4731), "DXB": (25.2532, 55.3657),
    "TLV": (32.0055, 34.8854), "LIM": (-12.0219, -77.1143), "BOG": (4.7016, -74.1469),
    "YYZ": (43.6777, -79.6248), "PDX": (45.5898, -122.5951), "SLC": (40.7899, -111.9791),
    "IAH": (29.9902, -95.3368), "BWI": (39.1774, -76.6684), "LGA": (40.7769, -73.8740),
    "SAN": (32.7338, -117.1933), "DTW": (42.2162, -83.3554), "TPA": (27.9772, -82.5311),
    "FLL": (26.0742, -80.1506), "MDW": (41.7868, -87.7522), "HKG": (22.3080, 113.9185),
    "PVG": (31.1443, 121.8083), "TPE": (25.0797, 121.2342), "DOH": (25.2609, 51.6138),
    "AMS": (52.3105, 4.7683), "DUB": (53.4264, -6.2499), "KEF": (63.9850, -22.6056),
    "CHS": (32.8986, -80.0405), "RDU": (35.8801, -78.7880), "BNA": (36.1263, -86.6774),
    "SAV": (32.1276, -81.2021), "ORF": (36.8946, -76.2012), "SJU": (18.4394, -66.0018),
    "AUS": (30.1975, -97.6664), "SMF": (38.6954, -121.5908), "SCL": (-33.3930, -70.7858),
    "EZE": (-34.8222, -58.5358), "MAD": (40.4983, -3.5676), "PEK": (40.0799, 116.6031),
}

# (airport_code, year, passengers, seats, operations, capacity_ops, on_time_pct, avg_delay_min, gates, runways)
_M = [
    ("BOS", 2024, 42_500_000, 50_000_000, 400_000, 470_000, 75.0, 13.0, 100, 6),
    ("BOS", 2025, 44_600_000, 51_800_000, 412_000, 470_000, 74.2, 13.8, 100, 6),
    ("PVD", 2024, 4_100_000, 5_000_000, 60_000, 200_000, 79.0, 10.0, 22, 2),
    ("PVD", 2025, 4_430_000, 5_300_000, 64_000, 200_000, 78.5, 10.2, 22, 2),
    ("BDL", 2024, 7_000_000, 8_500_000, 90_000, 250_000, 78.0, 10.5, 24, 2),
    ("BDL", 2025, 7_420_000, 8_900_000, 94_000, 250_000, 77.8, 10.6, 24, 2),
    ("MHT", 2024, 1_500_000, 2_000_000, 40_000, 180_000, 80.0, 9.0, 14, 2),
    ("MHT", 2025, 1_545_000, 2_050_000, 40_500, 180_000, 80.3, 8.9, 14, 2),
    ("PWM", 2024, 2_300_000, 2_800_000, 45_000, 150_000, 78.0, 10.0, 11, 2),
    ("PWM", 2025, 2_460_000, 2_950_000, 47_500, 150_000, 77.5, 10.4, 11, 2),
    ("BTV", 2024, 800_000, 1_050_000, 50_000, 140_000, 77.0, 11.0, 15, 2),
    ("BTV", 2025, 816_000, 1_070_000, 50_500, 140_000, 77.2, 10.9, 15, 2),
    ("JFK", 2024, 63_000_000, 75_000_000, 470_000, 520_000, 74.0, 14.0, 128, 4),
    ("JFK", 2025, 65_500_000, 77_000_000, 480_000, 520_000, 73.5, 14.4, 128, 4),
    ("EWR", 2024, 48_000_000, 56_000_000, 430_000, 460_000, 68.0, 19.0, 125, 3),
    ("EWR", 2025, 49_400_000, 57_200_000, 436_000, 460_000, 67.0, 19.8, 125, 3),
    ("LAX", 2024, 76_000_000, 90_500_000, 590_000, 700_000, 76.0, 13.0, 146, 4),
    ("LAX", 2025, 76_800_000, 91_000_000, 592_000, 700_000, 76.2, 12.9, 146, 4),
    ("SNA", 2024, 11_700_000, 13_300_000, 122_000, 140_000, 82.0, 8.0, 20, 2),
    ("SNA", 2025, 12_400_000, 13_900_000, 126_000, 140_000, 81.5, 8.3, 20, 2),
    ("SFO", 2024, 52_000_000, 59_800_000, 400_000, 430_000, 72.0, 16.0, 115, 4),
    ("SFO", 2025, 54_100_000, 61_500_000, 410_000, 430_000, 71.0, 16.8, 115, 4),
    ("OAK", 2024, 11_000_000, 13_400_000, 220_000, 350_000, 80.0, 9.0, 32, 4),
    ("OAK", 2025, 10_670_000, 13_100_000, 214_000, 350_000, 80.5, 8.8, 32, 4),
    ("SJC", 2024, 12_000_000, 14_600_000, 170_000, 300_000, 81.0, 8.0, 30, 3),
    ("SJC", 2025, 12_240_000, 14_800_000, 172_000, 300_000, 81.0, 8.1, 30, 3),
    ("SEA", 2024, 52_000_000, 61_200_000, 430_000, 480_000, 77.0, 12.0, 115, 3),
    ("SEA", 2025, 54_100_000, 63_000_000, 440_000, 480_000, 76.4, 12.5, 115, 3),
    ("ANC", 2024, 5_500_000, 6_900_000, 250_000, 400_000, 82.0, 8.0, 40, 3),
    ("ANC", 2025, 5_665_000, 7_050_000, 254_000, 400_000, 82.1, 8.0, 40, 3),
    ("ORD", 2024, 80_000_000, 97_500_000, 780_000, 1_000_000, 74.0, 14.0, 190, 8),
    ("ORD", 2025, 83_200_000, 100_500_000, 800_000, 1_000_000, 73.8, 14.2, 190, 8),
    ("DFW", 2024, 87_000_000, 105_000_000, 720_000, 1_000_000, 78.0, 11.0, 174, 7),
    ("DFW", 2025, 91_350_000, 109_000_000, 748_000, 1_000_000, 77.6, 11.3, 174, 7),
    ("DEN", 2024, 82_000_000, 98_800_000, 660_000, 900_000, 76.0, 12.0, 180, 6),
    ("DEN", 2025, 86_900_000, 103_500_000, 690_000, 900_000, 75.5, 12.4, 180, 6),
    ("ATL", 2024, 108_000_000, 127_000_000, 780_000, 950_000, 79.0, 10.0, 195, 5),
    ("ATL", 2025, 111_200_000, 130_000_000, 795_000, 950_000, 78.8, 10.1, 195, 5),
    ("MIA", 2024, 55_000_000, 66_300_000, 430_000, 600_000, 76.0, 13.0, 130, 4),
    ("MIA", 2025, 58_900_000, 69_800_000, 452_000, 600_000, 75.4, 13.5, 130, 4),
]
METRICS = [
    dict(airport_code=c, year=y, passengers=p, seats=s, operations=o, capacity_ops=cap,
         on_time_pct=ot, avg_delay_min=d, gates=g, runways=r)
    for c, y, p, s, o, cap, ot, d, g, r in _M
]

# (origin, dest, dest_name, annual_flights, international)
ROUTES = [
    # New England
    ("BOS", "LGA", "New York LaGuardia", 14_000, 0), ("BOS", "DCA", "Washington National", 11_000, 0),
    ("BOS", "ORD", "Chicago O'Hare", 9_500, 0), ("BOS", "ATL", "Atlanta", 8_000, 0),
    ("BOS", "LAX", "Los Angeles", 5_200, 0), ("BOS", "SFO", "San Francisco", 4_600, 0),
    ("BOS", "LHR", "London Heathrow", 3_900, 1), ("BOS", "CDG", "Paris CDG", 1_500, 1),
    ("BOS", "DUB", "Dublin", 1_400, 1), ("BOS", "DOH", "Doha", 730, 1), ("BOS", "TLV", "Tel Aviv", 700, 1),
    ("PVD", "BWI", "Baltimore", 2_600, 0), ("PVD", "MCO", "Orlando", 2_200, 0), ("PVD", "CLT", "Charlotte", 1_500, 0),
    ("PVD", "PHL", "Philadelphia", 1_800, 0), ("PVD", "DCA", "Washington National", 1_400, 0), ("PVD", "FLL", "Fort Lauderdale", 1_200, 0),
    ("BDL", "ATL", "Atlanta", 2_600, 0), ("BDL", "CLT", "Charlotte", 2_400, 0), ("BDL", "ORD", "Chicago O'Hare", 2_500, 0),
    ("BDL", "DCA", "Washington National", 2_100, 0), ("BDL", "MCO", "Orlando", 2_000, 0), ("BDL", "LAX", "Los Angeles", 730, 0),
    ("BDL", "DUB", "Dublin", 365, 1),
    ("MHT", "ORD", "Chicago O'Hare", 1_500, 0), ("MHT", "PHL", "Philadelphia", 1_100, 0), ("MHT", "BWI", "Baltimore", 1_300, 0),
    ("MHT", "MCO", "Orlando", 900, 0), ("MHT", "ATL", "Atlanta", 800, 0),
    ("PWM", "PHL", "Philadelphia", 1_400, 0), ("PWM", "CLT", "Charlotte", 1_200, 0), ("PWM", "ORD", "Chicago O'Hare", 1_300, 0),
    ("PWM", "DCA", "Washington National", 1_100, 0), ("PWM", "ATL", "Atlanta", 900, 0), ("PWM", "JFK", "New York JFK", 1_000, 0),
    ("BTV", "PHL", "Philadelphia", 900, 0), ("BTV", "ORD", "Chicago O'Hare", 800, 0), ("BTV", "DCA", "Washington National", 900, 0),
    ("BTV", "JFK", "New York JFK", 1_000, 0), ("BTV", "ATL", "Atlanta", 500, 0),
    # NYC
    ("JFK", "LAX", "Los Angeles", 14_000, 0), ("JFK", "SFO", "San Francisco", 8_500, 0), ("JFK", "MIA", "Miami", 9_000, 0),
    ("JFK", "BOS", "Boston", 8_000, 0), ("JFK", "LHR", "London Heathrow", 9_200, 1), ("JFK", "CDG", "Paris CDG", 4_400, 1),
    ("JFK", "TLV", "Tel Aviv", 2_900, 1), ("JFK", "NRT", "Tokyo Narita", 1_500, 1), ("JFK", "DXB", "Dubai", 1_460, 1),
    ("JFK", "GRU", "São Paulo", 1_800, 1), ("JFK", "MAD", "Madrid", 2_200, 1), ("JFK", "HKG", "Hong Kong", 1_100, 1),
    ("EWR", "ORD", "Chicago O'Hare", 8_000, 0), ("EWR", "LAX", "Los Angeles", 7_500, 0), ("EWR", "SFO", "San Francisco", 6_200, 0),
    ("EWR", "MCO", "Orlando", 6_000, 0), ("EWR", "LHR", "London Heathrow", 6_500, 1), ("EWR", "FRA", "Frankfurt", 2_200, 1),
    ("EWR", "TLV", "Tel Aviv", 2_500, 1), ("EWR", "DXB", "Dubai", 730, 1), ("EWR", "PEK", "Beijing", 700, 1),
    # West Coast
    ("LAX", "SFO", "San Francisco", 18_000, 0), ("LAX", "JFK", "New York JFK", 14_000, 0), ("LAX", "LAS", "Las Vegas", 15_000, 0),
    ("LAX", "SEA", "Seattle", 11_000, 0), ("LAX", "ORD", "Chicago O'Hare", 9_500, 0), ("LAX", "DFW", "Dallas/Fort Worth", 9_000, 0),
    ("LAX", "LHR", "London Heathrow", 5_800, 1), ("LAX", "NRT", "Tokyo Narita", 4_000, 1), ("LAX", "ICN", "Seoul Incheon", 3_800, 1),
    ("LAX", "SYD", "Sydney", 2_200, 1), ("LAX", "MEX", "Mexico City", 5_000, 1), ("LAX", "HKG", "Hong Kong", 2_600, 1),
    ("LAX", "TPE", "Taipei", 2_900, 1), ("LAX", "PVG", "Shanghai", 1_800, 1),
    ("SNA", "SFO", "San Francisco", 8_500, 0), ("SNA", "DEN", "Denver", 7_000, 0), ("SNA", "PHX", "Phoenix", 7_500, 0),
    ("SNA", "SEA", "Seattle", 6_500, 0), ("SNA", "DFW", "Dallas/Fort Worth", 5_500, 0), ("SNA", "ORD", "Chicago O'Hare", 3_600, 0),
    ("SNA", "SJC", "San Jose", 5_000, 0), ("SNA", "LAS", "Las Vegas", 6_000, 0), ("SNA", "MEX", "Mexico City", 730, 1),
    ("SFO", "LAX", "Los Angeles", 18_000, 0), ("SFO", "JFK", "New York JFK", 8_500, 0), ("SFO", "SEA", "Seattle", 12_000, 0),
    ("SFO", "ORD", "Chicago O'Hare", 9_000, 0), ("SFO", "DEN", "Denver", 8_500, 0), ("SFO", "LHR", "London Heathrow", 5_100, 1),
    ("SFO", "NRT", "Tokyo Narita", 3_600, 1), ("SFO", "HKG", "Hong Kong", 3_200, 1), ("SFO", "ICN", "Seoul Incheon", 2_500, 1),
    ("SFO", "FRA", "Frankfurt", 2_200, 1), ("SFO", "SYD", "Sydney", 1_500, 1), ("SFO", "TPE", "Taipei", 2_600, 1),
    ("SFO", "PVG", "Shanghai", 1_500, 1), ("SFO", "DXB", "Dubai", 730, 1),
    ("OAK", "LAS", "Las Vegas", 9_000, 0), ("OAK", "SAN", "San Diego", 7_000, 0), ("OAK", "SEA", "Seattle", 6_000, 0),
    ("OAK", "PDX", "Portland", 5_000, 0), ("OAK", "PHX", "Phoenix", 5_500, 0), ("OAK", "DEN", "Denver", 4_500, 0),
    ("OAK", "HNL", "Honolulu", 1_800, 0), ("OAK", "CUN", "Cancun", 400, 1),
    ("SJC", "LAS", "Las Vegas", 7_500, 0), ("SJC", "SAN", "San Diego", 7_000, 0), ("SJC", "SEA", "Seattle", 6_500, 0),
    ("SJC", "PHX", "Phoenix", 5_000, 0), ("SJC", "DEN", "Denver", 4_500, 0), ("SJC", "NRT", "Tokyo Narita", 730, 1),
    ("SJC", "HNL", "Honolulu", 1_500, 0), ("SJC", "MEX", "Mexico City", 700, 1),
    ("SEA", "LAX", "Los Angeles", 11_000, 0), ("SEA", "SFO", "San Francisco", 12_000, 0), ("SEA", "ANC", "Anchorage", 8_500, 0),
    ("SEA", "DEN", "Denver", 9_000, 0), ("SEA", "ORD", "Chicago O'Hare", 6_500, 0), ("SEA", "LHR", "London Heathrow", 2_500, 1),
    ("SEA", "NRT", "Tokyo Narita", 2_200, 1), ("SEA", "ICN", "Seoul Incheon", 1_800, 1), ("SEA", "AMS", "Amsterdam", 1_400, 1),
    ("SEA", "DOH", "Doha", 730, 1), ("SEA", "HKG", "Hong Kong", 700, 1),
    # Alaska
    ("ANC", "SEA", "Seattle", 8_500, 0), ("ANC", "FAI", "Fairbanks", 4_400, 0), ("ANC", "JNU", "Juneau", 3_600, 0),
    ("ANC", "PDX", "Portland", 2_200, 0), ("ANC", "MSP", "Minneapolis", 1_500, 0), ("ANC", "ORD", "Chicago O'Hare", 900, 0),
    ("ANC", "DFW", "Dallas/Fort Worth", 800, 0), ("ANC", "DEN", "Denver", 1_200, 0), ("ANC", "LAX", "Los Angeles", 1_100, 0),
    ("ANC", "HNL", "Honolulu", 750, 0), ("ANC", "FRA", "Frankfurt", 180, 1), ("ANC", "ICN", "Seoul Incheon", 220, 1),
    # Other hubs
    ("ORD", "LGA", "New York LaGuardia", 15_000, 0), ("ORD", "LAX", "Los Angeles", 9_500, 0), ("ORD", "DFW", "Dallas/Fort Worth", 10_000, 0),
    ("ORD", "DEN", "Denver", 9_500, 0), ("ORD", "SFO", "San Francisco", 9_000, 0), ("ORD", "LHR", "London Heathrow", 6_200, 1),
    ("ORD", "FRA", "Frankfurt", 2_600, 1), ("ORD", "NRT", "Tokyo Narita", 2_100, 1), ("ORD", "HKG", "Hong Kong", 900, 1),
    ("ORD", "MEX", "Mexico City", 3_000, 1), ("ORD", "YYZ", "Toronto", 6_000, 1),
    ("DFW", "ORD", "Chicago O'Hare", 10_000, 0), ("DFW", "LAX", "Los Angeles", 9_000, 0), ("DFW", "ATL", "Atlanta", 9_500, 0),
    ("DFW", "DEN", "Denver", 8_000, 0), ("DFW", "IAH", "Houston", 8_500, 0), ("DFW", "LHR", "London Heathrow", 3_600, 1),
    ("DFW", "NRT", "Tokyo Narita", 1_100, 1), ("DFW", "SYD", "Sydney", 730, 1), ("DFW", "MEX", "Mexico City", 5_000, 1),
    ("DFW", "DOH", "Doha", 730, 1), ("DFW", "GRU", "São Paulo", 730, 1),
    ("DEN", "ORD", "Chicago O'Hare", 9_500, 0), ("DEN", "LAX", "Los Angeles", 9_000, 0), ("DEN", "DFW", "Dallas/Fort Worth", 8_000, 0),
    ("DEN", "SEA", "Seattle", 9_000, 0), ("DEN", "PHX", "Phoenix", 8_500, 0), ("DEN", "SLC", "Salt Lake City", 7_000, 0),
    ("DEN", "LHR", "London Heathrow", 1_500, 1), ("DEN", "FRA", "Frankfurt", 730, 1), ("DEN", "NRT", "Tokyo Narita", 700, 1),
    ("DEN", "CUN", "Cancun", 2_000, 1),
    ("ATL", "LGA", "New York LaGuardia", 12_000, 0), ("ATL", "MCO", "Orlando", 11_000, 0), ("ATL", "DFW", "Dallas/Fort Worth", 9_500, 0),
    ("ATL", "LAX", "Los Angeles", 8_000, 0), ("ATL", "ORD", "Chicago O'Hare", 8_500, 0), ("ATL", "LHR", "London Heathrow", 4_400, 1),
    ("ATL", "CDG", "Paris CDG", 2_900, 1), ("ATL", "AMS", "Amsterdam", 2_200, 1), ("ATL", "GRU", "São Paulo", 1_100, 1),
    ("ATL", "ICN", "Seoul Incheon", 1_100, 1), ("ATL", "MEX", "Mexico City", 3_600, 1),
    ("MIA", "JFK", "New York JFK", 9_000, 0), ("MIA", "LGA", "New York LaGuardia", 8_000, 0), ("MIA", "ATL", "Atlanta", 7_500, 0),
    ("MIA", "DFW", "Dallas/Fort Worth", 6_000, 0), ("MIA", "LAX", "Los Angeles", 4_000, 0), ("MIA", "SJU", "San Juan", 5_500, 0),
    ("MIA", "BOG", "Bogotá", 4_400, 1), ("MIA", "LIM", "Lima", 3_000, 1), ("MIA", "GRU", "São Paulo", 2_600, 1),
    ("MIA", "LHR", "London Heathrow", 2_900, 1), ("MIA", "MAD", "Madrid", 2_200, 1), ("MIA", "EZE", "Buenos Aires", 1_800, 1),
    ("MIA", "SCL", "Santiago", 1_500, 1), ("MIA", "MEX", "Mexico City", 3_600, 1), ("MIA", "DOH", "Doha", 730, 1),
]

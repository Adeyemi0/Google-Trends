from pytrends.request import TrendReq
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
from requests.exceptions import ConnectionError, Timeout

data_dictionary = """
## Data Dictionary

### Raw Trends Data
- **Date**: Date for which the interest is measured (YYYY-MM-DD).
- **Keyword1, Keyword2, ...**: Interest score (0-100) for each keyword on the specified date.

### Classified Trends Data
- **Keyword**: The keyword being analyzed.
- **Mean**: Average interest score over the past five years.
- **Trend**: Percentage change in interest in the last year compared to the 5-year average.
- **Trend2**: Percentage change in interest in the last year compared to the first year.
- **Stability**: A categorical label indicating trend stability.

### Consolidated Interest by Region Data
- **geoName**: Geographic region name.
- **Keyword1, Keyword2, ...**: Interest score (0-100) for each keyword in the specified region.
"""

print("Data Dictionary:")
print(data_dictionary)

# Pytrends setup with increased timeout
pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))

# User input for country
country = input('Select country (Nigeria, United States, United Kingdom, India, Australia): ')
geo_dict = {'Nigeria': 'NG', 'United States': 'US', 'United Kingdom': 'GB', 'India': 'IN', 'Australia': 'AU'}
geo = geo_dict.get(country)

# Keywords input
keywords_input = input("Enter keywords separated by commas (e.g., business funding, small business, SMEs): ")
keywords = [kw.strip() for kw in keywords_input.split(',') if kw.strip()]

# Retry function for Pytrends requests
def retry_request(pytrends, kw, retries=5):
    for attempt in range(retries):
        try:
            pytrends.build_payload([kw], timeframe='today 5-y', geo=geo)
            df_trends = pytrends.interest_over_time()
            return df_trends
        except (ConnectionError, Timeout) as e:
            if attempt < retries - 1:
                time.sleep(5 ** (attempt + 1))  # Exponential backoff
            else:
                print(f"Failed to retrieve data for {kw} after {retries} attempts.")
                return None

# Function to categorize keyword trends
def categorize_keyword_trend(kw):
    df_trends = retry_request(pytrends, kw)

    if df_trends is None or df_trends.empty:
        print(f'No data available for keyword: {kw}')
        return None, None

    mean = round(df_trends[kw].mean(), 2)
    avg_last_year = round(df_trends[kw][-52:].mean(), 2)
    avg_first_year = round(df_trends[kw][:52].mean(), 2)
    trend = round(((avg_last_year / mean) - 1) * 100, 2)
    trend2 = round(((avg_last_year / avg_first_year) - 1) * 100, 2)

    stability = categorize_stability(mean, trend)

    messages = [
        f'The average 5 years interest of "{kw}" was {mean}',
        f'The last year interest of "{kw}" compared to the last 5 years has changed by {trend}%',
        f'The interest for "{kw}" is {stability}',
        get_comparison_message(avg_first_year, trend2, kw)
    ]

    for message in messages:
        print(message)

    classified_data = {
        'Keyword': kw,
        'Mean': mean,
        'Trend': trend,
        'Trend2': trend2,
        'Stability': stability
    }

    return df_trends, classified_data

def categorize_stability(mean, trend):
    if mean > 75 and abs(trend) <= 5:
        return 'stable in the last 5 years.'
    elif mean > 75 and trend > 10:
        return 'stable and increasing in the last 5 years.'
    elif mean > 75 and trend < -10:
        return 'stable and decreasing in the last 5 years.'
    elif mean > 60 and abs(trend) <= 15:
        return 'relatively stable in the last 5 years.'
    elif mean > 60 and trend > 15:
        return 'relatively stable and increasing in the last 5 years.'
    elif mean > 60 and trend < -15:
        return 'relatively stable and decreasing in the last 5 years.'
    elif mean > 20 and abs(trend) <= 15:
        return 'seasonal.'
    elif mean > 20 and trend > 15:
        return 'trending.'
    elif mean > 20 and trend < -15:
        return 'significantly decreasing.'
    elif mean > 5 and abs(trend) <= 15:
        return 'cyclical.'
    elif mean > 0 and trend > 15:
        return 'new and trending.'
    elif mean > 0 and trend < -15:
        return 'decreasing and not comparable to its peak.'
    else:
        return 'something to be checked.'

def get_comparison_message(avg_first_year, trend2, kw):
    if avg_first_year == 0:
        return f'"{kw}" did not exist 5 years ago.'
    elif trend2 > 15:
        return f'The last year interest is quite higher compared to 5 years ago. It has increased by {trend2}%'
    elif trend2 < -15:
        return f'The last year interest is quite lower compared to 5 years ago. It has decreased by {trend2}%'
    else:
        return f'The last year interest is comparable to 5 years ago. It has changed by {trend2}%'

# Consolidated data storage
raw_trends_data = pd.DataFrame()
classified_trends_data = []
interest_by_region_data = pd.DataFrame()

if keywords:
    for kw in keywords:
        raw_data, classified_data = categorize_keyword_trend(kw)
        if raw_data is not None:
            raw_trends_data = pd.concat([raw_trends_data, raw_data[kw]], axis=1)
            classified_trends_data.append(classified_data)

            # Get and store interest by region data
            pytrends.build_payload([kw], timeframe='today 5-y', geo=geo)
            df_region = pytrends.interest_by_region().reset_index()
            df_region = df_region[['geoName', kw]]
            df_region.columns = ['geoName', kw]
            if interest_by_region_data.empty:
                interest_by_region_data = df_region
            else:
                interest_by_region_data = interest_by_region_data.merge(df_region, on='geoName', how='outer')

    df_classified_trends = pd.DataFrame(classified_trends_data)

    # Display raw trends data
    if not raw_trends_data.empty:
        print("Raw Trends Data")
        print(raw_trends_data)

    # Display classified trends data
    if not df_classified_trends.empty:
        print("Classified Trends Data")
        print(df_classified_trends)

    # Display consolidated interest by region data
    if not interest_by_region_data.empty:
        print("Consolidated Interest by Region Data")
        print(interest_by_region_data)

        # Visualization
        plt.figure(figsize=(10, 8))
        sns.heatmap(interest_by_region_data.set_index('geoName'), annot=True, fmt=".1f", cmap='coolwarm')
        plt.title('Interest by Region')
        plt.show()
else:
    print("Please enter keywords to analyze.")

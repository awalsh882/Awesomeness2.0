import requests
from bs4 import BeautifulSoup

# Specify the LinkedIn URL here
url = 'https://www.linkedin.com/analytics/creator/audience'

# Send a GET request to the URL
response = requests.get(url)

# If using authentication, you'd need cookies or headers here, LinkedIn usually requires this.

# Parse the response HTML content
soup = BeautifulSoup(response.text, 'html.parser')

# Find the specific <a> element by its class
link_element = soup.find('a', class_='app-aware-link pcd-analytics-view-item__container')

if link_element:
    # Extract the link (href attribute)
    link = link_element.get('href')

    # Extract the follower count from the <p> tag
    followers = link_element.find('p', class_='text-body-large-bold t-black').get_text(strip=True)

    # Extract the percent increase and the timeframe
    percent_change = link_element.find('strong', class_='analytics-tools-shared-trend-text__percent-change-value--increase').get_text(strip=True)
    timeframe = link_element.find('span').get_text(strip=True)

    # Print the extracted data
    print(f'Link: {link}')
    print(f'Followers: {followers}')
    print(f'Percent Change: {percent_change}')
    print(f'Timeframe: {timeframe}')
else:
    print("Element not found.")

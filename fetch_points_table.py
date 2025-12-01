import requests
import json
from datetime import datetime
import os

def fetch_ipl_points_table():
    api_url = 'https://cf-gotham.sportskeeda.com/cricket/ipl/points-table'
    
    # Try different CORS proxies
    cors_proxies = [
        f'https://corsproxy.io/?{api_url}',
        f'https://api.allorigins.win/raw?url={api_url}',
        f'https://cors-anywhere.herokuapp.com/{api_url}',
        api_url  # Try direct access as fallback
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.sportskeeda.com/',
        'Origin': 'https://www.sportskeeda.com'
    }
    
    for proxy_url in cors_proxies:
        try:
            print(f"Trying to fetch data from: {proxy_url}")
            response = requests.get(proxy_url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process the data
            points = []
            if 'table' in data and data['table'] and 'table' in data['table'][0]:
                for team in data['table'][0]['table']:
                    if 'group' in team:
                        points.extend(team['group'])
                    else:
                        points.append(team)
            
            if points:  # If we successfully got the data
                # Create Backend/Static/public directory if it doesn't exist
                os.makedirs('Backend/Static/public', exist_ok=True)
                
                # Save to a JSON file in Backend/Static/public directory
                filename = 'Backend/Static/public/points_table.json'
                
                with open(filename, 'w') as f:
                    json.dump({'points': points}, f, indent=4)
                    
                print(f"Successfully fetched points table data. Saved to {filename}")
                print(f"\nTotal teams: {len(points)}")
                
                # Print the points table in a readable format
                print("\nIPL Points Table:")
                print("-" * 80)
                print(f"{'Pos':<5}{'Team':<20}{'P':<5}{'W':<5}{'L':<5}{'T':<5}{'NR':<5}{'Pts':<5}{'NRR':<10}")
                print("-" * 80)
                
                for team in points:
                    print(f"{team.get('position', '-'):<5}"
                          f"{team.get('team_name', '-'):<20}"
                          f"{team.get('played', '-'):<5}"
                          f"{team.get('won', '-'):<5}"
                          f"{team.get('lost', '-'):<5}"
                          f"{team.get('tied', '-'):<5}"
                          f"{team.get('no_result', '-'):<5}"
                          f"{team.get('points', '-'):<5}"
                          f"{team.get('nrr', '-'):<10}")
                
                return points
                
        except requests.exceptions.RequestException as e:
            print(f"Error with proxy {proxy_url}: {e}")
            continue
        except Exception as e:
            print(f"Error processing data from {proxy_url}: {e}")
            continue
    
    print("All proxy attempts failed. Could not fetch points table data.")
    return None

if __name__ == "__main__":
    fetch_ipl_points_table() 
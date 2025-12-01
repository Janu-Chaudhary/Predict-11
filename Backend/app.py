from flask import Flask, jsonify, request, send_from_directory, send_file
import requests
from flask_cors import CORS
import pandas as pd
import numpy as np
import json
import os
import time

app = Flask(__name__, static_folder='Static')
CORS(app, resources={r"/*": {"origins": "*"}})

# Route to serve static files from the public folder
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('Static/public', filename)

# Serve any JSON or CSV file from the root directory
@app.route('/api/fantasy_team')
def fansty_team():
    from team import main  # Import the main function from team.py
    result = main()        # Call the main function
    return jsonify(result) # Return the result as JSON

@app.route('/<path:filename>')
def serve_static_file(filename):
    return send_from_directory(os.getcwd(), filename)

@app.route('/api/test')
def serve():
    return jsonify({'message': 'Hello, world!'})

@app.route('/api/ipl_matches')
def serve_match():
    with open('Static/public/ipl_matches_2025.json') as f:
        data = json.load(f)
    return jsonify(data)

API_URL = 'https://livescoreapi.thehindu.com/api/cricket/grouped/fixtures/3634'

@app.route('/api/live-matches')
def live_matches():
    try:
        # First try to fetch from external API
        try:
            resp = requests.get(API_URL, timeout=5)  # Add timeout
            if resp.status_code == 200:
                return jsonify(resp.json())
            else:
                raise Exception(f"API returned status code {resp.status_code}")
        except Exception as e:
            print(f"External API error: {str(e)}")

        # Fallback to local JSON file if external API fails
        with open('Static/public/ipl_matches_2025.json', 'r') as f:
            data = json.load(f)
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e), 'message': 'Unable to load match data'}), 500

points_table_cache = None
last_completed_match_id = None

# Helper function to get the latest completed match ID
def get_latest_completed_match_id():
    url = "https://livescoreapi.thehindu.com/api/cricket/grouped/fixtures/3634"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        results = data.get("results", [])
        if results:
            # Assuming the first result is the latest
            return results[0]["game_id"]
    except Exception as e:
        print(f"Error fetching latest completed match id: {e}")
    return None

# Helper function to fetch points table from Sportskeeda
def fetch_points_table_from_sportskeeda():
    api_url = 'https://cf-gotham.sportskeeda.com/cricket/ipl/points-table'
    cors_proxies = [
        f'https://corsproxy.io/?{api_url}',
        f'https://api.allorigins.win/raw?url={api_url}',
        f'https://cors-anywhere.herokuapp.com/{api_url}',
        api_url
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.sportskeeda.com/',
        'Origin': 'https://www.sportskeeda.com'
    }
    for proxy_url in cors_proxies:
        try:
            response = requests.get(proxy_url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            points = []
            if 'table' in data and data['table'] and 'table' in data['table'][0]:
                for team in data['table'][0]['table']:
                    if 'group' in team:
                        points.extend(team['group'])
                    else:
                        points.append(team)
            if points:
                return {'points': points}
        except Exception as e:
            print(f"Error fetching points table from {proxy_url}: {e}")
            continue
    return None

@app.route('/points_table')
def points_table():
    global points_table_cache, last_completed_match_id
    latest_match_id = get_latest_completed_match_id()
    if latest_match_id != last_completed_match_id:
        # A new match has finished, refresh the cache
        new_cache = fetch_points_table_from_sportskeeda()
        if new_cache:
            points_table_cache = new_cache
            last_completed_match_id = latest_match_id
    if points_table_cache:
        return jsonify(points_table_cache)
    else:
        return jsonify({'error': 'Points table not available'}), 500

# Create a directory to store JSON results if it doesn't exist
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)
# Add this dictionary at the top (or near your imports)
PLAYER_NAME_MAP = {'Sanju Samson': 'SV Samson', 'Shubham Dubey': 'SB Dubey', 'Vaibhav Suryavanshi': 'V Suryavanshi', 'Kunal Rathore': 'KS Rathore', 'Shimron Hetmyer': 'SO Hetmyer', 'Yashasvi Jaiswal': 'YBK Jaiswal', 'Dhruv Jurel': 'Dhruv Jurel', 'Riyan Parag': 'R Parag', 'Nitish Rana': 'N Rana', 'Yudhvir Singh Charak': 'Yudhvir Singh', 'Jofra Archer': 'JC Archer', 'Maheesh Theekshana': 'M Theekshana', 'Wanindu Hasaranga': 'PWH de Silva', 'Akash Madhwal': 'A Madhwal', 'Kumar Kartikeya Singh': 'K Kartikeya', 'Tushar Deshpande': 'TU Deshpande', 'Fazalhaq Farooqi': 'Fazalhaq Farooqi', 'Kwena Maphaka': 'K Maphaka', 'Ashok Sharma': 'A Sharma', 'Sandeep Sharma': 'Sandeep Sharma', 'Ishan Kishan': 'Ishan Kishan', 'Atharva Taide': 'Atharva Taide', 'Abhinav Manohar': 'A Manohar', 'Aniket Verma': 'Aniket Verma', 'Heinrich Klaasen': 'H Klaasen', 'Travis Head': 'TM Head', 'Harshal Patel': 'HV Patel', 'Kamindu Mendis': 'PHKD Mendis', 'Wiaan Mulder': 'PWA Mulder', 'Abhishek Sharma': 'Abhishek Sharma', 'Nitish Kumar Reddy': 'Nithish Kumar Reddy', 'Pat Cummins': 'Pat Cummins', 'Mohammad Shami': 'Mohammad Shami', 'Rahul Chahar': 'RD Chahar', 'Simarjeet Singh': 'Simarjeet Singh', 'Zeeshan Ansari': 'Zeeshan Ansari', 'Jaydev Unadkat': 'JD Unadkat', 'Eshan Malinga': 'E Malinga', 'Ajinkya Rahane': 'AM Rahane', 'Rinku Singh': 'RK Singh', 'Quinton de Kock': 'Q de Kock', 'Rahmanullah Gurbaz': 'Rahmanullah Gurbaz', 'Angkrish Raghuvanshi': 'A Raghuvanshi', 'Rovman Powell': 'R Powell', 'Manish Pandey': 'MK Pandey', 'Venkatesh Iyer': 'VR Iyer', 'Anukul Roy': 'AS Roy', 'Moeen Ali': 'MM Ali', 'Ramandeep Singh': 'Ramandeep Singh', 'Andre Russell': 'AD Russell', 'Anrich Nortje': 'A Nortje', 'Vaibhav Arora': 'VG Arora', 'Mayank Markande': 'M Markande', 'Spencer Johnson': 'SH Johnson', 'Harshit Rana': 'Harshit Rana', 'Sunil Narine': 'SP Narine', 'Varun Chakaravarthy': 'CV Varun', 'Chetan Sakariya': 'C Sakariya', 'MS Dhoni': 'MS Dhoni', 'Dewald Brevis': 'D Brevis', 'Devon Conway': 'DP Conway', 'Rahul Tripathi': 'R Tripathi', 'Shaik Rasheed': 'SK Rasheed', 'Ayush Mhatre': 'A Mhatre ', 'Rachin Ravindra': 'R Ravindra', 'Ravichandran Ashwin': 'R Ashwin', 'Vijay Shankar': 'V Shankar', 'Sam Curran': 'SM Curran', 'Anshul Kamboj': 'A Kamboj', 'Deepak Hooda': 'DJ Hooda', 'Jamie Overton': 'J Overton', 'Ravindra Jadeja': 'RA Jadeja', 'Shivam Dube': 'S Dube', 'Khaleel Ahmed': 'KK Ahmed', 'Noor Ahmad': 'Noor Ahmad', 'Mukesh Choudhary': 'Mukesh Choudhary', 'Nathan Ellis': 'NT Ellis', 'Shreyas Gopal': 'S Gopal', 'Matheesha Pathirana': 'M Pathirana', 'Shubman Gill': 'Shubman Gill', 'Jos Buttler': 'JC Buttler', 'Kumar Kushagra': 'Kumar Kushagra', 'Anuj Rawat': 'Anuj Rawat', 'Sherfane Rutherford': 'SE Rutherford', 'Mahipal Lomror': 'MK Lomror', 'Washington Sundar': 'Washington Sunder', 'Mohd. Arshad Khan': 'Arshad Khan', 'Sai Kishore': 'R Sai Kishore', 'Jayant Yadav': 'J Yadav', 'Sai Sudharsan': 'B Sai Sudharsan', 'Dasun shanaka': 'MD Shanaka', 'Shahrukh Khan': 'M Shahrukh Khan', 'Kagiso Rabada': 'K Rabada', 'Mohammed Siraj': 'Mohammed Siraj', 'Prasidh Krishna': 'M Prasidh Krishna', 'Gerald Coetzee': 'G Coetzee', 'Ishant Sharma': 'I Sharma', 'Kulwant Khejroliya': 'K Khejroliya', 'Rahul Tewatia': 'R Tewatia', 'Rashid Khan': 'Rashid Khan', 'Rajat Patidar': ' RM Patidar', 'Virat Kohli': 'V Kohli', 'Phil Salt': 'PD Salt', 'Jitesh Sharma': 'JM Sharma', 'Devdutt Padikkal': 'D Padikkal', 'Swastik Chhikara': 'SS Chhikara', 'Liam Livingstone': 'LS Livingstone', 'Krunal Pandya': 'KH Pandya', 'Swapnil Singh': 'S Singh', 'Tim David': 'TH David', 'Romario Shepherd': 'R Shepherd', 'Manoj Bhandage': 'MS Bhandage', 'Jacob Bethell': 'JG Bethell', 'Josh Hazlewood': 'JR Hazlewood', 'Rasikh Dar': 'Rasikh Salam', 'Suyash Sharma': 'Suyash Sharma', 'Bhuvneshwar Kumar': 'B Kumar', 'Nuwan Thushara': 'N Thushara', 'Lungisani Ngidi': 'L Ngidi', 'Abhinandan Singh': 'A Singh', 'Mohit Rathee': 'M Rathee', 'Yash Dayal': 'Y Dayal', 'Rishabh Pant': 'RR Pant', 'David Miller': 'DA Miller', 'Aiden Markram': 'AK Markram', 'Nicholas Pooran': 'N Pooran', 'Mitchell Marsh': 'MR Marsh', 'Abdul Samad': 'Abdul Samad ', 'Shahbaz Ahamad': 'Shahbaz Ahmed', 'Rajvardhan Hangargekar': 'RS Hangargekar', 'Ayush Badoni': 'A Badoni', 'Shardul Thakur': 'SN Thakur', 'Avesh Khan': 'Avesh Khan', 'Akash Deep': 'Akash Deep', 'M. Siddharth': 'M Siddharth', 'Digvesh Singh': 'DS Rathi', 'Akash Singh': 'Akash Singh', 'Prince Yadav': 'Prince Yadav', 'Mayank Yadav': 'MP Yadav', 'Ravi Bishnoi': 'Ravi Bishnoi', 'Shreyas Iyer': 'SS Iyer', 'Nehal Wadhera': 'N Wadhera', 'Vishnu Vinod': 'Vishnu Vinod', 'Josh Inglis': 'JP Inglis', 'Prabhsimran Singh': 'P Simran Singh', 'Shashank Singh': 'Shashank Singh', 'Marcus Stoinis': 'MP Stoinis', 'Glenn Maxwell': 'GJ Maxwell', 'Harpreet Brar': 'Harpreet Brar', 'Marco Jansen': 'M Jansen', 'Azmatullah Omarzai': 'Azmatullah Omarzai', 'Priyansh Arya': 'Priyansh Arya', 'Suryansh Shedge': 'Suryansh Shedge', 'Arshdeep Singh': 'Arshdeep Singh', 'Yuzvendra Chahal': 'YS Chahal', 'Vyshak Vijaykumar': 'Vijaykumar Vyshak', 'Yash Thakur': 'Yash Thakur', 'Lockie Ferguson': 'LH Ferguson', 'Kuldeep Sen': 'KR Sen', 'Xavier Bartlett': 'XC Bartlett', 'Pravin Dubey': 'P Dubey', 'KL Rahul': 'KL Rahul', 'Jake Fraser-McGurk': 'J Fraser-McGurk', 'Karun Nair': 'KK Nair', 'Faf du Plessis': 'F du Plessis', 'Donovan Ferreira': 'D Ferreira', 'Abishek Porel': 'Abhishek Porel', 'Tristan Stubbs': 'T Stubbs', 'Axar Patel': 'AR Patel', 'Sameer Rizvi': 'Sameer Rizvi', 'Ashutosh Sharma': 'Ashutosh Sharma', 'Vipraj Nigam': 'V Nigam', 'Mitchell Starc': 'MA Starc', 'T. Natarajan': 'T Natarajan', 'Mohit Sharma': 'MM Sharma', 'Mukesh Kumar': 'Mukesh Kumar', 'Dushmantha Chameera': 'PVD Chameera', 'Kuldeep Yadav': 'Kuldeep Yadav', 'Rohit Sharma': 'RG Sharma', 'Surya Kumar Yadav': 'SA Yadav', 'Robin Minz': 'R Minz', 'Ryan Rickelton': 'RD Rickelton', 'Shrijith Krishnan': 'K Shrijith', 'Bevon Jacobs': 'B Jacobs', 'N. Tilak Varma': 'Tilak Varma', 'Hardik Pandya': 'HH Pandya', 'Naman Dhir': 'Naman Dhir', 'Will Jacks': 'WG Jacks', 'Mitchell Santner': 'MJ Santner', 'Raj Angad Bawa': 'RA Bawa', 'Vignesh Puthur': 'V Puthur', 'Trent Boult': 'TA Boult', 'Karn Sharma': 'KV Sharma', 'Deepak Chahar': 'DL Chahar', 'Ashwani Kumar': 'Ashwani Kumar', 'Reece Topley': 'R Topley', 'V.Satyanarayana Penmetsa': 'PVSN Raju', 'Arjun Tendulkar': 'A Tendulkar', 'Mujeeb-ur-Rahman': 'Mujeeb ur Rahman', 'Jasprit Bumrah': 'JJ Bumrah'}

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    batter_name = data.get('batter')
    bowler_name = data.get('bowler')

    if not batter_name or not bowler_name:
        return jsonify({'error': 'Both batsman and bowler names are required'}), 400

    try:
        result = analyze_batter_vs_bowler("deliveries.csv", batter_name, bowler_name)
        if result is None:
            return jsonify({'error': f'No head-to-head data found between {batter_name} and {bowler_name}.'}), 404

        # Save the result to a JSON file
        filename = f"{batter_name.replace(' ', '')}_vs_{bowler_name.replace(' ', '')}.json"
        filepath = os.path.join(RESULTS_DIR, filename)

        with open(filepath, 'w') as f:
            json.dump(result, f)

        # Return the filename so the frontend knows which file to request
        return jsonify({'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results/<filename>', methods=['GET'])
def get_result(filename):
    filepath = os.path.join(RESULTS_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='application/json')
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/head_to_head', methods=['GET', 'POST'])
def head_to_head():
    h2h = None
    if request.method == 'POST':
        player1 = request.form.get('player1')
        player2 = request.form.get('player2')
        # TODO: Fetch head-to-head data for player1 and player2 and assign to h2h
        # For now, just return the player names to show they're being used
        h2h = {'player1': player1, 'player2': player2, 'message': 'Head-to-head data will be implemented later'}
    return jsonify({'h2h': h2h})

def analyze_batter_vs_bowler(file, batter_name, bowler_name):
    df = pd.read_csv(file)
    # Filter only the relevant head-to-head deliveries
    head_to_head = df[(df['batter'] == batter_name) & (df['bowler'] == bowler_name)].copy()

    # Exclude extras that don't count as legal deliveries faced
    head_to_head = head_to_head[~head_to_head['extras_type'].isin(['wides', 'legbyes', 'byes']) | head_to_head['extras_type'].isna()]

    if head_to_head.empty:
        return None

    total_balls = len(head_to_head)
    dot_balls = len(head_to_head[head_to_head['batsman_runs'] == 0])
    runs = head_to_head['batsman_runs'].sum()
    run_breakdown = head_to_head['batsman_runs'].value_counts().to_dict()
    dismissals = head_to_head['player_dismissed'].eq(batter_name).sum()

    strike_rate = (runs / total_balls) * 100 if total_balls else 0
    average = (runs / dismissals) if dismissals else runs
    boundary_pct = (run_breakdown.get(4, 0) + run_breakdown.get(6, 0)) / total_balls * 100 if total_balls else 0

    summary = {
        'Batter': batter_name,
        'Bowler': bowler_name,
        'Balls Faced': total_balls,
        'Dot Balls': dot_balls,
        'Total Runs': runs,
        '1s': run_breakdown.get(1, 0),
        '2s': run_breakdown.get(2, 0),
        '3s': run_breakdown.get(3, 0),
        '4s': run_breakdown.get(4, 0),
        '6s': run_breakdown.get(6, 0),
        'Dismissals': dismissals,
        'Strike Rate': round(strike_rate, 2),
        'Average': round(average, 2),
        'Boundary %': round(boundary_pct, 2)
    }
    # Convert all values to native Python types
    summary = {k: (int(v) if isinstance(v, (np.integer, int)) else float(v) if isinstance(v, (np.floating, float)) else v) for k, v in summary.items()}
    return summary


if __name__ == '__main__':
    app.run(debug=True)
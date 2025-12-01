import json
import pandas as pd
import numpy as np
import os
from collections import defaultdict
import argparse
from io import StringIO

class Dream11Predictor:
    def __init__(self, batter_data_path, bowler_data_path, teams_folder_path):
        # Load data from JSON files
        with open(batter_data_path, 'r') as f:
            self.batter_data = json.load(f)
        
        with open(bowler_data_path, 'r') as f:
            self.bowler_data = json.load(f)
        
        # Load team data from CSV files
        self.teams_data = {}
        self.load_teams_data(teams_folder_path)
        
        self.player_scores = {}
        self.selected_team = []
        self.player_roles = {}
        self.player_credits = {}
        self.player_is_foreign = {}
        # Add team constraint tracking
        self.player_teams = {}  # Maps player name to their IPL team
        self.team_counts = defaultdict(int)
        self.role_team_counts = defaultdict(lambda: defaultdict(int))
    
    def load_teams_data(self, teams_folder_path):
        """Load all team data from CSV files in the Teams folder"""
        for filename in os.listdir(teams_folder_path):
            if filename.endswith('_squad.csv'):
                team_name = filename.replace('_squad.csv', '').replace('-', ' ').title()
                file_path = os.path.join(teams_folder_path, filename)
                try:
                    team_df = pd.read_csv(file_path)
                    self.teams_data[team_name] = team_df
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
    
    def get_player_info_from_csv(self, player_name):
        """Updated with exact column names"""
        for team_name, team_df in self.teams_data.items():
            player_row = team_df[team_df['Name'].str.strip().str.lower() == player_name.strip().lower()]
            if not player_row.empty:
                player_info = player_row.iloc[0]
                # Track player-team mapping
                self.player_teams[player_name] = team_name
                return {
                    'role': player_info['Role'],
                    'credits': float(player_info['Credits']),  # Use 'Credits' with capital C
                    'foreign': player_info['Foreign Player'] == True,
                    'team': team_name
                }
        return None
    
    def set_player_roles(self, players_with_roles):
        """Set player roles from the provided list and update with CSV data"""
        for player_info in players_with_roles:
            parts = player_info.strip().split('(', 1)
            if len(parts) >= 2:
                player_name = parts[0].strip()
                role_part = parts[1].strip()
                if role_part.endswith(')'):
                    role = role_part[:-1].strip()
                    self.player_roles[player_name] = role
            else:
                # If no role is specified, default to "Unknown"
                player_name = player_info.strip()
                self.player_roles[player_name] = "Unknown"
            
            # Try to get additional info from CSV
            csv_info = self.get_player_info_from_csv(player_name)
            if csv_info:
                # Update role if it was unknown
                if self.player_roles[player_name] == "Unknown":
                    self.player_roles[player_name] = csv_info['role']
                
                # Set credits and foreign status
                self.player_credits[player_name] = csv_info['credits']
                self.player_is_foreign[player_name] = csv_info['foreign']
            else:
                # Default values if not found in CSV
                self.player_credits[player_name] = 7.0  # Default credit value
                self.player_is_foreign[player_name] = False  # Default to Indian player
    
    def analyze_head_to_head(self, team1_players, team2_players):
        """Analyze head-to-head performance between players of two teams"""
        for batter in team1_players:
            if batter not in self.player_scores:
                self.player_scores[batter] = 0
                
            if batter in self.batter_data:
                # Analyze batter's performance against team2 bowlers
                for bowler in team2_players:
                    if bowler in self.batter_data[batter].get('head_to_head', {}):
                        h2h_data = self.batter_data[batter]['head_to_head'][bowler]
                        
                        # If there's a list of encounters, take the first one
                        if isinstance(h2h_data, list) and len(h2h_data) > 0:
                            h2h_data = h2h_data[0]
                        
                        # Skip if no data or message indicates no data
                        if isinstance(h2h_data, dict) and 'Message' not in h2h_data:
                            # Calculate batting score based on strike rate, average, and boundary %
                            try:
                                strike_rate = h2h_data.get('Strike Rate', 0)
                                avg = h2h_data.get('Average', 0)
                                boundary_pct = h2h_data.get('Boundary %', 0)
                                dismissals = h2h_data.get('Dismissals', 0)
                                
                                # Higher score for better performance against this bowler
                                batting_score = (strike_rate / 100) * 2 + (avg / 10) + (boundary_pct / 10) - (dismissals * 2)
                                self.player_scores[batter] += batting_score
                            except (TypeError, ValueError):
                                pass
        
        for bowler in team2_players:
            if bowler not in self.player_scores:
                self.player_scores[bowler] = 0
                
            if bowler in self.bowler_data:
                # Analyze bowler's performance against team1 batters
                for batter in team1_players:
                    if batter in self.bowler_data[bowler].get('head_to_head', {}):
                        h2h_data = self.bowler_data[bowler]['head_to_head'][batter]
                        
                        # Skip if no data
                        if isinstance(h2h_data, dict):
                            # Calculate bowling score based on economy and wickets
                            try:
                                dismissals = float(h2h_data.get('Dismissals', 0))
                                economy = float(h2h_data.get('Econ', 15))  # Default high economy if not available
                                
                                # Higher score for more wickets and lower economy
                                bowling_score = (dismissals * 5) + (10 - min(economy, 10))
                                self.player_scores[bowler] += bowling_score
                            except (TypeError, ValueError):
                                pass
    
    def analyze_venue_performance(self, venue, players):
        """Enhanced venue parsing with precise columns"""
        for player in players:
            # Batting venue analysis
            if player in self.batter_data:
                venue_data = self.batter_data[player].get('venue', {})
                if venue_data and 'Batting' in venue_data:
                    try:
                        venue_df = pd.read_csv(StringIO(venue_data['Batting']), sep=r'\s{2,}', engine='python')
                        venue_row = venue_df[venue_df['venue'].str.contains(venue, case=False)]
                        if not venue_row.empty:
                            avg = venue_row['Average'].values[0]
                            strike_rate = venue_row['Strike Rate'].values[0]
                            self.player_scores[player] += (avg/20) + (strike_rate/100)
                    except Exception as e:
                        print(f"Venue data error for {player}: {str(e)}")
            # Bowling venue analysis
            if player in self.bowler_data:
                venue_data = self.bowler_data[player].get('venue', {})
                if venue_data and 'Bowling' in venue_data:
                    try:
                        venue_df = pd.read_csv(StringIO(venue_data['Bowling']), sep=r'\s{2,}', engine='python')
                        venue_row = venue_df[venue_df['venue'].str.contains(venue, case=False)]
                        if not venue_row.empty:
                            wickets = venue_row['Wickets'].values[0]
                            economy = venue_row['Economy'].values[0]
                            self.player_scores[player] += (wickets*3) + (10 - min(economy, 10))
                    except Exception as e:
                        print(f"Venue data error for {player}: {str(e)}")
    
    def analyze_recent_form(self, players):
        """Analyze players' recent form based on last 5 matches"""
        for player in players:
            if player not in self.player_scores:
                self.player_scores[player] = 0
            
            # Check batter recent form
            if player in self.batter_data and 'recent_form' in self.batter_data[player]:
                recent_form = self.batter_data[player]['recent_form']
                
                for form_data in recent_form:
                    if len(form_data) >= 2 and form_data[0] == 'Batting Match-wise':
                        try:
                            form_df = pd.read_csv(pd.StringIO(form_data[1]), sep=r'\s{2,}', engine='python')
                            
                            # Calculate average runs and strike rate from last 5 matches
                            if 'Runs' in form_df.columns:
                                avg_runs = form_df['Runs'].mean()
                                self.player_scores[player] += avg_runs / 10
                            
                            if 'Strike Rate' in form_df.columns:
                                avg_sr = form_df['Strike Rate'].mean()
                                self.player_scores[player] += avg_sr / 100
                        except Exception:
                            pass
            
            # Check bowler recent form
            if player in self.bowler_data and 'recent_form' in self.bowler_data[player]:
                recent_form = self.bowler_data[player]['recent_form']
                
                for form_data in recent_form:
                    if len(form_data) >= 2 and form_data[0] == 'Bowling Match-wise':
                        try:
                            form_df = pd.read_csv(pd.StringIO(form_data[1]), sep=r'\s{2,}', engine='python')
                            
                            # Calculate average wickets and economy from last 5 matches
                            if 'Wickets' in form_df.columns:
                                avg_wickets = form_df['Wickets'].mean()
                                self.player_scores[player] += avg_wickets * 5
                            
                            if 'Economy' in form_df.columns:
                                avg_economy = form_df['Economy'].mean()
                                self.player_scores[player] += (10 - min(avg_economy, 10))
                        except Exception:
                            pass
    
    def categorize_players(self, sorted_players):
        """Categorize players based on their roles"""
        batsmen = []
        bowlers = []
        all_rounders = []
        wicket_keepers = []
        
        for player, score in sorted_players:
            role = self.player_roles.get(player, "Unknown")
            
            if "WK" in role:
                wicket_keepers.append((player, score))
            elif "Bowler" in role:
                bowlers.append((player, score))
            elif "All-Rounder" in role or "Allrounder" in role or "All-rounder" in role or "All Rounder" in role:
                all_rounders.append((player, score))
            elif "Batter" in role or "Batsman" in role:
                batsmen.append((player, score))
            else:
                # Fallback to the original logic if role is unknown
                if player in self.batter_data and player not in self.bowler_data:
                    # Pure batsman
                    if player in ['MS Dhoni', 'Rishabh Pant', 'KL Rahul', 'Sanju Samson', 'Ishan Kishan', 'Nicholas Pooran', 'Josh Inglis', 'Prabhsimran Singh']:
                        wicket_keepers.append((player, score))
                    else:
                        batsmen.append((player, score))
                elif player in self.bowler_data and player not in self.batter_data:
                    # Pure bowler
                    bowlers.append((player, score))
                else:
                    # All-rounder (has both batting and bowling data)
                    all_rounders.append((player, score))
        
        return {
            'batsmen': batsmen,
            'bowlers': bowlers,
            'all_rounders': all_rounders,
            'wicket_keepers': wicket_keepers
        }
    
    def ensure_minimum_requirements(self, categorized_players, total_credits, foreign_count):
        """Ensure minimum requirements for each category (1 player from each)"""
        selected_players = []
        
        # New constraints
        min_per_category = 1
        max_per_category = 5
        max_credits = 100
        max_foreign = 4
        
        # Select at least one player from each category
        for category_name in ['wicket_keepers', 'batsmen', 'all_rounders', 'bowlers']:
            category = categorized_players[category_name if category_name != 'wicket_keepers' else 'wicket_keepers']
            
            for player, score in category:
                if len([p for p in selected_players if p[0] == player]) > 0:
                    continue  # Skip if player already selected
                    
                credits = self.player_credits.get(player, 7.0)
                is_foreign = self.player_is_foreign.get(player, False)
                
                if total_credits + credits <= max_credits and (not is_foreign or foreign_count < max_foreign):
                    selected_players.append((player, score))
                    total_credits += credits
                    if is_foreign:
                        foreign_count += 1
                    break  # We only need one player from each category for minimum requirements
        
        return selected_players, total_credits, foreign_count
    
    def _simplify_role(self, player):
        role = self.player_roles.get(player, "Unknown")
        if "WK" in role:
            return "WK"
        elif "Bowler" in role:
            return "BOWL"
        elif "All-Rounder" in role or "Allrounder" in role:
            return "ALL"
        elif "Batter" in role or "Batsman" in role:
            return "BAT"
        else:
            return "BAT"

    def select_dream11_team(self):
        """Updated with precise constraints"""
        MAX_TEAM_PLAYERS = 6
        MAX_ROLE_PER_TEAM = {'WK': 2, 'BAT': 3, 'ALL': 3, 'BOWL': 3}
        max_foreign = 4
        max_credits = 100
        sorted_players = sorted(self.player_scores.items(), key=lambda x: x[1], reverse=True)
        selected_players = []
        total_credits = 0
        foreign_count = 0
        self.team_counts = defaultdict(int)
        self.role_team_counts = defaultdict(lambda: defaultdict(int))
        for player, score in sorted_players:
            credits = self.player_credits.get(player, 7.0)
            is_foreign = self.player_is_foreign.get(player, False)
            team = self.player_teams.get(player, "Unknown")
            role_category = self._simplify_role(player)
            # Team constraint check
            if self.team_counts[team] >= MAX_TEAM_PLAYERS:
                continue
            # Role-team constraint check
            if self.role_team_counts[team][role_category] >= MAX_ROLE_PER_TEAM[role_category]:
                continue
            # Credit and foreign constraints
            if total_credits + credits > max_credits:
                continue
            if is_foreign and foreign_count >= max_foreign:
                continue
            # Proceed with selection
            selected_players.append((player, score))
            self.team_counts[team] += 1
            self.role_team_counts[team][role_category] += 1
            total_credits += credits
            if is_foreign:
                foreign_count += 1
            if len(selected_players) == 11:
                break
        self.selected_team = selected_players
        # Captain/vice-captain logic can be upgraded next
        if len(self.selected_team) >= 2:
            captain = self.selected_team[0][0]
            vice_captain = self.selected_team[1][0]
            return self.selected_team, captain, vice_captain, total_credits, foreign_count
        else:
            return self.selected_team, None, None, total_credits, foreign_count
    
    def predict_dream11(self, team1, team2, venue, team1_playing11, team2_playing11):
        """Main function to predict Dream11 team for a match with specific playing XI"""
        # Combine playing 11 from both teams
        playing11 = team1_playing11 + team2_playing11
        
        # Set player roles from the provided playing 11
        self.set_player_roles(playing11)
        
        # Extract player names without roles
        all_players = [p.split('(')[0].strip() for p in playing11]
        
        # Determine which players belong to which team
        team1_players = [p.split('(')[0].strip() for p in team1_playing11]
        team2_players = [p.split('(')[0].strip() for p in team2_playing11]
        
        # Reset player scores
        self.player_scores = {}
        
        # Analyze different aspects
        self.analyze_head_to_head(team1_players, team2_players)
        self.analyze_head_to_head(team2_players, team1_players)  # Analyze in reverse too
        self.analyze_venue_performance(venue, all_players)
        self.analyze_recent_form(all_players)
        
        # Select the best team
        team, captain, vice_captain, total_credits, foreign_count = self.select_dream11_team()
        
        return team, captain, vice_captain, team1, team2, venue, total_credits, foreign_count

    def display_team(self, team, captain, vice_captain, team1, team2, venue, total_credits, foreign_count):
        """Display the selected Dream11 team"""
        print(f"\n===== DREAM 11 TEAM =====\n")
        print(f"Match: {team1} vs {team2}")
        print(f"Venue: {venue}\n")
        print(f"Total Credits: {total_credits:.1f}/100.0")
        print(f"Foreign Players: {foreign_count}/4\n")
        
        # Categorize selected players
        wk = []
        bat = []
        ar = []
        bowl = []
        
        for player, score in team:
            role = self.player_roles.get(player, "Unknown")
            credits = self.player_credits.get(player, 7.0)
            is_foreign = self.player_is_foreign.get(player, False)
            
            if "WK" in role:
                wk.append((player, score, "WK", credits, is_foreign))
            elif "Bowler" in role:
                bowl.append((player, score, "BOWL", credits, is_foreign))
            elif "All-Rounder" in role or "Allrounder" in role or "All-rounder" in role or "All Rounder" in role:
                ar.append((player, score, "ALL", credits, is_foreign))
            elif "Batter" in role or "Batsman" in role:
                bat.append((player, score, "BAT", credits, is_foreign))
            else:
                # Fallback to the original logic if role is unknown
                if player in self.batter_data and player not in self.bowler_data:
                    if player in ['MS Dhoni', 'Rishabh Pant', 'KL Rahul', 'Sanju Samson', 'Ishan Kishan', 'Nicholas Pooran', 'Josh Inglis', 'Prabhsimran Singh']:
                        wk.append((player, score, "WK", credits, is_foreign))
                    else:
                        bat.append((player, score, "BAT", credits, is_foreign))
                elif player in self.bowler_data and player not in self.batter_data:
                    bowl.append((player, score, "BOWL", credits, is_foreign))
                else:
                    ar.append((player, score, "ALL", credits, is_foreign))
        
        # Display by category
        print("WICKET-KEEPERS:")
        for player, score, _, credits, is_foreign in wk:
            captain_mark = " (C)" if player == captain else " (VC)" if player == vice_captain else ""
            foreign_mark = " [FOREIGN]" if is_foreign else ""
            print(f"  {player}{captain_mark} - {score:.2f} points - {credits} credits{foreign_mark}")
        
        print("\nBATSMEN:")
        for player, score, _, credits, is_foreign in bat:
            captain_mark = " (C)" if player == captain else " (VC)" if player == vice_captain else ""
            foreign_mark = " [FOREIGN]" if is_foreign else ""
            print(f"  {player}{captain_mark} - {score:.2f} points - {credits} credits{foreign_mark}")
        
        print("\nALL-ROUNDERS:")
        for player, score, _, credits, is_foreign in ar:
            captain_mark = " (C)" if player == captain else " (VC)" if player == vice_captain else ""
            foreign_mark = " [FOREIGN]" if is_foreign else ""
            print(f"  {player}{captain_mark} - {score:.2f} points - {credits} credits{foreign_mark}")
        
        print("\nBOWLERS:")
        for player, score, _, credits, is_foreign in bowl:
            captain_mark = " (C)" if player == captain else " (VC)" if player == vice_captain else ""
            foreign_mark = " [FOREIGN]" if is_foreign else ""
            print(f"  {player}{captain_mark} - {score:.2f} points - {credits} credits{foreign_mark}")
        
        print("\nCAPTAIN: " + (captain if captain else "None"))
        print("VICE-CAPTAIN: " + (vice_captain if vice_captain else "None"))
        
        # Precise team distribution
        print("\nTeam Constraints Verification:")
        team_dist = defaultdict(int)
        role_dist = defaultdict(lambda: defaultdict(int))
        for player, _ in team:
            team_name = self.player_teams.get(player, "Unknown")
            role = self._simplify_role(player)
            team_dist[team_name] += 1
            role_dist[team_name][role] += 1
        print("\nPlayers per Team:")
        for team, count in team_dist.items():
            print(f"  {team}: {count}/6")
        print("\nRole Distribution per Team:")
        for team, roles in role_dist.items():
            print(f"  {team}:")
            for role, count in roles.items():
                print(f"    {role}: {count}/3")

def main():
    # Define paths to data files
    current_dir = os.path.dirname(os.path.abspath(__file__))
    batter_data = os.path.join(current_dir, 'Static', 'public', 'batter_data_cache.json')
    bowler_data = os.path.join(current_dir, 'Static', 'public', 'bowler_data_cache.json')
    teams_folder = os.path.join(current_dir, 'Teams')
    
    # Create predictor instance
    predictor = Dream11Predictor(batter_data, bowler_data, teams_folder)
    
    # Example usage (you can modify these values)
    team1 = "Mumbai Indians"
    team2 = "Delhi Capitals"
    venue = "Wankhede Stadium, Mumbai"
    
    # Example playing 11 (you can modify these)
    team1_playing11 = [
    "Ryan Rickelton",
    "Rohit Sharma",
    "Will Jacks",
    "Surya Kumar Yadav",
    "N. Tilak Varma",
    "Hardik Pandya",
    "Naman Dhir",
    "Mitchell Santner",
    "Deepak Chahar",
    "Trent Boult",
    "Jasprit Bumrah",
    "Karn Sharma"
    ]
    
    team2_playing11 = [
    "Faf du Plessis",
    "Abishek Porel",
    "Sameer Rizvi",
    "Tristan Stubbs",
    "Ashutosh Sharma",
    "Vipraj Nigam",
    "Madhav Tiwari",
    "Kuldeep Yadav",
    "Dushmantha Chameera",
    "Mukesh Kumar",
    "KL Rahul"
    ]
    
    # Predict Dream11 team
    team, captain, vice_captain, team1, team2, venue, total_credits, foreign_count = predictor.predict_dream11(
        team1, team2, venue, team1_playing11, team2_playing11
    )
    
    # Display the team
    predictor.display_team(team, captain, vice_captain, team1, team2, venue, total_credits, foreign_count)
    
    # Save the team data to a JSON file in Static/public
    output_path = os.path.join(current_dir, 'Static', 'public', 'fantasy_team.json')
    team_data = []
    for player, score in team:
        role = predictor.player_roles.get(player, "Unknown")
        credits = predictor.player_credits.get(player, 7.0)
        is_foreign = predictor.player_is_foreign.get(player, False)
        
        # Determine player's team
        player_team = "Unknown"
        if player in [p.split('(')[0].strip() for p in team1_playing11]:
            player_team = team1
        elif player in [p.split('(')[0].strip() for p in team2_playing11]:
            player_team = team2
            
        # Convert team name to abbreviation
        team_abbr = ""
        if "Sunrisers" in player_team:
            team_abbr = "SRH"
        elif "Delhi" in player_team:
            team_abbr = "DC"
        elif "Chennai" in player_team:
            team_abbr = "CSK"
        elif "Mumbai" in player_team:
            team_abbr = "MI"
        elif "Kolkata" in player_team:
            team_abbr = "KKR"
        elif "Punjab" in player_team:
            team_abbr = "PBKS"
        elif "Rajasthan" in player_team:
            team_abbr = "RR"
        elif "Bangalore" in player_team or "Bengaluru" in player_team:
            team_abbr = "RCB"
        elif "Gujarat" in player_team:
            team_abbr = "GT"
        elif "Lucknow" in player_team:
            team_abbr = "LSG"
        else:
            team_abbr = player_team[:2]
        
        # Simplify role for web display
        display_role = "Batsman"
        if "WK" in role:
            display_role = "Wicketkeeper"
        elif "Bowler" in role:
            display_role = "Bowler"
        elif "All-Rounder" in role or "Allrounder" in role:
            display_role = "All-Rounder"
        
        team_data.append({
            "name": player,
            "team": team_abbr,
            "role": display_role,
            "credit": credits,
        })
    
    # Save to JSON file
    with open(output_path, 'w') as f:
        json.dump({
            "players": team_data,
            "total_credits": total_credits,
            "match": f"{team1} vs {team2}",
            "venue": venue,
            "captain": captain,
            "vice_captain": vice_captain
        }, f, indent=2)
    
    print(f"\nTeam data saved to {output_path}")
    
if __name__ == "__main__":
    main()
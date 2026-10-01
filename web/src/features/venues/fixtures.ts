import type { VenueCard } from "./types";

/** Trimmed snapshot of GET /api/v1/venues/154 (Wankhede) on 2026-10-02, for tests. */
export const WANKHEDE_FIXTURE: VenueCard = {
  "id": 154,
  "name": "Wankhede Stadium",
  "city": "Mumbai",
  "matches": 132,
  "first_match": "2008-04-20",
  "last_match": "2026-05-24",
  "par_weighted": 189.6,
  "recent": {
    "matches": 27,
    "avg_first_innings": 196.7,
    "median_first_innings": 205.0,
    "avg_second_innings": 183.0,
    "chase_win_pct": 55.6,
    "bat_first_win_pct": 44.4
  },
  "all_time": {
    "matches": 130,
    "avg_first_innings": 173.4,
    "median_first_innings": 174.5,
    "avg_second_innings": 162.2,
    "chase_win_pct": 54.6,
    "bat_first_win_pct": 45.4
  },
  "toss_recent": {
    "matches": 28,
    "chose_field": 26,
    "chose_bat": 2,
    "field_pct": 92.9,
    "toss_winner_win_pct": 50.0,
    "toss_winner_win_pct_when_field": 53.8,
    "toss_winner_win_pct_when_bat": 0.0
  },
  "toss_all_time": {
    "matches": 132,
    "chose_field": 101,
    "chose_bat": 31,
    "field_pct": 76.5,
    "toss_winner_win_pct": 52.3,
    "toss_winner_win_pct_when_field": 54.5,
    "toss_winner_win_pct_when_bat": 45.2
  },
  "phases_recent": [
    {
      "phase": "powerplay",
      "run_rate": 9.73,
      "wickets_per_innings": 1.38
    },
    {
      "phase": "middle",
      "run_rate": 9.36,
      "wickets_per_innings": 2.48
    },
    {
      "phase": "death",
      "run_rate": 11.18,
      "wickets_per_innings": 2.11
    }
  ],
  "phases_all_time": [
    {
      "phase": "powerplay",
      "run_rate": 8.04,
      "wickets_per_innings": 1.47
    },
    {
      "phase": "middle",
      "run_rate": 8.25,
      "wickets_per_innings": 2.36
    },
    {
      "phase": "death",
      "run_rate": 10.56,
      "wickets_per_innings": 2.17
    }
  ],
  "by_season": [
    {
      "season": 2021,
      "matches": 10,
      "avg_first_innings": 176.6
    },
    {
      "season": 2022,
      "matches": 21,
      "avg_first_innings": 166.8
    },
    {
      "season": 2023,
      "matches": 7,
      "avg_first_innings": 197.9
    },
    {
      "season": 2024,
      "matches": 7,
      "avg_first_innings": 188.1
    },
    {
      "season": 2025,
      "matches": 7,
      "avg_first_innings": 178.3
    },
    {
      "season": 2026,
      "matches": 7,
      "avg_first_innings": 219.7
    }
  ],
  "highest_totals": [
    {
      "match_id": 1529284,
      "date": "2026-04-29",
      "season": 2026,
      "team": "Sunrisers Hyderabad",
      "opponent": "Mumbai Indians",
      "innings": 2,
      "runs": 249,
      "wickets": 4,
      "overs": "18.4",
      "score": "249/4 (18.4)"
    },
    {
      "match_id": 1529284,
      "date": "2026-04-29",
      "season": 2026,
      "team": "Mumbai Indians",
      "opponent": "Sunrisers Hyderabad",
      "innings": 1,
      "runs": 243,
      "wickets": 5,
      "overs": "20",
      "score": "243/5 (20)"
    },
    {
      "match_id": 1527693,
      "date": "2026-04-12",
      "season": 2026,
      "team": "Royal Challengers Bengaluru",
      "opponent": "Mumbai Indians",
      "innings": 1,
      "runs": 240,
      "wickets": 4,
      "overs": "20",
      "score": "240/4 (20)"
    }
  ],
  "lowest_totals": [
    {
      "match_id": 336021,
      "date": "2008-05-16",
      "season": 2008,
      "team": "Kolkata Knight Riders",
      "opponent": "Mumbai Indians",
      "innings": 1,
      "runs": 67,
      "wickets": 10,
      "overs": "15.2",
      "score": "67 (15.2)"
    },
    {
      "match_id": 548325,
      "date": "2012-04-16",
      "season": 2012,
      "team": "Mumbai Indians",
      "opponent": "Delhi Capitals",
      "innings": 1,
      "runs": 92,
      "wickets": 10,
      "overs": "19.2",
      "score": "92 (19.2)"
    },
    {
      "match_id": 1304105,
      "date": "2022-05-12",
      "season": 2022,
      "team": "Chennai Super Kings",
      "opponent": "Mumbai Indians",
      "innings": 1,
      "runs": 97,
      "wickets": 10,
      "overs": "16",
      "score": "97 (16)"
    }
  ],
  "top_run_scorers": [
    {
      "player": {
        "id": "740742ef",
        "name": "RG Sharma"
      },
      "innings": 90,
      "value": 2632,
      "rate": 140.22
    },
    {
      "player": {
        "id": "271f83cd",
        "name": "SA Yadav"
      },
      "innings": 46,
      "value": 1556,
      "rate": 162.42
    },
    {
      "player": {
        "id": "a757b0d8",
        "name": "KA Pollard"
      },
      "innings": 57,
      "value": 1226,
      "rate": 155.78
    }
  ],
  "top_wicket_takers": [
    {
      "player": {
        "id": "a12e1d51",
        "name": "SL Malinga"
      },
      "innings": 43,
      "value": 68,
      "rate": 7.0
    },
    {
      "player": {
        "id": "462411b3",
        "name": "JJ Bumrah"
      },
      "innings": 54,
      "value": 65,
      "rate": 7.5
    },
    {
      "player": {
        "id": "8b5b6769",
        "name": "Harbhajan Singh"
      },
      "innings": 47,
      "value": 49,
      "rate": 7.09
    }
  ],
  "notes": [
    "Pace vs spin wicket split is not available: bowling style is not stored in the DB yet.",
    "Par / chase figures use completed non-DLS matches with a result. Run rates are runs (incl. extras) per 6 legal balls."
  ]
};

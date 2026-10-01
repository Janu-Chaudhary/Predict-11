#!/usr/bin/env bash
# Probe 00: download Cricsheet zips + registers into samples/, HEAD-check larger zips.
cd "$(dirname "$0")/samples"; UA="predict11-spike/0.1 (personal research)"
for f in recently_added_7_json.zip recently_added_30_json.zip ipl_json.zip; do curl -sS -A "$UA" -o $f https://cricsheet.org/downloads/$f; done
curl -sS -A "$UA" -o people.csv https://cricsheet.org/register/people.csv
curl -sS -A "$UA" -o names.csv https://cricsheet.org/register/names.csv
for f in all_json.zip t20s_json.zip t20s_male_json.zip it20s_json.zip bbl_json.zip psl_json.zip cpl_json.zip sat_json.zip ilt_json.zip mlc_json.zip ntb_json.zip sma_json.zip lpl_json.zip bpl_json.zip; do
  printf "%s " $f; curl -sSI -A "$UA" https://cricsheet.org/downloads/$f | grep -iE "content-length|last-modified" | tr -d '\r' | tr '\n' ' '; echo; done

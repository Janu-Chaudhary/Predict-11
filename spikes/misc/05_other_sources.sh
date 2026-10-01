#!/usr/bin/env bash
# Probe 05: quick check of other free IPL sources (GitHub search, Kaggle public list API, howstat, cricketarchive).
cd "$(dirname "$0")/samples"; UA="predict11-spike/0.1 (personal research)"
curl -sS -A "$UA" "https://api.github.com/search/repositories?q=IPL+2026&sort=updated&per_page=10" > github_ipl2026_search.json
curl -sS -A "$UA" "https://www.kaggle.com/api/v1/datasets/list?search=ipl%202026&sortBy=updated" > kaggle_ipl2026.json
curl -sS -o /dev/null -w "howstat %{http_code}\n" -A "$UA" https://www.howstat.com/cricket/Statistics/IPL/MatchList.asp
curl -sS -o /dev/null -w "cricketarchive %{http_code}\n" -A "$UA" https://cricketarchive.com/

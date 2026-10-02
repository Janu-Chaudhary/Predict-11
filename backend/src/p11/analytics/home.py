"""Home page data (landing hero + next-match card + bento tiles).

Reads only the resolved views (``delivery_resolved``, ``innings_resolved``,
``match_player_resolved``) and the match/team/venue/season tables. Pure rules (phase, hero
choice, best XI, shot parsing) live in ``home_phase`` / ``home_xi`` / ``home_wagon``.

There is no fixtures table yet, so ``next_fixture`` is read from a ``fixture`` table only if one
exists at runtime (columns ``start_time``, ``team1_id``, ``team2_id`` and optionally ``id``,
``venue_id``, ``stage``, ``match_number``, ``xi_confirmed``); otherwise it is null.
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, text

from . import home_wagon, home_xi
from .home_phase import (
    IST,
    choose_hero,
    decide_phase,
    match_title,
    overs_text,
    team_code,
    team_display,
)
from .home_schemas import (
    XI,
    BallKind,
    FantasyTile,
    H2HTile,
    HomeMatch,
    HomeScore,
    HomeState,
    HomeTeam,
    HomeTiles,
    HomeVenue,
    NextFixture,
    PlayerStatLine,
    PlayersTile,
    RecordsTile,
    SeasonCard,
    Shot,
    TableTile,
    VenuesTile,
    Wagon,
    Worm,
    WormBall,
    WormInnings,
    XIPlayer,
)

NOT_A_WICKET = ("retired hurt", "retired not out")
NOT_BOWLER_WICKET = (
    "run out",
    "retired hurt",
    "retired out",
    "retired not out",
    "obstructing the field",
)


class NotFound(LookupError):
    pass


# --------------------------------------------------------------------------- refs
def _team(team_id: int, canonical: str, year: int | None) -> HomeTeam:
    return HomeTeam(
        id=team_id, name=team_display(canonical, year), short_code=team_code(canonical, year)
    )


def _venue(vid: int | None, name: str | None, city: str | None) -> HomeVenue | None:
    return HomeVenue(id=vid, name=name, city=city) if vid is not None and name else None


_MATCH_SQL = """
    SELECT m.id, m.start_date, s.year, m.stage, m.match_number, m.result, m.winner_id,
           m.win_by_runs, m.win_by_wickets, m.method,
           m.team1_id, t1.name AS t1_name, m.team2_id, t2.name AS t2_name,
           v.id AS venue_id, v.name AS venue_name, COALESCE(v.city, m.city) AS venue_city
    FROM match m
    JOIN season s ON s.id = m.season_id
    JOIN team t1 ON t1.id = m.team1_id
    JOIN team t2 ON t2.id = m.team2_id
    LEFT JOIN venue v ON v.id = m.venue_id
"""


def _scores(conn: Connection, match_id: int) -> list[HomeScore]:
    rows = conn.execute(
        text(
            """
            SELECT i.innings, i.team_id,
                   COALESCE(SUM(d.total_runs), 0) AS runs,
                   COUNT(*) FILTER (WHERE d.wicket_kind IS NOT NULL
                                    AND d.wicket_kind <> ALL(:nw)) AS wkts,
                   COUNT(*) FILTER (WHERE d.wides = 0 AND d.noballs = 0) AS legal
            FROM innings_resolved i
            LEFT JOIN delivery_resolved d ON d.match_id = i.match_id AND d.innings = i.innings
            WHERE i.match_id = :mid AND NOT i.super_over
            GROUP BY i.innings, i.team_id ORDER BY i.innings
            """
        ),
        {"mid": match_id, "nw": list(NOT_A_WICKET)},
    ).mappings()
    return [
        HomeScore(
            innings=r["innings"],
            team_id=r["team_id"],
            runs=int(r["runs"]),
            wickets=int(r["wkts"]),
            overs=overs_text(int(r["legal"])),
        )
        for r in rows
    ]


def _result_text(r: Any, t1: HomeTeam, t2: HomeTeam) -> str:
    if r["result"] == "no_result":
        return "No result"
    winner = {t1.id: t1, t2.id: t2}.get(r["winner_id"])
    if r["result"] == "tie":
        return f"Tied, {winner.short_code} won the super over" if winner else "Match tied"
    if winner is None:
        return "Result unknown"
    dls = " (DLS)" if r["method"] else ""
    if r["win_by_runs"]:
        n = r["win_by_runs"]
        return f"{winner.short_code} won by {n} run{'s' if n != 1 else ''}{dls}"
    if r["win_by_wickets"]:
        n = r["win_by_wickets"]
        return f"{winner.short_code} won by {n} wicket{'s' if n != 1 else ''}{dls}"
    return f"{winner.short_code} won{dls}"


def _home_match(conn: Connection, r: Any) -> HomeMatch:
    year = r["year"]
    t1 = _team(r["team1_id"], r["t1_name"], year)
    t2 = _team(r["team2_id"], r["t2_name"], year)
    return HomeMatch(
        id=r["id"],
        date=r["start_date"],
        season=year,
        title=match_title(r["stage"], r["match_number"]),
        stage=r["stage"],
        match_number=r["match_number"],
        venue=_venue(r["venue_id"], r["venue_name"], r["venue_city"]),
        team1=t1,
        team2=t2,
        winner_id=r["winner_id"],
        result=_result_text(r, t1, t2),
        scores=_scores(conn, r["id"]),
    )


def get_match(conn: Connection, match_id: int) -> HomeMatch:
    r = conn.execute(text(_MATCH_SQL + " WHERE m.id = :mid"), {"mid": match_id}).mappings().first()
    if r is None:
        raise NotFound(f"match {match_id} not found")
    return _home_match(conn, r)


def last_match(conn: Connection, before: dt.date | None = None) -> HomeMatch | None:
    where = " WHERE m.start_date <= :d" if before else ""
    r = (
        conn.execute(
            text(_MATCH_SQL + where + " ORDER BY m.start_date DESC, m.id DESC LIMIT 1"),
            {"d": before} if before else {},
        )
        .mappings()
        .first()
    )
    return _home_match(conn, r) if r else None


def season_card(conn: Connection, year: int) -> SeasonCard:
    r = (
        conn.execute(
            text(
                """
                SELECT m.id, m.winner_id, m.team1_id, t1.name AS t1, m.team2_id, t2.name AS t2
                FROM match m JOIN season s ON s.id = m.season_id
                JOIN team t1 ON t1.id = m.team1_id JOIN team t2 ON t2.id = m.team2_id
                WHERE s.year = :y AND m.stage = 'Final'
                ORDER BY m.start_date DESC LIMIT 1
                """
            ),
            {"y": year},
        )
        .mappings()
        .first()
    )
    champ = runner = None
    if r is not None and r["winner_id"] is not None:
        sides = {
            r["team1_id"]: _team(r["team1_id"], r["t1"], year),
            r["team2_id"]: _team(r["team2_id"], r["t2"], year),
        }
        champ = sides[r["winner_id"]]
        runner = next(t for tid, t in sides.items() if tid != r["winner_id"])
    return SeasonCard(
        year=year,
        champion=champ,
        runner_up=runner,
        final_match_id=r["id"] if r else None,
        next_season=f"IPL {year + 1} starts ~March",
    )


# --------------------------------------------------------------------------- fixtures
def _table_columns(conn: Connection, table: str) -> set[str]:
    return set(
        conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = :t"
            ),
            {"t": table},
        ).scalars()
    )


def next_fixture(conn: Connection, now: dt.datetime) -> NextFixture | None:
    cols = _table_columns(conn, "fixture")
    if not {"start_time", "team1_id", "team2_id"} <= cols:
        return None
    opt = {c: (f"f.{c}" if c in cols else "NULL") for c in ("id", "venue_id", "stage")}
    num = "f.match_number" if "match_number" in cols else "NULL::int"
    xi = "f.xi_confirmed" if "xi_confirmed" in cols else "false"
    r = (
        conn.execute(
            text(
                f"""
                SELECT {opt["id"]} AS id, f.start_time, f.team1_id, t1.name AS t1,
                       f.team2_id, t2.name AS t2, {opt["stage"]}::text AS stage,
                       {num} AS match_number, {xi} AS xi_confirmed,
                       v.id AS venue_id, v.name AS venue_name, v.city AS venue_city
                FROM fixture f
                JOIN team t1 ON t1.id = f.team1_id JOIN team t2 ON t2.id = f.team2_id
                LEFT JOIN venue v ON v.id = {opt["venue_id"]}
                WHERE f.start_time > :since
                ORDER BY f.start_time LIMIT 1
                """  # noqa: S608 - column names come from information_schema, not input
            ),
            {"since": now - dt.timedelta(hours=4)},
        )
        .mappings()
        .first()
    )
    if r is None:
        return None
    start: dt.datetime = r["start_time"]
    if start.tzinfo is None:
        start = start.replace(tzinfo=IST)
    year = start.year
    return NextFixture(
        id=r["id"],
        start=start,
        title=match_title(r["stage"], r["match_number"]),
        venue=_venue(r["venue_id"], r["venue_name"], r["venue_city"]),
        team1=_team(r["team1_id"], r["t1"], year),
        team2=_team(r["team2_id"], r["t2"], year),
        status="xi_confirmed" if r["xi_confirmed"] else "provisional",
    )


# --------------------------------------------------------------------------- state
def home_state(
    conn: Connection, now: dt.datetime | None = None, *, dev_spike_wagon: bool = False
) -> HomeState:
    now = (now or dt.datetime.now(IST)).astimezone(IST)
    fixture = next_fixture(conn, now)
    last = last_match(conn, now.date())
    phase = decide_phase(now, fixture.start if fixture else None, last.date if last else None)

    season = season_card(conn, last.season) if last else None
    xi_ok = wagon_ok = False
    if phase == "pre_match" and fixture is not None and fixture.id is not None:
        xi_ok = xi_available(conn, fixture.id)
    if phase == "post_match" and last is not None:
        wagon_ok = home_wagon.load_shots(last.id, query_flag=dev_spike_wagon) is not None
    hero, reason = choose_hero(phase, xi_available=xi_ok, wagon_available=wagon_ok)

    if hero == "B" and fixture is not None:
        hero_match = fixture.id
    elif phase == "off_season" and season is not None and season.final_match_id is not None:
        hero_match = season.final_match_id
    else:
        hero_match = last.id if last else None
    return HomeState(
        phase=phase,
        now=now,
        hero=hero,
        hero_match_id=hero_match,
        hero_reason=reason,
        next_fixture=fixture if phase != "off_season" else None,
        last_match=last,
        season=season,
    )


# --------------------------------------------------------------------------- C: worm
def ball_kind(batter_runs: int, total_runs: int, wicket_kind: str | None) -> BallKind:
    if wicket_kind is not None and wicket_kind not in NOT_A_WICKET:
        return "wicket"
    if batter_runs == 6:
        return "six"
    if batter_runs == 4:
        return "four"
    return "run" if total_runs > 0 else "dot"


def worm(conn: Connection, match_id: int) -> Worm:
    match = get_match(conn, match_id)
    teams = {match.team1.id: match.team1, match.team2.id: match.team2}
    rows = conn.execute(
        text(
            """
            SELECT i.innings, i.team_id, d.over, d.wides, d.noballs, d.batter_runs,
                   d.total_runs, d.wicket_kind
            FROM innings_resolved i
            JOIN delivery_resolved d ON d.match_id = i.match_id AND d.innings = i.innings
            WHERE i.match_id = :mid AND NOT i.super_over
            ORDER BY i.innings, d.ball_seq
            """
        ),
        {"mid": match_id},
    ).mappings()
    by_inn: dict[int, tuple[int, list[WormBall]]] = {}
    # innings -> [runs, wkts, legal_total, cur_over, legal_in_over]
    state: dict[int, list[int]] = {}
    for r in rows:
        inn = r["innings"]
        if inn not in by_inn:
            by_inn[inn] = (r["team_id"], [])
            state[inn] = [0, 0, 0, -1, 0]
        st = state[inn]
        if r["over"] != st[3]:
            st[3], st[4] = r["over"], 0
        legal = r["wides"] == 0 and r["noballs"] == 0
        st[0] += r["total_runs"]
        kind = ball_kind(r["batter_runs"], r["total_runs"], r["wicket_kind"])
        if kind == "wicket":
            st[1] += 1
        if legal:
            st[2] += 1
            st[4] += 1
        by_inn[inn][1].append(
            WormBall(
                x=round(r["over"] + st[4] / 6, 4),
                runs=st[0],
                wickets=st[1],
                kind=kind,
                label=f"{r['over']}.{max(1, st[4]) if legal else st[4] + 1}",
            )
        )
    innings: list[WormInnings] = []
    for inn, (team_id, balls) in sorted(by_inn.items()):
        st = state[inn]
        team = teams.get(team_id) or HomeTeam(id=team_id, name=f"Team {team_id}", short_code="?")
        innings.append(
            WormInnings(
                innings=inn,
                team=team,
                runs=st[0],
                wickets=st[1],
                overs=overs_text(st[2]),
                balls=balls,
            )
        )
    if not innings:
        raise NotFound(f"no ball-by-ball for match {match_id}")
    top = max(i.runs for i in innings)
    return Worm(
        match=match,
        innings=innings,
        ball_count=sum(len(i.balls) for i in innings),
        y_max=max(60, -(-(top + 15) // 10) * 10),
    )


# --------------------------------------------------------------------------- A: wagon
def _batting_card(conn: Connection, match_id: int) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in conn.execute(
            text(
                """
                SELECT d.batter_id, p.name, i.team_id, t.name AS team_name, s.year,
                       SUM(d.batter_runs) AS runs,
                       COUNT(*) FILTER (WHERE d.wides = 0) AS balls,
                       bool_or(o.out) AS out
                FROM delivery_resolved d
                JOIN innings_resolved i ON i.match_id = d.match_id AND i.innings = d.innings
                JOIN team t ON t.id = i.team_id
                JOIN match m ON m.id = d.match_id JOIN season s ON s.id = m.season_id
                JOIN player p ON p.id = d.batter_id
                LEFT JOIN LATERAL (
                    SELECT EXISTS (
                        SELECT 1 FROM delivery_resolved x
                        WHERE x.match_id = d.match_id AND x.innings = d.innings
                          AND x.player_out_id = d.batter_id
                          AND x.wicket_kind <> ALL(:nw)
                    ) AS out
                ) o ON true
                WHERE d.match_id = :mid AND NOT d.super_over
                GROUP BY d.batter_id, p.name, i.team_id, t.name, s.year
                """
            ),
            {"mid": match_id, "nw": list(NOT_A_WICKET)},
        ).mappings()
    ]


def _match_batter(card: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    exact = [b for b in card if b["name"].lower() == name.lower()]
    if exact:
        return exact[0]
    last = name.split()[-1].lower()
    cands = [b for b in card if b["name"].split()[-1].lower() == last]
    return cands[0] if len(cands) == 1 else None


def wagon(conn: Connection, match_id: int, *, dev_spike_wagon: bool = False) -> Wagon | None:
    shots = home_wagon.load_shots(match_id, query_flag=dev_spike_wagon)
    if not shots:
        return None
    top = home_wagon.top_innings(shots)
    if top is None:
        return None
    batter, shot_runs, best = top
    bat = _match_batter(_batting_card(conn, match_id), batter)
    team = _team(bat["team_id"], bat["team_name"], bat["year"]) if bat else None
    return Wagon(
        match_id=match_id,
        batter=bat["name"] if bat else batter,
        team=team,
        runs=int(bat["runs"]) if bat else shot_runs,
        balls=int(bat["balls"]) if bat else None,
        not_out=(not bat["out"]) if bat else None,
        left_handed=best[0].left_handed,
        shots=[
            Shot(
                over=s.over,
                ball=s.ball,
                label=f"{s.over}.{s.ball}",
                runs=s.runs,
                direction=s.direction,
                distance_pct=s.distance_pct,
                zone=s.zone,
                zone_name=home_wagon.ZONES.get(s.zone, "field"),
                bowler=s.bowler,
            )
            for s in best
        ],
        source=home_wagon.SPIKE_SOURCE,
    )


# --------------------------------------------------------------------------- B: XI
def xi_available(conn: Connection, match_id: int) -> bool:
    src = home_xi.detect_source(conn)
    return src is not None and len(home_xi.load_candidates(conn, match_id, src)) >= 11


def xi(conn: Connection, match_id: int) -> XI | None:
    src = home_xi.detect_source(conn)
    if src is None:
        return None
    cands = home_xi.load_candidates(conn, match_id, src)
    pick = home_xi.best_xi(cands)
    if pick is None:
        return None
    chosen = {c.id for c in pick.players}
    teams = sorted({c.team for c in cands})
    players = [
        XIPlayer(
            id=c.id,
            name=c.name,
            short_name=home_xi.short_name(c.name),
            team=c.team,
            role=c.role,  # type: ignore[arg-type]
            points=round(c.points, 1),
            picked=c.id in chosen,
            captain="C" if c.id == pick.captain.id else "VC" if c.id == pick.vice.id else None,
        )
        for c in sorted(cands, key=lambda c: (-c.points, c.name))
    ]
    return XI(match_id=match_id, kind="actual", teams=teams, players=players, total=pick.total)


# --------------------------------------------------------------------------- bento tiles
def _safe[T](fn: Callable[[], T]) -> T | None:
    try:
        return fn()
    except Exception:  # a broken tile must never break the page
        return None


def _latest_year(conn: Connection) -> int:
    return int(
        conn.execute(
            text("SELECT max(s.year) FROM match m JOIN season s ON s.id = m.season_id")
        ).scalar_one()
    )


def _table_tile(conn: Connection, year: int) -> TableTile | None:
    rows = (
        conn.execute(
            text(
                """
            WITH league AS (
                SELECT m.* FROM match m JOIN season s ON s.id = m.season_id
                WHERE s.year = :y AND m.stage IS NULL
            ), sides AS (
                SELECT team1_id AS team_id, winner_id, result FROM league
                UNION ALL SELECT team2_id, winner_id, result FROM league
            )
            SELECT sd.team_id, t.name, COUNT(*) AS played,
                   2 * COUNT(*) FILTER (WHERE sd.winner_id = sd.team_id)
                     + COUNT(*) FILTER (WHERE sd.result = 'no_result') AS pts
            FROM sides sd JOIN team t ON t.id = sd.team_id
            GROUP BY sd.team_id, t.name ORDER BY pts DESC, t.name LIMIT 2
            """
            ),
            {"y": year},
        )
        .mappings()
        .all()
    )
    if not rows:
        return None
    lead = rows[0]
    leader = _team(lead["team_id"], lead["name"], year)
    # tie on points is broken by NRR in the real table; defer to the seasons service then
    if len(rows) > 1 and rows[1]["pts"] == lead["pts"]:
        top = _safe(lambda: _seasons_leader(year))
        if top is not None:
            leader = top
    return TableTile(
        season=year,
        leader=leader,
        leader_points=int(lead["pts"]),
        played=int(lead["played"]),
        champion=season_card(conn, year).champion,
    )


def _seasons_leader(year: int) -> HomeTeam:
    from . import seasons  # owned by the seasons workstream; used read-only for NRR ties

    row = seasons.points_table(year).rows[0]
    return HomeTeam(id=row.team.id, name=row.team.name, short_code=row.team.short_code)


def _player_tile(conn: Connection, year: int) -> PlayersTile:
    def team_of(pid: str) -> str | None:
        name = conn.execute(
            text(
                """
                SELECT t.name FROM match_player_resolved mp
                JOIN match m ON m.id = mp.match_id JOIN season s ON s.id = m.season_id
                JOIN team t ON t.id = mp.team_id
                WHERE mp.player_id = :pid AND s.year = :y
                ORDER BY m.start_date DESC LIMIT 1
                """
            ),
            {"pid": pid, "y": year},
        ).scalar()
        return team_code(name, year) if name else None

    def top(sql: str, extra: dict[str, Any]) -> PlayerStatLine | None:
        r = conn.execute(text(sql), {"y": year, **extra}).mappings().first()
        if r is None:
            return None
        return PlayerStatLine(
            id=r["pid"], name=r["name"], team=team_of(r["pid"]), value=int(r["v"])
        )

    base = """
        FROM delivery_resolved d
        JOIN match m ON m.id = d.match_id JOIN season s ON s.id = m.season_id
        JOIN player p ON p.id = d.{who}
        WHERE s.year = :y AND NOT d.super_over {cond}
        GROUP BY d.{who}, p.name ORDER BY v DESC, p.name LIMIT 1
    """
    runs = top(
        "SELECT d.batter_id AS pid, p.name, SUM(d.batter_runs) AS v "
        + base.format(who="batter_id", cond=""),
        {},
    )
    wkts = top(
        "SELECT d.bowler_id AS pid, p.name, COUNT(*) AS v "
        + base.format(
            who="bowler_id", cond="AND d.wicket_kind IS NOT NULL AND d.wicket_kind <> ALL(:nb)"
        ),
        {"nb": list(NOT_BOWLER_WICKET)},
    )
    return PlayersTile(season=year, top_runs=runs, top_wickets=wkts)


def _h2h_tile(conn: Connection) -> H2HTile | None:
    r = (
        conn.execute(
            text(
                """
                SELECT LEAST(m.team1_id, m.team2_id) AS a, GREATEST(m.team1_id, m.team2_id) AS b,
                       COUNT(*) AS n,
                       COUNT(*) FILTER (WHERE m.winner_id = LEAST(m.team1_id, m.team2_id)) AS aw,
                       COUNT(*) FILTER (WHERE m.winner_id = GREATEST(m.team1_id, m.team2_id)) AS bw
                FROM match m GROUP BY 1, 2 ORDER BY n DESC, a, b LIMIT 1
                """
            )
        )
        .mappings()
        .first()
    )
    if r is None:
        return None
    names = dict(
        conn.execute(
            text("SELECT id, name FROM team WHERE id IN (:a, :b)"), {"a": r["a"], "b": r["b"]}
        ).all()
    )
    return H2HTile(
        team_a=_team(r["a"], names[r["a"]], None),
        team_b=_team(r["b"], names[r["b"]], None),
        matches=int(r["n"]),
        a_wins=int(r["aw"]),
        b_wins=int(r["bw"]),
    )


def _venues_tile(conn: Connection, year: int) -> VenuesTile:
    used = conn.execute(
        text(
            "SELECT COUNT(DISTINCT m.venue_id) FROM match m JOIN season s ON s.id = m.season_id "
            "WHERE s.year = :y"
        ),
        {"y": year},
    ).scalar_one()
    r = (
        conn.execute(
            text(
                """
                WITH first_inn AS (
                    SELECT m.venue_id, d.match_id, SUM(d.total_runs) AS runs
                    FROM delivery_resolved d
                    JOIN match m ON m.id = d.match_id JOIN season s ON s.id = m.season_id
                    WHERE s.year = :y AND d.innings = 1 AND NOT d.super_over
                      AND m.result <> 'no_result'
                    GROUP BY m.venue_id, d.match_id
                )
                SELECT v.id, v.name, v.city, ROUND(AVG(f.runs)) AS par, COUNT(*) AS n
                FROM first_inn f JOIN venue v ON v.id = f.venue_id
                GROUP BY v.id, v.name, v.city HAVING COUNT(*) >= 4
                ORDER BY par DESC LIMIT 1
                """
            ),
            {"y": year},
        )
        .mappings()
        .first()
    )
    return VenuesTile(
        season=year,
        venues_used=int(used),
        top_par_venue=_venue(r["id"], r["name"], r["city"]) if r else None,
        top_par=int(r["par"]) if r else None,
    )


def _records_tile(conn: Connection) -> RecordsTile | None:
    r = (
        conn.execute(
            text(
                """
                SELECT d.match_id, d.innings, i.team_id, s.year,
                       SUM(d.total_runs) AS runs,
                       COUNT(*) FILTER (WHERE d.wicket_kind IS NOT NULL
                                        AND d.wicket_kind <> ALL(:nw)) AS wkts,
                       m.team1_id, m.team2_id
                FROM delivery_resolved d
                JOIN innings_resolved i ON i.match_id = d.match_id AND i.innings = d.innings
                JOIN match m ON m.id = d.match_id JOIN season s ON s.id = m.season_id
                WHERE NOT d.super_over
                GROUP BY d.match_id, d.innings, i.team_id, s.year, m.team1_id, m.team2_id
                ORDER BY runs DESC, d.match_id LIMIT 1
                """
            ),
            {"nw": list(NOT_A_WICKET)},
        )
        .mappings()
        .first()
    )
    if r is None:
        return None
    opp_id = r["team2_id"] if r["team_id"] == r["team1_id"] else r["team1_id"]
    names = dict(
        conn.execute(
            text("SELECT id, name FROM team WHERE id IN (:a, :b)"),
            {"a": r["team_id"], "b": opp_id},
        ).all()
    )
    return RecordsTile(
        team=_team(r["team_id"], names[r["team_id"]], r["year"]),
        opponent=_team(opp_id, names[opp_id], r["year"]),
        runs=int(r["runs"]),
        wickets=int(r["wkts"]),
        year=int(r["year"]),
        match_id=int(r["match_id"]),
    )


def _fantasy_tile(year: int) -> FantasyTile | None:
    from .fantasy import leaderboard  # local: fantasy loads its own cache on first use

    lb = leaderboard(year, min_matches=1, limit=1)
    if not lb.rows:
        return None
    r = lb.rows[0]
    return FantasyTile(
        season=lb.season,
        top=PlayerStatLine(
            id=r.player.id,
            name=r.player.display_name or r.player.name,
            team=r.team.short_code,
            value=r.total,
        ),
        matches=r.n,
        mean=r.mean,
    )


_TILES_TTL_S = 300.0
_tiles_cache: tuple[float, HomeTiles] | None = None


def tiles(conn: Connection) -> HomeTiles:
    """Bento tiles, memoised for ``_TILES_TTL_S`` (they only change after a post-match harvest)."""
    global _tiles_cache
    now = time.monotonic()
    if _tiles_cache is not None and now - _tiles_cache[0] < _TILES_TTL_S:
        return _tiles_cache[1]
    out = _compute_tiles(conn)
    _tiles_cache = (now, out)
    return out


def _compute_tiles(conn: Connection) -> HomeTiles:
    year = _latest_year(conn)

    def guarded[T](fn: Callable[[], T]) -> T | None:
        # each tile in its own savepoint so one failing query does not poison the others
        try:
            with conn.begin_nested():
                return fn()
        except Exception:
            return None

    return HomeTiles(
        table=guarded(lambda: _table_tile(conn, year)),
        players=guarded(lambda: _player_tile(conn, year)),
        h2h=guarded(lambda: _h2h_tile(conn)),
        venues=guarded(lambda: _venues_tile(conn, year)),
        records=guarded(lambda: _records_tile(conn)),
        fantasy=guarded(lambda: _fantasy_tile(year)),
    )

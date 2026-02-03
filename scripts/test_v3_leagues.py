import asyncio
from datetime import date
from fm_manager.core import init_db, get_session_maker
from fm_manager.engine.season_simulator import SeasonSimulator
from fm_manager.core.models import League
from sqlalchemy import select

async def sim_league(league_name, country):
    await init_db()
    session_maker = get_session_maker()
    async with session_maker() as session:
        r = await session.execute(
            select(League).where(
                (League.name == league_name) & (League.country == country)))
        )
        league = r.scalar_one_or_none()
        if not league:
            return None
        simulator = SeasonSimulator(session, engine_version="v3")
        result = await simulator.simulate_season(league_id=league.id, season_year=2024, start_date=date(2024, 8, 15), use_dynamic_states=False)
        avg_goals = sum(m.home_score + m.away_score for m in result.matches) / len(result.matches)
        champion = result.get_champion()
        champ_name = champion.club_name if champion else "N/A"
        champ_points = champion.points if champion else 0
        return f"{league_name}: {avg_goals:.2f} | Champ: {champ_name} ({champ_points} pts)"

leagues = [
    ("Premier League", "England"),
    ("La Liga", "Spain"),
    ("Bundesliga", "Germany"),
    ("Serie A", "Italy"),
    ("Ligue 1", "France"),
]
targets = {"Premier League": 2.55, "La Liga": 2.35, "Bundesliga": 2.75, "Serie A": 2.40, "Ligue 1": 2.40}

print("=== V3 Engine Final Results ===")
for league, country in leagues:
    r = asyncio.run(sim_league(league, country))
    if r:
        target = targets[league]
        actual = float(r.split("|")[0].split(": ")[1].strip())
        diff = actual - target
        status = "OK" if abs(diff) < 0.15 else "OFF"
        print(f"{r} | Target: {target:.2f} (Diff: {diff:+.2f}) [{status}]")

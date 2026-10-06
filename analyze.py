"""Portable Formula 1 analysis with explicit units and defensible metrics."""
import argparse,json
from pathlib import Path
import pandas as pd

def time_seconds(value):
    try:
        text=str(value).strip()
        if text.startswith('+') or text in {r'\N','nan',''}:return None
        parts=[float(x) for x in text.split(':')]
        if len(parts)>3 or any(v<0 for v in parts):return None
        result=0.
        for part in parts:result=result*60+part
        return result if result>0 else None
    except (ValueError,TypeError):return None

def fastest_laps(results,races,drivers,circuits):
    rows=results.copy()
    rows['lap_seconds']=rows.fastestLapTime.map(time_seconds)
    rows=rows.dropna(subset=['lap_seconds'])
    rows=rows.merge(races[['raceId','circuitId']],on='raceId',validate='many_to_one')
    if rows.empty:return pd.DataFrame()
    rows=rows.loc[rows.groupby('circuitId').lap_seconds.idxmin()]
    return rows.merge(drivers[['driverId','forename','surname']],on='driverId',validate='many_to_one').merge(circuits[['circuitId','name']],on='circuitId',validate='many_to_one')

def analyze(folder):
    def read(name):return pd.read_csv(Path(folder)/(name+'.csv'),na_values=[r'\N'])
    results,races,drivers,constructors,circuits,status=[read(n) for n in ('results','races','drivers','constructors','circuits','status')]
    for col in ('positionOrder','points','grid'):results[col]=pd.to_numeric(results[col],errors='coerce')
    joined=results.merge(races[['raceId','year','circuitId']],on='raceId',validate='many_to_one')
    wins=joined[joined.positionOrder==1]
    constructor_wins=wins.groupby(['year','constructorId']).size().rename('wins').reset_index().merge(constructors[['constructorId','name']],on='constructorId')
    top_year=constructor_wins.sort_values(['year','wins','name'],ascending=[True,False,True]).drop_duplicates('year')
    driver_wins=wins.groupby('driverId').size().rename('wins').reset_index().merge(drivers[['driverId','forename','surname']],on='driverId').sort_values('wins',ascending=False)
    decade=wins.assign(decade=(wins.year//10)*10).groupby(['decade','driverId']).size().rename('wins').reset_index()
    decade=decade.sort_values(['decade','wins'],ascending=[True,False]).drop_duplicates('decade').merge(drivers[['driverId','forename','surname']],on='driverId')
    podium=results.groupby('constructorId').agg(entries=('raceId','count'),podiums=('positionOrder',lambda x:(x<=3).sum()),average_points=('points','mean'))
    podium['podium_rate']=podium.podiums/podium.entries
    podium=podium.reset_index().merge(constructors[['constructorId','name']],on='constructorId')
    fastest=fastest_laps(results,races,drivers,circuits)
    grid=joined[(joined.grid>0)&joined.positionOrder.notna()].copy();grid['net_position_gain']=grid.grid-grid.positionOrder
    gains=grid.groupby('circuitId').net_position_gain.sum().reset_index().merge(circuits[['circuitId','name']],on='circuitId')
    retirement=joined.merge(status,on='statusId',validate='many_to_one')
    # Finished or classified laps behind the winner are not retirements.
    retirement=retirement[~retirement.status.str.match(r'^Finished$|^\+\d+ Laps?$',na=False)]
    retirement=retirement.groupby('circuitId').size().rename('nonfinish_status_count').reset_index().merge(circuits[['circuitId','name']],on='circuitId')
    counts=races.groupby('circuitId').size().rename('race_count').reset_index().merge(circuits[['circuitId','name']],on='circuitId')
    lap_times=read('lap_times');lap_times['milliseconds']=pd.to_numeric(lap_times.milliseconds,errors='coerce')
    averages=lap_times.merge(races[['raceId','circuitId']],on='raceId',validate='many_to_one').groupby('circuitId').milliseconds.mean().div(1000).rename('mean_recorded_lap_seconds').reset_index().merge(circuits[['circuitId','name']],on='circuitId')
    tables={'constructor_winners_by_year':top_year,'driver_wins':driver_wins,'driver_wins_by_decade':decade,'constructor_podium_rates':podium,
            'fastest_recorded_lap_by_circuit':fastest,'net_position_gain_by_circuit':gains,'nonfinish_status_by_circuit':retirement,'races_by_circuit':counts,
            'average_recorded_lap_time':averages,'grid_vs_finish_2024':grid[grid.year==2024]}
    return {'dataset':'Supplied historical Ergast-style CSV files','result_rows':len(results),'race_rows':len(races),
            'fastest_lap_method':'minimum parsed fastestLapTime in seconds; fastestLap lap number is not used as speed',
            'position_gain_limitation':'Net grid-to-finish position change is not an observed overtaking count.',
            'nonfinish_limitation':'Nonfinish status includes disqualifications, nonstarts and retirements; counts are labeled accordingly.',
            'tables':{name:json.loads(table.to_json(orient='records')) for name,table in tables.items()}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--output',type=Path,default=Path('analysis.json'))
    a=p.parse_args();r=analyze(a.data_dir);a.output.write_text(json.dumps(r,indent=2,allow_nan=False),encoding='utf-8');print(r['result_rows'],r['race_rows'])
if __name__=='__main__':main()

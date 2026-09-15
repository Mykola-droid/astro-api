from fastapi import FastAPI
from pydantic import BaseModel
import swisseph as swe
from datetime import datetime

app = FastAPI()

class ChartRequest(BaseModel):
    date: str  # "YYYY-MM-DD"
    time: str  # "HH:MM"
    lat: float
    lon: float

iau_boundaries = [
    {"name": "Риби", "start": 351.0, "end": 28.0},
    {"name": "Овен", "start": 28.0, "end": 54.0},
    {"name": "Телець", "start": 54.0, "end": 90.0},
    {"name": "Близнюки", "start": 90.0, "end": 118.0},
    {"name": "Рак", "start": 118.0, "end": 139.0},
    {"name": "Лев", "start": 139.0, "end": 176.0},
    {"name": "Діва", "start": 176.0, "end": 223.0},
    {"name": "Терези", "start": 223.0, "end": 246.0},
    {"name": "Скорпіон", "start": 246.0, "end": 253.0},
    {"name": "Змієносець", "start": 253.0, "end": 272.0},
    {"name": "Стрілець", "start": 272.0, "end": 305.0},
    {"name": "Козоріг", "start": 305.0, "end": 328.0},
    {"name": "Водолій", "start": 328.0, "end": 351.0}
]

def get_sign_and_degree(longitude):
    longitude = (longitude % 360 + 360) % 360
    for constel in iau_boundaries:
        if constel["start"] > constel["end"]:
            if longitude >= constel["start"] or longitude < constel["end"]:
                pos = longitude - constel["start"] if longitude >= constel["start"] else (360 - constel["start"]) + longitude
                return {"sign": constel["name"], "degree": f"{pos % 30:.1f}°"}
        else:
            if constel["start"] <= longitude < constel["end"]:
                pos = longitude - constel["start"]
                return {"sign": constel["name"], "degree": f"{pos % 30:.1f}°"}
    return {"sign": "Риби", "degree": "0.0°"}

@app.post("/calculate")
def calculate_chart(req: ChartRequest):
    try:
        dt = datetime.strptime(f"{req.date} {req.time}", "%Y-%m-%d %H:%M")
        tz_offset = req.lon / 15.0
        ut_hour = dt.hour + dt.minute / 60.0 - tz_offset
        jd = swe.julday(dt.year, dt.month, dt.day, ut_hour)

        planets = [
            ("Сонце ☉", swe.SUN),
            ("Місяць ☽", swe.MOON),
            ("Меркурій ☿", swe.MERCURY),
            ("Венера ♀", swe.VENUS)
        ]

        placements = []
        for name, p_id in planets:
            res, flags = swe.calc_ut(jd, p_id)
            placement = get_sign_and_degree(res[0])
            placements.append({
                "planet": name,
                "sign": placement["sign"],
                "degree": placement["degree"]
            })

        houses, ascmc = swe.houses(jd, req.lat, req.lon, b'P')
        asc_placement = get_sign_and_degree(ascmc[0])
        placements.insert(2, {
            "planet": "Асцендент ↗",
            "sign": asc_placement["sign"],
            "degree": asc_placement["degree"]
        })

        return {"status": "success", "placements": placements}
    except Exception as e:
        return {"status": "error", "message": str(e)}

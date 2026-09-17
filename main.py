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

import math
from fastapi import Response

# 1. Повний список 13 сузір'їв IAU (включаючи Ophiuchus)
ZODIAC_13 = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
    "Libra", "Scorpio", "Ophiuchus", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

def generate_svg_chart(planets_data: dict) -> str:
    width, height = 600, 600
    cx, cy, radius = 300, 300, 240
    inner_radius = 170

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">',
        f'<rect width="{width}" height="{height}" fill="#0b0f19"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" stroke="#4a5568" stroke-width="2" fill="none"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{inner_radius}" stroke="#4a5568" stroke-width="1" fill="none"/>'
    ]

    # Створення 13 секторів
    sector_angle = 360 / 13
    for i, name in enumerate(ZODIAC_13):
        angle_deg = i * sector_angle - 90
        angle_rad = math.radians(angle_deg)

        x1 = cx + inner_radius * math.cos(angle_rad)
        y1 = cy + inner_radius * math.sin(angle_rad)
        x2 = cx + radius * math.cos(angle_rad)
        y2 = cy + radius * math.sin(angle_rad)
        svg_lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#2d3748" stroke-width="1.5"/>')

        mid_angle_rad = math.radians(angle_deg + sector_angle / 2)
        tx = cx + (radius - 25) * math.cos(mid_angle_rad)
        ty = cy + (radius - 25) * math.sin(mid_angle_rad)
        svg_lines.append(
            f'<text x="{tx}" y="{ty}" fill="#a0aec0" font-size="11" font-family="Arial" '
            f'text-anchor="middle" dominant-baseline="central">{name[:3].upper()}</text>'
        )

    # Відображення планет на карті
    colors = {"Sun": "#ecc94b", "Moon": "#e2e8f0", "Ascendant": "#e53e3e"}

    for planet, deg in planets_data.items():
        if isinstance(deg, (int, float)):
            p_angle_rad = math.radians(deg - 90)
            px = cx + (inner_radius - 30) * math.cos(p_angle_rad)
            py = cy + (inner_radius - 30) * math.sin(p_angle_rad)
            color = colors.get(planet, "#3182ce")

            svg_lines.append(f'<circle cx="{px}" cy="{py}" r="5" fill="{color}"/>')
            svg_lines.append(
                f'<text x="{px}" y="{py - 10}" fill="{color}" font-size="10" font-family="Arial" '
                f'font-weight="bold" text-anchor="middle">{planet[:3]}</text>'
            )

    svg_lines.append('</svg>')
    return "".join(svg_lines)

# 2. Новий Ендпоінт для генерації SVG
@app.post("/chart-svg")
async def get_chart_svg(data: dict):
    planets = {
        "Sun": float(data.get("sun_deg", 240.0)),
        "Moon": float(data.get("moon_deg", 110.0)),
        "Ascendant": float(data.get("asc_deg", 85.0))
    }
    svg_code = generate_svg_chart(planets)
    return Response(content=svg_code, media_type="image/svg+xml")

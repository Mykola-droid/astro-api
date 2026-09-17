from fastapi import FastAPI, Response
from pydantic import BaseModel
import swisseph as swe
from datetime import datetime
import math

app = FastAPI()

class ChartRequest(BaseModel):
    date: str  # "YYYY-MM-DD"
    time: str  # "HH:MM"
    lat: float
    lon: float
    lang: str = "en"  # Основна мова за замовчуванням — англійська

# 1. Астрономічні межі 13 сузір'їв IAU
iau_boundaries = [
    {"code": "Pisces", "start": 351.0, "end": 28.0},
    {"code": "Aries", "start": 28.0, "end": 54.0},
    {"code": "Taurus", "start": 54.0, "end": 90.0},
    {"code": "Gemini", "start": 90.0, "end": 118.0},
    {"code": "Cancer", "start": 118.0, "end": 139.0},
    {"code": "Leo", "start": 139.0, "end": 176.0},
    {"code": "Virgo", "start": 176.0, "end": 223.0},
    {"code": "Libra", "start": 223.0, "end": 246.0},
    {"code": "Scorpius", "start": 246.0, "end": 253.0},
    {"code": "Ophiuchus", "start": 253.0, "end": 272.0},
    {"code": "Sagittarius", "start": 272.0, "end": 305.0},
    {"code": "Capricornus", "start": 305.0, "end": 328.0},
    {"code": "Aquarius", "start": 328.0, "end": 351.0}
]

# 2. Мультимовний словник (EN, UK, DE, ES, PL, FR, IT)
TRANSLATIONS = {
    "en": {
        "Sun": "Sun ☉", "Moon": "Moon ☽", "Ascendant": "Ascendant ↗",
        "Mercury": "Mercury ☿", "Venus": "Venus ♀", "Mars": "Mars ♂",
        "Jupiter": "Jupiter ♃", "Saturn": "Saturn ♄",
        "Aries": "Aries", "Taurus": "Taurus", "Gemini": "Gemini", "Cancer": "Cancer",
        "Leo": "Leo", "Virgo": "Virgo", "Libra": "Libra", "Scorpius": "Scorpius",
        "Ophiuchus": "Ophiuchus", "Sagittarius": "Sagittarius", "Capricornus": "Capricorn",
        "Aquarius": "Aquarius", "Pisces": "Pisces"
    },
    "uk": {
        "Sun": "Сонце ☉", "Moon": "Місяць ☽", "Ascendant": "Асцендент ↗",
        "Mercury": "Меркурій ☿", "Venus": "Венера ♀", "Mars": "Марс ♂",
        "Jupiter": "Юпітер ♃", "Saturn": "Сатурн ♄",
        "Aries": "Овен", "Taurus": "Телець", "Gemini": "Близнюки", "Cancer": "Рак",
        "Leo": "Лев", "Virgo": "Діва", "Libra": "Терези", "Scorpius": "Скорпіон",
        "Ophiuchus": "Змієносець", "Sagittarius": "Стрілець", "Capricornus": "Козоріг",
        "Aquarius": "Водолій", "Pisces": "Риби"
    },
    "de": {
        "Sun": "Sonne ☉", "Moon": "Mond ☽", "Ascendant": "Aszendent ↗",
        "Mercury": "Merkur ☿", "Venus": "Venus ♀", "Mars": "Mars ♂",
        "Jupiter": "Jupiter ♃", "Saturn": "Saturn ♄",
        "Aries": "Widder", "Taurus": "Stier", "Gemini": "Zwillinge", "Cancer": "Krebs",
        "Leo": "Löwe", "Virgo": "Jungfrau", "Libra": "Waage", "Scorpius": "Skorpion",
        "Ophiuchus": "Schlangenträger", "Sagittarius": "Schütze", "Capricornus": "Steinbock",
        "Aquarius": "Wassermann", "Pisces": "Fische"
    },
    "es": {
        "Sun": "Sol ☉", "Moon": "Luna ☽", "Ascendant": "Ascendente ↗",
        "Mercury": "Mercurio ☿", "Venus": "Venus ♀", "Mars": "Marte ♂",
        "Jupiter": "Júpiter ♃", "Saturn": "Saturno ♄",
        "Aries": "Aries", "Taurus": "Tauro", "Gemini": "Géminis", "Cancer": "Cáncer",
        "Leo": "Leo", "Virgo": "Virgo", "Libra": "Libra", "Scorpius": "Escorpio",
        "Ophiuchus": "Ofiuco", "Sagittarius": "Sagitario", "Capricornus": "Capricornio",
        "Aquarius": "Acuario", "Pisces": "Piscis"
    },
    "pl": {
        "Sun": "Słońce ☉", "Moon": "Księżyc ☽", "Ascendant": "Askendent ↗",
        "Mercury": "Merkury ☿", "Venus": "Wenus ♀", "Mars": "Mars ♂",
        "Jupiter": "Jowisz ♃", "Saturn": "Saturn ♄",
        "Aries": "Baran", "Taurus": "Byk", "Gemini": "Bliźnięta", "Cancer": "Rak",
        "Leo": "Lew", "Virgo": "Panna", "Libra": "Waga", "Scorpius": "Skorpion",
        "Ophiuchus": "Wężownik", "Sagittarius": "Strzelec", "Capricornus": "Koziorożec",
        "Aquarius": "Wodnik", "Pisces": "Ryby"
    },
    "fr": {
        "Sun": "Soleil ☉", "Moon": "Lune ☽", "Ascendant": "Ascendant ↗",
        "Mercury": "Mercure ☿", "Venus": "Vénus ♀", "Mars": "Mars ♂",
        "Jupiter": "Jupiter ♃", "Saturn": "Saturne ♄",
        "Aries": "Bélier", "Taurus": "Taureau", "Gemini": "Gémeaux", "Cancer": "Cancer",
        "Leo": "Lion", "Virgo": "Vierge", "Libra": "Balance", "Scorpius": "Scorpion",
        "Ophiuchus": "Serpentaire", "Sagittarius": "Sagittaire", "Capricornus": "Capricorne",
        "Aquarius": "Verseau", "Pisces": "Poissons"
    },
    "it": {
        "Sun": "Sole ☉", "Moon": "Luna ☽", "Ascendant": "Ascendente ↗",
        "Mercury": "Mercurio ☿", "Venus": "Venere ♀", "Mars": "Marte ♂",
        "Jupiter": "Giove ♃", "Saturn": "Saturno ♄",
        "Aries": "Ariete", "Taurus": "Toro", "Gemini": "Gemelli", "Cancer": "Cancro",
        "Leo": "Leone", "Virgo": "Vergine", "Libra": "Bilancia", "Scorpius": "Scorpione",
        "Ophiuchus": "Ofiuco", "Sagittarius": "Sagittario", "Capricornus": "Capricorno",
        "Aquarius": "Acquario", "Pisces": "Pesci"
    }
}

def get_sign_and_degree(longitude, lang="en"):
    longitude = (longitude % 360 + 360) % 360
    dict_lang = TRANSLATIONS.get(lang, TRANSLATIONS["en"])

    for constel in iau_boundaries:
        code = constel["code"]
        translated_sign = dict_lang.get(code, code)

        if constel["start"] > constel["end"]:
            if longitude >= constel["start"] or longitude < constel["end"]:
                pos = longitude - constel["start"] if longitude >= constel["start"] else (360 - constel["start"]) + longitude
                return {"sign": translated_sign, "degree": f"{pos % 30:.1f}°"}
        else:
            if constel["start"] <= longitude < constel["end"]:
                pos = longitude - constel["start"]
                return {"sign": translated_sign, "degree": f"{pos % 30:.1f}°"}

    return {"sign": dict_lang.get("Pisces", "Pisces"), "degree": "0.0°"}

@app.post("/calculate")
def calculate_chart(req: ChartRequest):
    try:
        dt = datetime.strptime(f"{req.date} {req.time}", "%Y-%m-%d %H:%M")
        tz_offset = req.lon / 15.0
        ut_hour = dt.hour + dt.minute / 60.0 - tz_offset
        jd = swe.julday(dt.year, dt.month, dt.day, ut_hour)

        dict_lang = TRANSLATIONS.get(req.lang, TRANSLATIONS["en"])

        planets = [
            ("Sun", swe.SUN),
            ("Moon", swe.MOON),
            ("Mercury", swe.MERCURY),
            ("Venus", swe.VENUS),
            ("Mars", swe.MARS),
            ("Jupiter", swe.JUPITER),
            ("Saturn", swe.SATURN)
        ]

        placements = []
        for p_code, p_id in planets:
            res, flags = swe.calc_ut(jd, p_id)
            placement = get_sign_and_degree(res[0], req.lang)
            placements.append({
                "planet": dict_lang.get(p_code, p_code),
                "sign": placement["sign"],
                "degree": placement["degree"]
            })

        # Асцендент
        houses, ascmc = swe.houses(jd, req.lat, req.lon, b'P')
        asc_placement = get_sign_and_degree(ascmc[0], req.lang)
        placements.insert(2, {
            "planet": dict_lang.get("Ascendant", "Ascendant"),
            "sign": asc_placement["sign"],
            "degree": asc_placement["degree"]
        })

        return {"status": "success", "placements": placements}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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

    zodiac_codes = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpius", "Ophiuchus", "Sagittarius", "Capricornus", "Aquarius", "Pisces"]
    sector_angle = 360 / 13

    for i, name in enumerate(zodiac_codes):
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
            f'<text x="{tx}" y="{ty}" fill="#a0aec0" font-size="11" font-family="Arial" text-anchor="middle" dominant-baseline="central">{name[:3].upper()}</text>'
        )

    colors = {"Sun": "#ecc94b", "Moon": "#e2e8f0", "Ascendant": "#e53e3e"}
    for planet, deg in planets_data.items():
        if isinstance(deg, (int, float)):
            p_angle_rad = math.radians(deg - 90)
            px = cx + (inner_radius - 30) * math.cos(p_angle_rad)
            py = cy + (inner_radius - 30) * math.sin(p_angle_rad)
            color = colors.get(planet, "#3182ce")
            svg_lines.append(f'<circle cx="{px}" cy="{py}" r="5" fill="{color}"/>')
            svg_lines.append(f'<text x="{px}" y="{py - 10}" fill="{color}" font-size="10" font-family="Arial" font-weight="bold" text-anchor="middle">{planet[:3]}</text>')

    svg_lines.append('</svg>')
    return "".join(svg_lines)

@app.post("/chart-svg")
async def get_chart_svg(data: dict):
    planets = {
        "Sun": float(data.get("sun_deg", 240.0)),
        "Moon": float(data.get("moon_deg", 110.0)),
        "Ascendant": float(data.get("asc_deg", 85.0))
    }
    svg_code = generate_svg_chart(planets)
    return Response(content=svg_code, media_type="image/svg+xml")

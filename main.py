from fastapi import FastAPI, Response
from pydantic import BaseModel
import swisseph as swe
from datetime import datetime, timedelta
import math
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo

app = FastAPI()
tf = TimezoneFinder()

# Межі сузір'їв фіксовані відносно зір (J2000), тому й координати планет мають бути в системі J2000.
# Без цього виникає зсув через прецесію (≈0,014° на рік від 2000 р.): 0,35° для 1975 р., 0,7° для 1950 р.
swe.set_sid_mode(swe.SIDM_J2000, 0, 0)
CALC_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL


class ChartRequest(BaseModel):
    date: str  # "YYYY-MM-DD"
    time: str  # "HH:MM"
    lat: float
    lon: float
    lang: str = "en"


# 1. Астрономічні межі 13 сузір'їв IAU (еклиптична довгота, рівнодення J2000.0).
# Значення НЕ округлені: кожна межа є початком наступного сузір'я.
# Позиції планет рахуються в тій самій системі відліку (J2000), див. CALC_FLAGS нижче.
iau_boundaries = [
    {"code": "Pisces", "start": 351.573, "end": 28.687},
    {"code": "Aries", "start": 28.687, "end": 53.417},
    {"code": "Taurus", "start": 53.417, "end": 90.140},
    {"code": "Gemini", "start": 90.140, "end": 117.988},
    {"code": "Cancer", "start": 117.988, "end": 138.038},
    {"code": "Leo", "start": 138.038, "end": 173.851},
    {"code": "Virgo", "start": 173.851, "end": 217.810},
    {"code": "Libra", "start": 217.810, "end": 241.047},
    {"code": "Scorpius", "start": 241.047, "end": 247.638},
    {"code": "Ophiuchus", "start": 247.638, "end": 266.238},
    {"code": "Sagittarius", "start": 266.238, "end": 299.656},
    {"code": "Capricornus", "start": 299.656, "end": 327.488},
    {"code": "Aquarius", "start": 327.488, "end": 351.573}
]

# 2. Повний мультимовний словник (EN, UK, DE, ES, PL, FR, IT)
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
                return {"sign": translated_sign, "degree": f"{pos:.1f}°"}
        else:
            if constel["start"] <= longitude < constel["end"]:
                pos = longitude - constel["start"]
                return {"sign": translated_sign, "degree": f"{pos:.1f}°"}
    return {"sign": dict_lang.get("Pisces", "Pisces"), "degree": "0.0°"}


def generate_13month_gregorian_map(start_year=2026):
    start_date = datetime(start_year, 3, 21)
    month_names = [
        "Місяць 1", "Місяць 2", "Місяць 3", "Місяць 4",
        "Місяць 5", "Місяць 6", "Місяць 7", "Місяць 8",
        "Місяць 9", "Місяць 10", "Місяць 11", "Місяць 12",
        "Місяць 13 (Мерцедоній)"
    ]
    calendar_map = []
    current = start_date
    for i in range(13):
        days_in_month = 29 if i == 12 else 28
        end_date = current + timedelta(days=days_in_month - 1)
        calendar_map.append({
            "month_num": i + 1,
            "month_name": month_names[i],
            "gregorian_range": f"{current.strftime('%d.%m')} – {end_date.strftime('%d.%m.%Y')}",
            "start_date": current.strftime('%Y-%m-%d')
        })
        current = end_date + timedelta(days=1)
    return calendar_map


@app.post("/calculate")
def calculate_chart(req: ChartRequest):
    try:
        dt_naive = datetime.strptime(f"{req.date} {req.time}", "%Y-%m-%d %H:%M")

        # Визначаємо РЕАЛЬНИЙ часовий пояс за координатами (IANA tz database),
        # враховуючи літній/зимовий час на конкретну дату — замість наближення "довгота/15"
        tz_name = tf.timezone_at(lat=req.lat, lng=req.lon)
        if tz_name is None:
            tz_name = "UTC"

        local_tz = ZoneInfo(tz_name)
        dt_local = dt_naive.replace(tzinfo=local_tz)
        dt_utc = dt_local.astimezone(ZoneInfo("UTC"))

        ut_hour = dt_utc.hour + dt_utc.minute / 60.0
        jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, ut_hour)

        dict_lang = TRANSLATIONS.get(req.lang, TRANSLATIONS["en"])

        planets = [
            ("Sun", swe.SUN), ("Moon", swe.MOON), ("Mercury", swe.MERCURY),
            ("Venus", swe.VENUS), ("Mars", swe.MARS), ("Jupiter", swe.JUPITER),
            ("Saturn", swe.SATURN)
        ]

        placements = []
        for p_code, p_id in planets:
            res, flags = swe.calc_ut(jd, p_id, CALC_FLAGS)
            placement = get_sign_and_degree(res[0], req.lang)
            placements.append({
                "planet": dict_lang.get(p_code, p_code),
                "sign": placement["sign"],
                "degree": placement["degree"],
                "abs_deg": round(res[0], 2)
            })

        # Асцендент
        try:
            houses, ascmc = swe.houses_ex(jd, req.lat, req.lon, b'P', swe.FLG_SIDEREAL)
        except Exception:
            # Плацидус не рахується за полярним колом; Асцендент від системи домів не залежить
            houses, ascmc = swe.houses_ex(jd, req.lat, req.lon, b'O', swe.FLG_SIDEREAL)
        asc_placement = get_sign_and_degree(ascmc[0], req.lang)
        placements.insert(2, {
            "planet": dict_lang.get("Ascendant", "Ascendant"),
            "sign": asc_placement["sign"],
            "degree": asc_placement["degree"],
            "abs_deg": round(ascmc[0], 2)
        })

        # Генерація григоріанської карти на 13 місяців
        gregorian_map = generate_13month_gregorian_map(datetime.now().year)

        return {
            "status": "success",
            "timezone_used": tz_name,
            "placements": placements,
            "gregorian_calendar_map": gregorian_map
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def generate_svg_chart(planets_data: dict) -> str:
    width, height = 600, 600
    cx, cy, radius = 300, 300, 240
    inner_radius = 170
    r_text = 205

    # Графітовий колір для ліній та тексту під олівець
    PENCIL_COLOR = "#2b2b2b"

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">',
        # Прибрали <rect fill="#0b0f19"/> повністю для прозорого фону
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" stroke="{PENCIL_COLOR}" stroke-width="1.5" fill="none"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{inner_radius}" stroke="{PENCIL_COLOR}" stroke-width="1" fill="none"/>',
    ]

    constellations_iau = [
        {"code": c["code"][:3].upper(), "start": c["start"], "end": c["end"]}
        for c in iau_boundaries
    ]

    for c in constellations_iau:
        angle_rad = math.radians(c["start"] - 90)
        x1 = cx + inner_radius * math.cos(angle_rad)
        y1 = cy + inner_radius * math.sin(angle_rad)
        x2 = cx + radius * math.cos(angle_rad)
        y2 = cy + radius * math.sin(angle_rad)
        svg_lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{PENCIL_COLOR}" stroke-width="1"/>')

        span = (c["end"] - c["start"]) % 360
        mid_angle = (c["start"] + span / 2 - 90) % 360
        mid_rad = math.radians(mid_angle)
        tx = cx + r_text * math.cos(mid_rad)
        ty = cy + r_text * math.sin(mid_rad)
        svg_lines.append(f'<text x="{tx:.1f}" y="{ty:.1f}" fill="{PENCIL_COLOR}" font-size="11" font-family="Arial" font-weight="bold" text-anchor="middle" dominant-baseline="central">{c["code"]}</text>')

    planet_abbr = {
        "Sun": "Sun", "Moon": "Moo", "Ascendant": "Asc",
        "Mercury": "Mer", "Venus": "Ven", "Mars": "Mar",
        "Jupiter": "Jup", "Saturn": "Sat"
    }

    # Поліпшені кольори під олівцевий стиль
    colors = {
        "Sun": "#b45309",        # Темно-золотий / охра
        "Moon": "#3f3f46",       # Темно-сірий
        "Ascendant": "#b91c1c",  # Темно-червоний
        "Mercury": "#0f766e",   # Темна бірюза
        "Venus": "#a16207",     # Оливково-золотий
        "Mars": "#b91c1c",      # Темно-червоний
        "Jupiter": "#6b21a8",   # Темно-фіолетовий
        "Saturn": "#c2410c"     # Теракотовий
    }

    # === ЛІНІЇ АСПЕКТІВ (ТРИКУТНИКИ ТА ЗВ'ЯЗКИ) ===
    r_aspect = inner_radius - 10
    planet_coords = {}

    for p_name, p_deg in planets_data.items():
        if isinstance(p_deg, (int, float)):
            p_rad = math.radians(p_deg - 90)
            px = cx + r_aspect * math.cos(p_rad)
            py = cy + r_aspect * math.sin(p_rad)
            planet_coords[p_name] = (px, py, p_deg)

    p_keys = list(planet_coords.keys())
    aspects_list = [
        {"target": 120, "orb": 8, "color": "#b45309", "dash": ""},      # Темно-золотий (Тригон)
        {"target": 90,  "orb": 7, "color": "#b91c1c", "dash": ""},      # Червоний (Квадрат)
        {"target": 180, "orb": 8, "color": "#9f1239", "dash": "4,4"},  # Пунктир (Опозиція)
        {"target": 60,  "orb": 5, "color": "#0369a1", "dash": "2,2"},  # Синій (Секстиль)
    ]

    for i in range(len(p_keys)):
        for j in range(i + 1, len(p_keys)):
            p1, p2 = p_keys[i], p_keys[j]
            x1, y1, deg1 = planet_coords[p1]
            x2, y2, deg2 = planet_coords[p2]
            diff = abs(deg1 - deg2)
            if diff > 180:
                diff = 360 - diff

            for asp in aspects_list:
                if abs(diff - asp["target"]) <= asp["orb"]:
                    dash_attr = f'stroke-dasharray="{asp["dash"]}"' if asp["dash"] else ''
                    svg_lines.append(
                        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                        f'stroke="{asp["color"]}" stroke-width="1.2" opacity="0.75" {dash_attr}/>'
                    )
                    break

    for planet, deg in planets_data.items():
        if isinstance(deg, (int, float)):
            p_angle_rad = math.radians(deg - 90)
            px = cx + (inner_radius - 30) * math.cos(p_angle_rad)
            py = cy + (inner_radius - 30) * math.sin(p_angle_rad)
            color = colors.get(planet, "#1e3a8a")
            label = planet_abbr.get(planet, planet[:3])
            svg_lines.append(f'<circle cx="{px}" cy="{py}" r="4" fill="{color}"/>')
            svg_lines.append(f'<text x="{px}" y="{py - 10}" fill="{color}" font-size="10" font-family="Arial" font-weight="bold" text-anchor="middle">{label}</text>')

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

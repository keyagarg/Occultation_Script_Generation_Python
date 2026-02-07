import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import pandas as pd

MONTH_NUM = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
             "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
STAR_PREFIXES = {"UCAC4", "UCAC5", "TYC", "Gaia", "2MASS", "HIP", "GSC", "PPMXL"}
EVENT_ROW = re.compile(r"^\s*\d{4}\s+[A-Za-z]{3}\s+\d{1,2}\b")
PROB_TOK  = re.compile(r"^\d+%$")
INT_TOK   = re.compile(r"^-?\d+$")

def telescope_accept_mask(df: pd.DataFrame, telescope_key: str) -> pd.Series:
    mag = df["star_mag"].astype(float)

    if df["durn"].dtype == object:
        dur = df["durn"].astype(str).str.rstrip("s").astype(float)
    else:
        dur = df["durn"].astype(float)

    tel = telescope_key.lower().strip()

    if tel == "c11":
        rejected = ((mag >= 15.0) & (dur < 1.0)) | ((mag >= 14.5) & (dur < 0.3)) #ADD MAG CONDITIONS HERE
        return ~rejected
    elif tel == "c14":
        rejected = ((mag >= 15.5) & (dur < 1.0)) #ADD MAG CONDITIONS HERE
        return ~rejected
    elif tel == "hubble24":
        rejected = ((mag >= 16.0) & (dur < 1.0)) #ADD MAG CONDITIONS HERE
        return ~rejected
    else:
        raise ValueError(f"Unknown telescope: {telescope_key}")

def float_prefix(s: str) -> float:
    m = re.match(r"\s*([0-9]*\.?[0-9]+)", s)
    return float(m.group(1)) if m else float("nan")

# def filter_events_for_telescope(events, telescope_key: str, day_of_observation: int):
#     filtered = []
#     for ev in events:
#         if not night_window(ev, day_of_observation):
#             continue
#         if telescope_key == "c11":
#             # ADD MAG CONDITIONS HERE
#             if not ((ev.mag >= 15.0) and (ev.dur < 1.0)):
#                 if not ((ev.mag >= 14.5) and (ev.dur < 0.3)):
#                     filtered.append(ev)
#         elif telescope_key == "c14":
#             # ADD MAG CONDITIONS HERE
#             if not ((ev.mag >= 15.5) and (ev.dur < 1.0)):
#                 filtered.append(ev)
#         elif telescope_key == "hubble24":
#             # ADD MAG CONDITIONS HERE
#             if not ((ev.mag >= 15.5) and (ev.dur < 1.0)):
#                 filtered.append(ev)
#     return filtered

def exposure_for_mag(mag: float) -> float:
    inttime = 0.0067
    if mag > 9.0:  inttime = 0.015
    if mag > 9.5:  inttime = 0.020
    if mag > 10.0: inttime = 0.025
    if mag > 11.4: inttime = 0.030
    if mag > 11.9: inttime = 0.040
    if mag > 12.4: inttime = 0.050
    if mag > 12.9: inttime = 0.075
    if mag > 13.2: inttime = 0.100
    if mag > 13.5: inttime = 0.150
    if mag > 14.0: inttime = 0.200
    if mag > 14.2: inttime = 0.225
    if mag > 14.4: inttime = 0.275
    if mag > 14.6: inttime = 0.300
    if mag > 14.8: inttime = 0.325
    if mag > 15.0: inttime = 0.375
    if mag > 15.2: inttime = 0.425
    if mag > 15.4: inttime = 0.500
    return inttime

@dataclass
class Event:
    asteroid_id: str
    year: int
    month: str
    day: int
    date_str: str
    hour: int
    minute_float: float
    min_int: int
    sec: int
    time: str
    date_object: datetime
    dur: float
    dur_token: str
    mag: float
    mag_token: str
    mag_drop: float
    radec: str
    altaz: str
    target: str
    occulted_star: str
    prob: float
    maxint: float
    inttime: float
    nsamp: int
    sttime: str
    mttime: str
    lstime: str
    stime: float
    lshour: int
    lsmin: int

def parse_radec_from_end(tokens):
    t = tokens[:]
    if t and t[-1].isdigit():
        t = t[:-1]
    if len(t) >= 7 and t[-4] in ("-", "+"):
        ra_h, ra_m, ra_s = t[-7], t[-6], t[-5]
        dec_d = t[-4] + t[-3]      # "-3" or "+12"
        dec_m, dec_s = t[-2], t[-1]
        core = t[:-7]
    else:
        ra_h, ra_m, ra_s, dec_d, dec_m, dec_s = t[-6:]
        core = t[:-6]

    ra  = f"{ra_h} {ra_m} {ra_s}"
    dec = f"{dec_d} {dec_m} {dec_s}"
    return core, ra, dec

def find_altaz_index(tokens):
    for i in range(len(tokens) - 3, -1, -1):
        if INT_TOK.match(tokens[i]) and INT_TOK.match(tokens[i+1]):
            alt = int(tokens[i]); az = int(tokens[i+1])
            if -90 <= alt <= 90 and 0 <= az <= 360:
                try:
                    float(tokens[i+2])  # dist
                    return i
                except:
                    pass
    return None

def find_probability(tokens):
    for i in range(len(tokens) - 1, -1, -1):
        if PROB_TOK.match(tokens[i]):
            return float(tokens[i].rstrip("%"))
    return float("nan")

def find_star_anchor(tokens):
    for i, tok in enumerate(tokens):
        if tok in STAR_PREFIXES and i + 1 < len(tokens):
            return f"{tok} {tokens[i+1]}", i + 2

    for i, tok in enumerate(tokens):
        if tok.startswith("J") and ("+" in tok or "-" in tok):
            return tok, i + 1

    return "", None

def find_asteroid(tokens):
    alt_i = find_altaz_index(tokens)
    if alt_i is None:
        return ""

    star_no, j = find_star_anchor(tokens)
    if j is None:
        return ""
    while j < len(tokens) and len(tokens[j]) == 1 and tokens[j].isalpha():
        j += 1

    if j + 1 >= alt_i:
        return ""

    start = j + 1
    return " ".join(tokens[start:alt_i]).strip()

def parse_event_line(line: str):
    if not EVENT_ROW.match(line):
        return None

    tokens = line.split()
    core, ra, dec = parse_radec_from_end(tokens)
    year  = int(core[0]); month = core[1]; day = int(core[2])
    hour  = int(core[3]); minute_float = float(core[4])

    date = f"{year} {month} {day:02d}"
    ut = f"{hour} {minute_float:g}"

    durn_token = core[7]
    durn = float_prefix(durn_token)   # seconds
    star_mag = float(core[9])
    mag_drop = float_prefix(core[10]) #CHANGE HERE FOR CONFLICT OF ADDITIONAL COLUMNS FROM OCCULT 4

    star_no, _ = find_star_anchor(core)
    asteroid = find_asteroid(core)

    alt_i = find_altaz_index(core)
    alt = int(core[alt_i]) if alt_i is not None else None
    az  = int(core[alt_i + 1]) if alt_i is not None else None

    probability = find_probability(core)

    return {
        "date": date,
        "ut": ut,
        "durn": durn,
        "star_mag": star_mag,
        "mag_drop": mag_drop,
        "star_no": star_no,
        "asteroid": asteroid,
        "alt": alt,
        "az": az,
        "probability": probability,
        "ra": ra,
        "dec": dec,
    }

def events_to_dataframe(path: str) -> pd.DataFrame:
    rows = []
    bad = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln_no, line in enumerate(f, 1):
            line = line.strip("\n")
            if not line.strip():
                continue
            try:
                d = parse_event_line(line)
                if d:
                    rows.append(d)
            except Exception as e:
                if len(bad) < 10:
                    bad.append((ln_no, str(e), line))

    df = pd.DataFrame(rows)
    def row_to_dt(r):
        year, month, day = parse_date_str(r["date"])
        hour, minute_float = parse_ut_str(r["ut"])
        min_int = int(minute_float)
        sec = int((minute_float - min_int) * 60)
        return datetime(year, MONTH_NUM[month], day, hour, min_int, sec)

    df["utc_dt"] = df.apply(row_to_dt, axis=1)

    cols = ["utc_dt","date","ut","durn","star_mag","mag_drop","star_no",
            "asteroid","alt","az","probability","ra","dec"]
    return df[cols]

def parse_date_str(date_str: str):
    y_str, mon, d_str = date_str.split()
    return int(y_str), mon, int(d_str)

def parse_ut_str(ut_str: str):
    h_str, m_str = ut_str.split()
    return int(h_str), float(m_str)

def extract_event(row) -> Event | None:
    year, month, day = parse_date_str(row["date"])
    date_str = f"{year} {month} {day:02d}"
    hour, minute_float = parse_ut_str(row["ut"])
    min_int = int(minute_float)
    sec = int((minute_float - min_int) * 60)
    time = f"{hour:02d}:{min_int:02d}:{sec:02d}"
    durn_val = row["durn"]
    if isinstance(durn_val, str):
        dur_token = durn_val
        dur = float_prefix(durn_val)
    else:
        dur = float(durn_val)
        dur_token = f"{dur:g}s"

    mag = float(row["star_mag"])
    mag_token = f"{mag:g}"
    mag_drop = float(row["mag_drop"])
    radec = f'{row["ra"]} {row["dec"]}'
    alt = int(row["alt"]) if pd.notna(row["alt"]) else 0
    az  = int(row["az"])  if pd.notna(row["az"]) else 0
    altaz = f"{alt:>3} {az:>3}"
    target = str(row["asteroid"]) if pd.notna(row["asteroid"]) else ""
    asteroid_id = target.split()[0] if target else ""
    occulted_star = str(row["star_no"])
    prob = float(row["probability"])
    date_object = datetime(year, MONTH_NUM[month], day, hour, min_int, sec)

    maxint = dur / 4.0
    lsmin = min_int - 1
    stmin = min_int - 8
    mtmin = min_int - 2
    mthour = hour
    sthour = hour
    lshour = hour
    mtsec = sec + 30
    lssec = sec + 30
    if lssec >= 60:
        lssec -= 60
        lsmin += 1
    if lsmin < 0:
        lsmin += 60
        lshour -= 1
    if lshour < 0:
        lshour += 24
    lstime = f"{lshour:02d}:{lsmin:02d}:{lssec:02d}"
    if mtsec >= 60:
        mtsec -= 60
        mtmin += 1
    if mtmin < 0:
        mtmin += 60
        mthour -= 1
    if mthour < 0:
        mthour += 24
    mttime = f"{mthour:02d}:{mtmin:02d}:{mtsec:02d}"
    if stmin < 0:
        stmin += 60
        sthour -= 1
    if sthour < 0:
        sthour += 24
    stime = sthour + stmin / 60.0
    sttime = f"{sthour:02d}:{stmin:02d}:{sec:02d}"
    inttime = exposure_for_mag(mag)
    if inttime > maxint:
        inttime = maxint

    nsamp = int(60 / inttime) if inttime > 0 else 0

    return Event(
        asteroid_id=asteroid_id, year=year, month=month, day=day, date_str=date_str,
        hour=hour, minute_float=minute_float, min_int=min_int, sec=sec, time=time, date_object=date_object,
        dur=dur, mag=mag, dur_token=dur_token, mag_token=mag_token, mag_drop=mag_drop,
        radec=radec, altaz=altaz, target=target,
        occulted_star=occulted_star, prob=prob,
        maxint=maxint, inttime=inttime, nsamp=nsamp,
        sttime=sttime, mttime=mttime, lstime=lstime, stime=stime,
        lshour=lshour, lsmin=lsmin
    )

def night_window_filter(df: pd.DataFrame, day_filter: int) -> pd.Series:
    dt = df["utc_dt"]
    return ((dt.dt.day == day_filter) & (dt.dt.hour < 16)) | ((dt.dt.day == day_filter - 1) & (dt.dt.hour > 16))


def handle_num(x) -> str:
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        return format(x, ".6g")
    return str(x)

def handle_print(*args) -> str:
    return " ".join(a if isinstance(a, str) else handle_num(a) for a in args) + "\n"

def get_flagged_events(events_list):
    flagged = []
    current = [events_list[0]]
    for i in range(1, len(events_list)):
        time_difference = (events_list[i].date_object - events_list[i-1].date_object).total_seconds()
        if time_difference <= 240:
            current.append(events_list[i])
        else:
            if len(current) >= 2:
                flagged.append(current)
            current = [events_list[i]]
    if len(current) >= 2:
        flagged.append(current)
    return flagged

def infer_day_from_filename(path: str) -> int | None:
    m = re.search(r"(\d{4})(\d{2})(\d{2})", Path(path).name)
    return int(m.group(3)) if m else None

def get_astrometry_string(radec: str) -> str:
    parts = radec.split()
    ra_h, ra_m, ra_s, dec_d, dec_m, dec_s = parts[:6]
    sign = "-" if dec_d.startswith("-") else "+"
    dec_d_abs = dec_d.lstrip("+-")
    return f"#Astrometry coordinates: {ra_h}h{ra_m}m{ra_s}s {sign}{dec_d_abs}d{dec_m}m{dec_s}s\n"

def generate_scs(events, output_path: str, pre_path: str, post_path: str) -> None:
    with open(pre_path, "r", encoding="utf-8", errors="replace", newline="") as f:
        header = f.read()
    if not header.endswith("\n"):
        header += "\n"
    with open(post_path, "r", encoding="utf-8", errors="replace", newline="") as f:
        footer = f.read()

    events.sort(key=lambda e: e.date_object)

    out = header
    star = 1
    laststime = -10.0
    for ev in events:
        out += handle_print("#Start hours ", ev.stime, " previous: ", laststime)
        out += handle_print("# *************** Occultation", star, "************")
        out += handle_print("#")
        out += handle_print(
            "#UT= ", ev.time,
            "Dur", ev.dur_token,
            "Mv=", ev.mag_token,
            "AltAz=", ev.altaz,
            "LocalStart=", ev.lstime,
            "prob=", ev.prob,
            "Target=", ev.target,
            "RA/DEC", ev.radec,
            "star=", ev.occulted_star,
            "MagDrop=", ev.mag_drop
        )
        out += get_astrometry_string(ev.radec)
        out += handle_print("TARGETNAME \"", ev.target, "\"")
        out += handle_print("UNLOCK CONTROLS")
        out += handle_print("MOUNT TRACKING None")
        if ev.hour > 16:
            out += handle_print('WAIT UNTIL LATER THAN LOCALTIME "', ev.sttime, '"') #midnight change to be handled here
        else:
            out += handle_print('WAIT UNTIL LATER THAN LOCALTIME "', ev.sttime, '"')
        out += handle_print("IGNORE ERRORS FROM ONERROR RUN \"\"")
        out += handle_print("MOUNT TRACKING Sidereal")
        out += handle_print("  MOUNT GOTO \"", ev.radec, "\"")
        out += handle_print("END IGNORE ERRORS")
        out += handle_print("DELAY 2")
        out += handle_print("#")
        if (ev.stime - laststime) * 60 > 20:
            out += handle_print("GOSUB AFOCUS")
        out += handle_print("GOSUB PLATESOLV")
        out += handle_print("WAIT UNTIL LATER THAN LOCALTIME \"", ev.mttime, "\"")
        out += handle_print("GOSUB PLATESOLV")
        out += handle_print("SET RESOLUTION TO 800x600")
        out += handle_print("SET EXPOSURE TO", ev.inttime)
        out += handle_print("DELAY 3")
        out += handle_print("DISPLAY STRETCH AUTO")
        out += handle_print("WAIT UNTIL LATER THAN LOCALTIME \"", ev.lstime, "\"")
        out += handle_print("  CAPTURE 60 SECONDS LIVE FRAMES")
        out += handle_print("SET RESOLUTION TO 1920x1200")
        out += handle_print("SET EXPOSURE TO 0.5")
        out += handle_print("DELAY 3")
        out += handle_print("DISPLAY STRETCH AUTO")
        out += handle_print("END UNLOCK")

        star += 1
        laststime = ev.lshour + (ev.lsmin + 5) / 60.0
    out += footer

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        f.write(out)

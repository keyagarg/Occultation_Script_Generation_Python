# %%
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import argparse

MONTH_NUM = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
             "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}

def float_prefix(s: str) -> float:
    m = re.match(r"\s*([0-9]*\.?[0-9]+)", s)
    return float(m.group(1)) if m else 0.0

def substr(line: str, start_1based: int, length: int) -> str:
    line = line.rstrip("\n")
    need = (start_1based - 1) + length
    if len(line) < need:
        line = line + " " * (need - len(line))
    i = start_1based - 1
    return line[i:i+length]


def c11(raw_lines, day_of_observation):
    events = []
    for line in raw_lines:
        ev = extract_event(line)
        if ev and night_window(ev, day_of_observation):
            # ADD MAG/DURATION CONDITIONS HERE #
            if not ((ev.mag >= 15.0) and (ev.dur < 1.0)):
                if not((ev.mag >= 14.5) and (ev.dur < 0.3)):
                    events.append(ev)
    return events

def hubble24(raw_lines, day_of_observation):
    events = []
    for line in raw_lines:
        ev = extract_event(line)
        if ev and night_window(ev, day_of_observation):
            # ADD MAG/DURATION CONDITIONS HERE #
            if not ((ev.mag >= 15.0) and (ev.dur < 1.0)):
                if not((ev.mag >= 14.5) and (ev.dur < 0.3)):
                    events.append(ev)
    return events

def c14(raw_lines, day_of_observation):
    events = []
    for line in raw_lines:
        ev = extract_event(line)
        if ev and night_window(ev, day_of_observation):
            # ADD MAG/DURATION CONDITIONS HERE #
            if not ((ev.mag >= 15.0) and (ev.dur < 1.0)):
                if not((ev.mag >= 14.5) and (ev.dur < 0.3)):
                    events.append(ev)
    return events

TELESCOPE_SELECTORS = {
    "c11": c11,
    "c14": c14,
    "hubble24": hubble24
}

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

def extract_radec_from_end(line: str) -> str:
    t = line.split()
    if t and re.fullmatch(r"\d+", t[-1]):
        t = t[:-1]
    ra_h, ra_m, ra_s, dec_d, dec_m, dec_s = t[-6:]
    return f"{ra_h} {ra_m} {ra_s} {dec_d} {dec_m} {dec_s}"

EVENT_ROW = re.compile(r"^\s*\d{4}\s+[A-Za-z]{3}\s+\d{1,2}\b")
def extract_event(line: str) -> Event | None:
    if not EVENT_ROW.match(line):
        return None
    p = line.split()

    year = int(p[0])
    month = p[1]
    day = int(p[2])
    date_str = f"{year} {month} {day:02d}"
    hour = int(p[3])
    minute_float = float(p[4])
    min_int = int(minute_float)
    sec = int((minute_float - min_int) * 60)
    time = f"{hour:02d}:{min_int:02d}:{sec:02d}"
    dur_token = p[7]
    dur = float_prefix(dur_token)
    mag_token = p[8]
    mag = float(mag_token)
    radec = extract_radec_from_end(line)
    altaz = substr(line, 122, 6)
    target = substr(line, 97, 24)
    occulted_star = substr(line, 64, 19)
    prob_str = substr(line, 146, 4)
    asteroid_id = target.split()[0]
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

    radec = radec.replace("- ", "-0")
    target = target.replace("  ", "")
    prob = float_prefix(prob_str)

    return Event(
        asteroid_id=asteroid_id, year=year, month=month, day=day, date_str=date_str,
        hour=hour, minute_float=minute_float, min_int=min_int, sec=sec, time=time, date_object=date_object,
        dur=dur, mag=mag, dur_token=dur_token, mag_token=mag_token,
        radec=radec, altaz=altaz, target=target,
        occulted_star=occulted_star, prob=prob,
        maxint=maxint, inttime=inttime, nsamp=nsamp,
        sttime=sttime, mttime=mttime, lstime=lstime, stime=stime,
        lshour=lshour, lsmin=lsmin
    )

def night_window(ev: Event, day_filter: int) -> bool:
    return ((ev.day == day_filter and ev.hour < 16) or (ev.day == day_filter - 1 and ev.hour > 16))

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

def generate_scs(events_txt_path: str, day_of_observation: int, output_path: str, pre_path: str, post_path: str, telescope: str) -> None:
    with open(pre_path, "r", encoding="utf-8", errors="replace", newline="") as f:
        header = f.read()
    if not header.endswith("\n"):
        header += "\n"
    with open(post_path, "r", encoding="utf-8", errors="replace", newline="") as f:
        footer = f.read()

    with open(events_txt_path, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = [ln.rstrip("\n") for ln in f]
    raw_lines = list(filter(None, raw_lines))

    telescope_key = telescope.strip().lower()
    events = TELESCOPE_SELECTORS[telescope_key](raw_lines, day_of_observation)
    events.sort(key=lambda e: e.date_object)

    flagged_events = get_flagged_events(events)
    print('\033[1m' + 'POTENTIAL CONFLICTS' + '\033[0m')
    for i in flagged_events:
        for j in i:
            print("Asteroid:", j.target,"  Event time:", j.time, "  Mag:", j.mag_token, "  Dur:", j.dur_token, "  Prob:", j.prob, " AltAz:", j.altaz)
        print()

    events_to_remove = input("Enter the asteriod number of the events to remove, separated by a comma. If none to remove, enter 0: ").strip()

    remove_ids = set()
    if events_to_remove != "0" and events_to_remove != "":
        parts = [p.strip() for p in events_to_remove.replace(" ", ",").split(",") if p.strip()]
        remove_ids = set(parts)
    if remove_ids:
        prev_len = len(events)
        events = [ev for ev in events if ev.asteroid_id not in remove_ids]
        new_len = len(events)
        print(f"Removed {prev_len - new_len} events.")
    else:
        print("No events removed.")


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
            "star=", ev.occulted_star
        )
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

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print("Script Generated!")

def main() -> None:
    ap = argparse.ArgumentParser(description="Generate .scs script from event summary.")
    ap.add_argument("events_txt", help="Input events text file, YYYYMMDD_events.txt")
    ap.add_argument("telescope", choices=["c11", "c14", "hubble24"], help="Input telescope type")
    ap.add_argument("--day", type=int, default=None, help="Day-of-month (e.g. 17). If omitted, inferred from filename.")
    ap.add_argument("--pre", default="pre174.txt", help="Header file (pre174)")
    ap.add_argument("--post", default="post571.txt", help="Footer file (post571)")
    ap.add_argument("-o", "--out", default=None, help="Output .scs path (default: YYYYMMDD_174_script.scs)")

    args = ap.parse_args()

    day_of_observation = args.day if args.day is not None else infer_day_from_filename(args.events_txt)

    if args.out is None:
        stem = Path(args.events_txt).name[:8]
        out_path = f"{stem}_174_script.scs"
    else:
        out_path = args.out

    generate_scs(args.events_txt, day_of_observation, out_path, args.pre, args.post, args.telescope)

if __name__ == "__main__":
    main()

# %%




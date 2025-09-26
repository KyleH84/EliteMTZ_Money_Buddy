from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import re, time

def _try_requests_get(url: str, retries: int = 2, timeout: int = 6) -> Optional[str]:
    try:
        import requests
    except Exception:
        return None
    for attempt in range(retries+1):
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
            if r.ok and r.text:
                return r.text
        except Exception:
            if attempt < retries:
                time.sleep(0.5 * (attempt+1))
                continue
            return None
    return None

@dataclass
class DrawStatus:
    game: str
    last_draw_date: Optional[str]
    last_white: Optional[List[int]]
    last_special: Optional[int]
    extra: Dict[str, Any]

def _parse_powerball_com(html: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not html:
        return out
    m = re.search(r'Jackpot[^$]*\$\s*([0-9.,]+)\s*(Million|Billion)', html, re.I)
    if m:
        out["jackpot"] = f"${m.group(1)} {m.group(2)}"
    return out

def _parse_powerball_net(html: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not html:
        return out
    m = re.search(r'(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2}).*?Powerball[:\s]+(\d{1,2}).*?(Power\s*Play[:\s]+(\d)x)?', html, re.I|re.S)
    if m:
        nums = [int(m.group(i)) for i in range(1,6)]
        out["white"] = nums
        out["special"] = int(m.group(6))
        if m.group(8):
            out["powerplay"] = m.group(8) + "x"
    md = re.search(r'(Monday|Wednesday|Saturday),\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}', html, re.I)
    if md:
        out["date"] = md.group(0)
    return out

def _parse_megamillions_com(html: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not html:
        return out
    m = re.search(r'(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2}).*?Mega\s*Ball[:\s]+(\d{1,2}).*?(Megaplier[:\s]+(\d)x)?', html, re.I|re.S)
    if m:
        nums = [int(m.group(i)) for i in range(1,6)]
        out["white"] = nums
        out["special"] = int(m.group(6))
        if m.group(8):
            out["megaplier"] = m.group(8) + "x"
    md = re.search(r'(Tuesday|Friday),\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}', html, re.I)
    if md:
        out["date"] = md.group(0)
    j = re.search(r'Jackpot[^$]*\$\s*([0-9.,]+)\s*(Million|Billion)', html, re.I)
    if j:
        out["jackpot"] = f"${j.group(1)} {j.group(2)}"
    return out

def fetch_powerball_status() -> DrawStatus:
    official = _try_requests_get("https://www.powerball.com/")
    net = _try_requests_get("https://www.powerball.net/")
    extras = {}
    if official:
        extras.update(_parse_powerball_com(official))
    parsed = _parse_powerball_net(net or "") if net else {}
    return DrawStatus("powerball", parsed.get("date"), parsed.get("white"), parsed.get("special"),
                      {k:v for k,v in extras.items() if v} | {k:v for k,v in parsed.items() if k not in ("date","white","special") and v})

def fetch_megamillions_status() -> DrawStatus:
    html = _try_requests_get("https://www.megamillions.com/")
    parsed = _parse_megamillions_com(html or "")
    return DrawStatus("megamillions", parsed.get("date"), parsed.get("white"), parsed.get("special"),
                      {k:v for k,v in parsed.items() if k not in ("date","white","special") and v})

def format_status_markdown(s: DrawStatus) -> str:
    title = "Powerball" if s.game=="powerball" else ("Mega Millions" if s.game=="megamillions" else s.game.title())
    lines = [f"### Current {title} Status"]
    if s.last_draw_date or s.last_white or s.last_special is not None:
        lines.append("**Last drawing**" + (f" — {s.last_draw_date}" if s.last_draw_date else "") + ":")
        wb = ", ".join(str(x) for x in (s.last_white or [])) or "n/a"
        spec_label = "Powerball" if s.game=="powerball" else ("Mega Ball" if s.game=="megamillions" else "Special")
        lines.append(f"- White balls: {wb}")
        lines.append(f"- {spec_label}: {s.last_special if s.last_special is not None else 'n/a'}")
    if s.extra.get("jackpot"):
        lines.append(f"**Next jackpot:** {s.extra['jackpot']} (estimate)")
    if s.extra.get("powerplay"):
        lines.append(f"- Power Play: {s.extra['powerplay']}")
    if s.extra.get("megaplier"):
        lines.append(f"- Megaplier: {s.extra['megaplier']}")
    return "\n".join(lines)

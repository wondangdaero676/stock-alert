import os
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    change_pct: float
    session_date: str  # 거래소 현지 기준 거래일. 같은 거래일에 중복 알림을 막는 데 사용


def fetch(market: str, symbol: str) -> Quote:
    if market == "US":
        return _finnhub(symbol)
    return _naver(symbol)


def _finnhub(symbol: str) -> Quote:
    resp = requests.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": symbol},
        headers={"X-Finnhub-Token": os.environ["FINNHUB_API_KEY"]},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("t") or not data.get("pc"):
        raise ValueError(f"Finnhub에서 {symbol} 시세를 찾을 수 없습니다: {data}")

    return Quote(
        symbol=symbol,
        price=float(data["c"]),
        change_pct=(data["c"] - data["pc"]) / data["pc"] * 100,
        session_date=datetime.fromtimestamp(data["t"], ZoneInfo("America/New_York")).date().isoformat(),
    )


def _naver(code: str) -> Quote:
    resp = requests.get(
        f"https://m.stock.naver.com/api/stock/{code}/basic",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    return Quote(
        symbol=data.get("stockName", code),
        price=float(data["closePrice"].replace(",", "")),
        change_pct=float(data["fluctuationsRatio"]),
        session_date=data["localTradedAt"][:10],
    )

from dataclasses import dataclass

import yaml

from alert.quotes import Quote

CONDITIONS = {
    "change_pct_below": lambda q, t: q.change_pct <= t,
    "change_pct_above": lambda q, t: q.change_pct >= t,
    "price_below": lambda q, t: q.price <= t,
    "price_above": lambda q, t: q.price >= t,
}


@dataclass(frozen=True)
class Rule:
    name: str
    market: str
    symbol: str
    condition: str
    threshold: float

    @property
    def key(self) -> str:
        return f"{self.market}:{self.symbol}:{self.condition}:{self.threshold:g}"

    def matches(self, quote: Quote) -> bool:
        return CONDITIONS[self.condition](quote, self.threshold)


def load(path: str) -> list[Rule]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rules = []
    for item in data["rules"]:
        market = item["market"].upper()
        symbol = str(item["symbol"]).upper()
        if market == "KR":
            symbol = symbol.zfill(6)
        rule = Rule(
            name=item["name"],
            market=market,
            symbol=symbol,
            condition=item["condition"],
            threshold=float(item["threshold"]),
        )
        if rule.market not in ("US", "KR"):
            raise ValueError(f"[{rule.name}] market은 US 또는 KR이어야 합니다: {rule.market}")
        if rule.condition not in CONDITIONS:
            raise ValueError(f"[{rule.name}] 알 수 없는 condition: {rule.condition}")
        rules.append(rule)
    return rules

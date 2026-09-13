import argparse
import logging
import sys

from alert import kakao, quotes, rules, state
from alert.quotes import Quote
from alert.rules import Rule

log = logging.getLogger("stock-alert")

CONDITION_LABELS = {
    "change_pct_below": "전일 대비 {t:g}% 이하",
    "change_pct_above": "전일 대비 {t:g}% 이상",
    "price_below": "가격 {t:g} 이하",
    "price_above": "가격 {t:g} 이상",
}


def format_message(rule: Rule, q: Quote) -> str:
    return (
        f"[주식 알림] {rule.name}\n"
        f"{q.symbol} {q.currency}{q.price:,.2f} ({q.change_pct:+.2f}%)\n"
        f"조건: {CONDITION_LABELS[rule.condition].format(t=rule.threshold)}\n"
        f"거래일: {q.session_date}"
    )


def check(dry_run: bool) -> int:
    rule_list = rules.load("rules.yaml")
    sent = state.load_sent()
    cache: dict[tuple[str, str], Quote] = {}
    triggered: list[tuple[Rule, Quote]] = []
    failed = False

    for rule in rule_list:
        target = (rule.market, rule.symbol)
        try:
            if target not in cache:
                cache[target] = quotes.fetch(*target)
        except Exception:
            log.exception("시세 조회 실패: %s", rule.name)
            failed = True
            continue

        q = cache[target]
        log.info("%s %s: %.2f (%+.2f%%) 거래일 %s", rule.market, q.symbol, q.price, q.change_pct, q.session_date)
        if not rule.matches(q):
            continue
        if sent.get(rule.key) == q.session_date:
            log.info("이미 이번 거래일에 알림을 보냄: %s", rule.name)
            continue
        triggered.append((rule, q))

    if triggered and dry_run:
        for rule, q in triggered:
            print("----- 보낼 메시지 (dry-run) -----\n" + format_message(rule, q))
    elif triggered:
        token = kakao.access_token()
        for rule, q in triggered:
            kakao.send(token, format_message(rule, q), q.url)
            sent[rule.key] = q.session_date
            state.save_sent(sent)
            log.info("알림 전송: %s", rule.name)

    return 1 if failed else 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="주식 알림")
    sub = parser.add_subparsers(dest="command", required=True)
    check_cmd = sub.add_parser("check", help="규칙을 확인하고 조건에 맞으면 카카오톡 알림")
    check_cmd.add_argument("--dry-run", action="store_true", help="카카오톡 대신 화면에 출력")
    sub.add_parser("refresh", help="카카오 토큰 갱신 (리프레시 토큰 만료 방지)")
    sub.add_parser("test", help="카카오톡 테스트 메시지 전송")
    args = parser.parse_args()

    if args.command == "check":
        return check(args.dry_run)
    if args.command == "refresh":
        kakao.access_token()
        log.info("카카오 토큰 갱신 완료")
        return 0
    kakao.send(kakao.access_token(), "[주식 알림] 테스트 메시지입니다. 연결이 정상입니다.", "https://finance.yahoo.com")
    log.info("테스트 메시지 전송 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())

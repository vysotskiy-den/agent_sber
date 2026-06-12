"""CLI-прогон симуляции с сохранением результата в JSON-артефакт.

Используется для воспроизводимого демо защиты: запускает 10 дней, собирает лог
рассуждений и все 6 метрик (включая Coherence и Tool Accuracy, которым нужен лог
прогона) и пишет в `data/run_result.json`.

Запуск:
    uv run python -m scripts.run_simulation --balance 10000 --risk aggressive
"""
from __future__ import annotations

import argparse
import json

from agents import portfolio_graph as pg
from core import config, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Прогон торговой МАС с сохранением результата")
    parser.add_argument("--balance", type=float, default=config.DEFAULT_INITIAL_BALANCE)
    parser.add_argument("--risk", choices=config.RISK_PROFILES, default=config.DEFAULT_RISK_PROFILE)
    args = parser.parse_args()

    days_log: list[dict] = []
    for rec in pg.run_simulation(initial_balance=args.balance, risk_profile=args.risk):
        days_log.append(rec)
        s = rec["state"]
        pos = f"{s.position.ticker}×{s.position.qty}@${s.position.buy_price:.2f}" if s.position else "нет"
        print(f"День {rec['day']:2d} | кэш ${s.cash:8.2f} | позиция {pos}")

    # JSON-представление лога (PortfolioState не сериализуется напрямую).
    serializable = []
    for rec in days_log:
        s = rec["state"]
        price = pg._safe_price(s)
        serializable.append({
            "day": rec["day"],
            "log": rec["log"],
            "cash": round(s.cash, 2),
            "position": (
                {"ticker": s.position.ticker, "qty": s.position.qty,
                 "buy_price": s.position.buy_price} if s.position else None
            ),
            "total": round(s.total_value(price), 2),
        })

    result = {
        "params": {"balance": args.balance, "risk": args.risk, "tickers": config.TICKERS},
        "metrics": metrics.summary(days_log),
        "days": serializable,
    }
    out = config.DATA_DIR / "run_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nМетрики: {result['metrics']}")
    print(f"Артефакт сохранён: {out}")


if __name__ == "__main__":
    main()

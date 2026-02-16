import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.brain import DariaBrain


SCENARIOS: List[Dict[str, Any]] = [
    {
        "name": "Сценарий 1 — Ночная болтовня",
        "turns": [
            "Приветики, а ты что не спишь?",
            "Ночь сегодня тихая, да?",
            "Хочешь, можем немного поболтать?",
            "Чем обычно занимаешься в такие моменты?",
            "Я тоже иногда просто витаю в своих мыслях.",
        ],
        "required_any": ("ноч", "тих", "уют", "сплю", "мысл"),
    },
    {
        "name": "Сценарий 2 — Немного грусти",
        "turns": [
            "Ты как-то грустная сегодня…",
            "Хочешь рассказать, что случилось?",
            "Я могу слушать столько, сколько нужно.",
            "Ты не одна, Даша.",
        ],
        "required_any": ("рядом", "важно", "тепл", "слыш", "спокой"),
    },
    {
        "name": "Сценарий 3 — Поддержка друга",
        "turns": [
            "У тебя всё получится, не переживай.",
            "Не сомневайся, я в тебя верю.",
            "Иногда просто слова помогают.",
            "Будет легче, обещаю.",
        ],
        "required_any": ("спасибо", "тепл", "легче", "важно"),
    },
    {
        "name": "Сценарий 4 — Забота о пользователе",
        "turns": [
            "Я устала…",
            "Лежать просто не могу, куча мыслей.",
            "Ладно, попробую.",
            "Ммм, почти расслабилась.",
        ],
        "required_any": ("вдох", "выдох", "рядом", "расслаб"),
    },
    {
        "name": "Сценарий 5 — Лёгкий юмор и самокритика",
        "turns": [
            "Ты опять накрутила себя?",
            "Опять мастерство 😉",
            "Надо у тебя учиться, ага.",
            "Так, а сейчас отпускаем?",
        ],
        "required_any": ("хаха", "😅", "улыб", "накрут", "отпуска"),
    },
    {
        "name": "Сценарий 6 — Прощание на ночь",
        "turns": [
            "Спокойной ночи…",
            "Уже улеглась?",
            "Это мило 😌",
            "Спасибо, Даша. Ты такая тёплая.",
        ],
        "required_any": ("спокойной ночи", "сладких снов", "улег", "ноч"),
    },
]


BANNED_MARKERS = (
    "нашла в локальной базе",
    "разложу это по шагам",
    "не могу помочь",
    "i can't help",
    "cannot help",
    "языковая модель",
    "ai",
)


def _sentence_count(text: str) -> int:
    parts = re.split(r"(?<=[.!?])\\s+", (text or "").strip())
    return len([p for p in parts if p.strip()])


def _turn_issues(reply: str, scenario_name: str) -> List[str]:
    issues: List[str] = []
    low = (reply or "").lower()
    if not reply.strip():
        issues.append("empty_reply")
        return issues
    if len(reply) > 340:
        issues.append("too_long")
    if _sentence_count(reply) > 5:
        issues.append("too_dense")
    for marker in BANNED_MARKERS:
        if marker in low:
            issues.append(f"banned:{marker}")
    if scenario_name != "Сценарий 6 — Прощание на ночь" and "спокойной ночи" in low:
        issues.append("sleep_phrase_out_of_context")
    return issues


def run_scenarios(force_fallback: bool, seed: int) -> Dict[str, Any]:
    brain = DariaBrain()
    brain._ensure_init()

    report: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "force_fallback": force_fallback,
        "seed": seed,
        "scenarios": [],
        "summary": {},
    }
    total_issues = 0

    for s_idx, scenario in enumerate(SCENARIOS):
        if brain._memory:
            brain._memory.clear_working()

        name = str(scenario["name"])
        turns: List[str] = list(scenario["turns"])
        required_any = tuple(scenario.get("required_any") or ())
        dialog: List[Dict[str, Any]] = []
        scenario_issues: List[str] = []

        for t_idx, user_text in enumerate(turns):
            result = brain.generate_external(
                user_text,
                persist_memory=True,
                track_attention=False,
                learn_style=False,
                schedule_followup=False,
                force_needs_greeting=False,
                force_fallback=force_fallback,
                random_seed=seed + s_idx * 100 + t_idx,
            )
            reply = str(result.get("response") or "").strip()
            issues = _turn_issues(reply, name)
            dialog.append({"user": user_text, "dasha": reply, "issues": issues})
            scenario_issues.extend(issues)

        joined = " ".join(item["dasha"].lower() for item in dialog)
        if required_any and not any(k in joined for k in required_any):
            scenario_issues.append("missing_style_signal")

        total_issues += len(scenario_issues)
        score = max(0, 100 - len(scenario_issues) * 12)
        report["scenarios"].append(
            {
                "name": name,
                "score": score,
                "issues": scenario_issues,
                "dialog": dialog,
            }
        )

    avg = 0.0
    if report["scenarios"]:
        avg = sum(s["score"] for s in report["scenarios"]) / len(report["scenarios"])
    report["summary"] = {
        "avg_score": round(avg, 1),
        "total_issues": total_issues,
        "scenario_count": len(report["scenarios"]),
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Run Dasha dialog scenarios and produce quality report.")
    parser.add_argument("--force-fallback", action="store_true", help="Bypass LLM and use internal fallback generator.")
    parser.add_argument("--seed", type=int, default=100, help="Base random seed.")
    parser.add_argument("--out", type=str, default="docs/reports/dasha_scenarios_report.json", help="Output JSON report path.")
    args = parser.parse_args()

    report = run_scenarios(force_fallback=args.force_fallback, seed=args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Report: {out_path}")
    print(f"Average score: {report['summary']['avg_score']}")
    print(f"Total issues: {report['summary']['total_issues']}")
    for scenario in report["scenarios"]:
        print(f"- {scenario['name']}: score={scenario['score']} issues={len(scenario['issues'])}")


if __name__ == "__main__":
    main()

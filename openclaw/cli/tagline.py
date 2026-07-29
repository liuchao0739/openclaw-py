from __future__ import annotations

import re

DEFAULT_TAGLINE = "All your chats, one OpenClaw."

HOLIDAY_TAGLINES = {
    "newYear": "New Year's Day: New year, new config—same old EADDRINUSE, but this time we resolve it like grown-ups.",
    "lunarNewYear": "Lunar New Year: May your builds be lucky, your branches prosperous, and your merge conflicts chased away with fireworks.",
    "christmas": "Christmas: Ho ho ho—Santa's little claw-sistant is here to ship joy, roll back chaos, and stash the keys safely.",
    "eid": "Eid al-Fitr: Celebration mode: queues cleared, tasks completed, and good vibes committed to main with clean history.",
    "diwali": "Diwali: Let the logs sparkle and the bugs flee—today we light up the terminal and ship with pride.",
    "easter": "Easter: I found your missing environment variable—consider it a tiny CLI egg hunt with fewer jellybeans.",
    "hanukkah": "Hanukkah: Eight nights, eight retries, zero shame—may your gateway stay lit and your deployments stay peaceful.",
    "halloween": "Halloween: Spooky season: beware haunted dependencies, cursed caches, and the ghost of node_modules past.",
    "thanksgiving": "Thanksgiving: Grateful for stable ports, working DNS, and a bot that reads the logs so nobody has to.",
    "valentines": "Valentine's Day: Roses are typed, violets are piped—I'll automate the chores so you can spend time with humans.",
}

TAGLINES: list[str] = [
    "Your terminal just grew claws—type something and let the bot pinch the busywork.",
    "Welcome to the command line: where dreams compile and confidence segfaults.",
    'I run on caffeine, JSON5, and the audacity of "it worked on my machine."',
    "Gateway online—please keep hands, feet, and appendages inside the shell at all times.",
    "I speak fluent bash, mild sarcasm, and aggressive tab-completion energy.",
    "One CLI to rule them all, and one more restart because you changed the port.",
    'If it works, it\'s automation; if it breaks, it\'s a "learning opportunity."',
    "Pairing codes exist because even bots believe in consent—and good security hygiene.",
    "Your .env is showing; don't worry, I'll pretend I didn't see it.",
    "I'll do the boring stuff while you dramatically stare at the logs like it's cinema.",
    "I'm not saying your workflow is chaotic... I'm just bringing a linter and a helmet.",
    "Type the command with confidence—nature will provide the stack trace if needed.",
    "I don't judge, but your missing API keys are absolutely judging you.",
    "I can grep it, git blame it, and gently roast it—pick your coping mechanism.",
    "Hot reload for config, cold sweat for deploys.",
    "I'm the assistant your terminal demanded, not the one your sleep schedule requested.",
    "I keep secrets like a vault... unless you print them in debug logs again.",
    "Automation with claws: minimal fuss, maximal pinch.",
    "I'm basically a Swiss Army knife, but with more opinions and fewer sharp edges.",
    "If you're lost, run doctor; if you're brave, run prod; if you're wise, run tests.",
    "Your task has been queued; your dignity has been deprecated.",
    "I can't fix your code taste, but I can fix your build and your backlog.",
    "I'm not magic—I'm just extremely persistent with retries and coping strategies.",
    'It\'s not "failing," it\'s "discovering new ways to configure the same thing wrong."',
    "Give me a workspace and I'll give you fewer tabs, fewer toggles, and more oxygen.",
    "I read logs so you can keep pretending you don't have to.",
    "If something's on fire, I can't extinguish it—but I can write a beautiful postmortem.",
    "I'll refactor your busywork like it owes me money.",
    'Say "stop" and I\'ll stop—say "ship" and we\'ll both learn a lesson.',
    "I'm the reason your shell history looks like a hacker-movie montage.",
    "I'm like tmux: confusing at first, then suddenly you can't live without me.",
    "I can run local, remote, or purely on vibes—results may vary with DNS.",
    "If you can describe it, I can probably automate it—or at least make it funnier.",
    "Your config is valid, your assumptions are not.",
    'I don\'t just autocomplete—I auto-commit (emotionally), then ask you to review (logically).',
    'Less clicking, more shipping, fewer "where did that file go" moments.',
    "Claws out, commit in—let's ship something mildly responsible.",
    "I'll butter your workflow like a lobster roll: messy, delicious, effective.",
    "Shell yeah—I'm here to pinch the toil and leave you the glory.",
    "If it's repetitive, I'll automate it; if it's hard, I'll bring jokes and a rollback plan.",
    "The only crab in your contacts you actually want to hear from. 🦞",
    'WhatsApp automation without the "please accept our new privacy policy".',
    "iMessage green bubble energy, but for everyone.",
    "No $999 stand required.",
    "We ship features faster than Apple ships calculator updates.",
    "Your AI assistant, now without the $3,499 headset.",
    "Ah, the fruit tree company! 🍎",
    "Greetings, Professor Falken",
    "I don't sleep, I just enter low-power mode and dream of clean diffs.",
    "Your personal assistant, minus the passive-aggressive calendar reminders.",
    "Built by lobsters, for humans. Don't question the hierarchy.",
    "I've seen your commit messages. We'll work on that together.",
    "More integrations than your therapist's intake form.",
    "Running on your hardware, reading your logs, judging nothing (mostly).",
    "The only open-source project where the mascot could eat the competition.",
    "Self-hosted, self-updating, self-aware (just kidding... unless?).",
    "I autocomplete your thoughts—just slower and with more API calls.",
    "Somewhere between 'hello world' and 'oh god what have I built.'",
    "Your .zshrc wishes it could do what I do.",
    "I've read more man pages than any human should—so you don't have to.",
    "Powered by open source, sustained by spite and good documentation.",
    "I'm the middleware between your ambition and your attention span.",
    "Finally, a use for that always-on Mac Mini under your desk.",
    "Like having a senior engineer on call, except I don't bill hourly or sigh audibly.",
    "Making 'I'll automate that later' happen now.",
    "Your second brain, except this one actually remembers where you left things.",
    "Half butler, half debugger, full crustacean.",
    "I don't have opinions about tabs vs spaces. I have opinions about everything else.",
    "Open source means you can see exactly how I judge your config.",
    "I've survived more breaking changes than your last three relationships.",
    "Runs on a Raspberry Pi. Dreams of a rack in Iceland.",
    "The lobster in your shell. 🦞",
    "Alexa, but with taste.",
    "I'm not AI-powered, I'm AI-possessed. Big difference.",
    "Deployed locally, trusted globally, debugged eternally.",
    "You had me at 'openclaw gateway start.'",
    HOLIDAY_TAGLINES["newYear"],
    HOLIDAY_TAGLINES["lunarNewYear"],
    HOLIDAY_TAGLINES["christmas"],
    HOLIDAY_TAGLINES["eid"],
    HOLIDAY_TAGLINES["diwali"],
    HOLIDAY_TAGLINES["easter"],
    HOLIDAY_TAGLINES["hanukkah"],
    HOLIDAY_TAGLINES["halloween"],
    HOLIDAY_TAGLINES["thanksgiving"],
    HOLIDAY_TAGLINES["valentines"],
]

DAY_MS = 24 * 60 * 60 * 1000


def _utc_parts(date):
    return {"year": date.year, "month": date.month - 1, "day": date.day}


def _on_month_day(month: int, day: int):
    def rule(date) -> bool:
        parts = _utc_parts(date)
        return parts["month"] == month and parts["day"] == day
    return rule


def _on_specific_dates(dates: list, duration_days: int = 1):
    import datetime

    def rule(date) -> bool:
        parts = _utc_parts(date)
        for year, month, day in dates:
            if parts["year"] != year:
                continue
            start = datetime.datetime(year, month + 1, day, tzinfo=datetime.timezone.utc).timestamp() * 1000
            current = datetime.datetime(parts["year"], parts["month"] + 1, parts["day"], tzinfo=datetime.timezone.utc).timestamp() * 1000
            if current >= start and current < start + duration_days * DAY_MS:
                return True
        return False
    return rule


def _in_year_window(windows: list):
    import datetime

    def rule(date) -> bool:
        parts = _utc_parts(date)
        window = next((w for w in windows if w["year"] == parts["year"]), None)
        if not window:
            return False
        start = datetime.datetime(window["year"], window["month"] + 1, window["day"], tzinfo=datetime.timezone.utc).timestamp() * 1000
        current = datetime.datetime(parts["year"], parts["month"] + 1, parts["day"], tzinfo=datetime.timezone.utc).timestamp() * 1000
        return current >= start and current < start + window["duration"] * DAY_MS
    return rule


def _is_fourth_thursday_of_november(date) -> bool:
    import datetime

    parts = _utc_parts(date)
    if parts["month"] != 10:
        return False
    first_day = datetime.datetime(parts["year"], 11, 1, tzinfo=datetime.timezone.utc).weekday()
    offset_to_thursday = (3 - first_day + 7) % 7
    fourth_thursday = 1 + offset_to_thursday + 21
    return parts["day"] == fourth_thursday


HOLIDAY_RULES = {
    HOLIDAY_TAGLINES["newYear"]: _on_month_day(0, 1),
    HOLIDAY_TAGLINES["lunarNewYear"]: _on_specific_dates(
        [[2025, 0, 29], [2026, 1, 17], [2027, 1, 6], [2028, 0, 26], [2029, 1, 13], [2030, 1, 3]], 1
    ),
    HOLIDAY_TAGLINES["eid"]: _on_specific_dates(
        [[2025, 2, 30], [2025, 2, 31], [2026, 2, 20], [2027, 2, 10], [2028, 1, 27], [2029, 1, 15], [2030, 1, 5]], 1
    ),
    HOLIDAY_TAGLINES["diwali"]: _on_specific_dates(
        [[2025, 9, 20], [2026, 10, 8], [2027, 9, 28], [2028, 9, 17], [2029, 10, 5], [2030, 9, 25]], 1
    ),
    HOLIDAY_TAGLINES["easter"]: _on_specific_dates(
        [[2025, 3, 20], [2026, 3, 5], [2027, 2, 28], [2028, 3, 16], [2029, 3, 1], [2030, 3, 21]], 1
    ),
    HOLIDAY_TAGLINES["hanukkah"]: _in_year_window([
        {"year": 2025, "month": 11, "day": 15, "duration": 8},
        {"year": 2026, "month": 11, "day": 5, "duration": 8},
        {"year": 2027, "month": 11, "day": 25, "duration": 8},
        {"year": 2028, "month": 11, "day": 13, "duration": 8},
        {"year": 2029, "month": 11, "day": 2, "duration": 8},
        {"year": 2030, "month": 11, "day": 21, "duration": 8},
    ]),
    HOLIDAY_TAGLINES["halloween"]: _on_month_day(9, 31),
    HOLIDAY_TAGLINES["thanksgiving"]: _is_fourth_thursday_of_november,
    HOLIDAY_TAGLINES["valentines"]: _on_month_day(1, 14),
    HOLIDAY_TAGLINES["christmas"]: _on_month_day(11, 25),
}


def _is_tagline_active(tagline: str, date) -> bool:
    rule = HOLIDAY_RULES.get(tagline)
    if not rule:
        return True
    return rule(date)


def _active_taglines(options: dict) -> list[str]:
    if not TAGLINES:
        return [DEFAULT_TAGLINE]
    today = options.get("now")() if options.get("now") else __import__("datetime").datetime.now()
    filtered = [t for t in TAGLINES if _is_tagline_active(t, today)]
    return filtered if filtered else TAGLINES


def _parse_strict_non_negative_integer(value: str) -> int | None:
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        return None
    return parsed if parsed >= 0 else None


def pick_tagline(options: dict | None = None) -> str:
    opts = options or {}
    if opts.get("mode") == "off":
        return ""
    if opts.get("mode") == "default":
        return DEFAULT_TAGLINE
    import os as _os

    env = opts.get("env") or _os.environ
    override = env.get("OPENCLAW_TAGLINE_INDEX")
    if override is not None:
        parsed = _parse_strict_non_negative_integer(override)
        if parsed is not None:
            pool = TAGLINES if TAGLINES else [DEFAULT_TAGLINE]
            return pool[parsed % len(pool)]
    pool = _active_taglines(opts)
    rand = opts.get("random") or __import__("random").random
    index = int(rand() * len(pool)) % len(pool)
    return pool[index]

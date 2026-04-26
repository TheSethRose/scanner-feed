import csv
import re

from .config import RADIO_PHONETICS_FILE, RADIO_UNITS_FILE, SCANNER_CODES_FILE, debug
from .models import RadioAlias, ScannerCode


NUMBER_WORDS = {
    "zero": 0,
    "oh": 0,
    "o": 0,
    "one": 1,
    "two": 2,
    "to": 2,
    "too": 2,
    "three": 3,
    "four": 4,
    "for": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "ate": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fourty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}

STRUCTURED_CODE_PREFIXES = ("code", "signal", "priority")
CODE_WORDS = {word for word in NUMBER_WORDS if word not in {"to", "too", "for"}}


def load_scanner_codes() -> dict[str, ScannerCode]:
    if not SCANNER_CODES_FILE.exists():
        debug(f"scanner code file not found: {SCANNER_CODES_FILE}")
        return {}

    scanner_codes: dict[str, ScannerCode] = {}

    with SCANNER_CODES_FILE.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = (row.get("code") or "").strip()

            if not code:
                continue

            scanner_codes[normalize_code_key(code)] = ScannerCode(
                code_type=(row.get("code_type") or "").strip(),
                code=code,
                meaning=(row.get("meaning") or "").strip(),
                category=(row.get("category") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            )

    return scanner_codes


def split_aliases(value: str) -> tuple[str, ...]:
    return tuple(alias.strip() for alias in value.split("|") if alias.strip())


def load_radio_aliases() -> list[RadioAlias]:
    if not RADIO_UNITS_FILE.exists():
        debug(f"radio units file not found: {RADIO_UNITS_FILE}")
        return []

    aliases: list[RadioAlias] = []

    with RADIO_UNITS_FILE.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            canonical = (row.get("canonical") or "").strip()

            if not canonical:
                continue

            aliases.append(
                RadioAlias(
                    term_type=(row.get("term_type") or "").strip(),
                    canonical=canonical,
                    aliases=tuple(dict.fromkeys((canonical, *split_aliases(row.get("aliases") or "")))),
                    notes=(row.get("notes") or "").strip(),
                )
            )

    return aliases


def load_radio_phonetics() -> dict[str, str]:
    if not RADIO_PHONETICS_FILE.exists():
        debug(f"radio phonetics file not found: {RADIO_PHONETICS_FILE}")
        return {}

    phonetics: dict[str, str] = {}

    with RADIO_PHONETICS_FILE.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            canonical = (row.get("canonical") or "").strip().upper()

            if not canonical:
                continue

            for alias in split_aliases(row.get("aliases") or ""):
                phonetics[alias.lower()] = canonical

    return phonetics


def normalize_code_key(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\bten[\s-]+(\d{1,3})\b", r"10-\1", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s*-\s*", "-", value)
    return value


def parse_number_words(words: list[str]) -> int | None:
    if not words:
        return None

    current = 0

    for word in words:
        value = NUMBER_WORDS.get(word)

        if value is None:
            return None

        if value == 100:
            current = max(current, 1) * 100
        else:
            current += value

    return current


def spoken_number_candidates(words: list[str]) -> list[int]:
    number = parse_number_words(words)

    if number is None:
        return []

    candidates = [number]

    if len(words) > 1:
        pieces = []

        for word in words:
            value = NUMBER_WORDS.get(word)

            if value is None:
                return candidates

            pieces.append(str(value))

        digits = "".join(pieces)

        if digits.isdigit():
            candidates.append(int(digits))

    return list(dict.fromkeys(candidates))


def short_meaning(meaning: str) -> str:
    meaning = meaning.split("/", 1)[0]
    meaning = meaning.split(" - ", 1)[0]
    meaning = meaning.split("(", 1)[0]
    return meaning.strip()


def token_spans(text: str) -> list[tuple[str, int, int]]:
    return [
        (match.group(0).lower(), match.start(), match.end())
        for match in re.finditer(r"[a-z0-9]+", text, flags=re.IGNORECASE)
    ]


def replace_spans(text: str, replacements: list[tuple[int, int, str]]) -> str:
    result = text

    for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        result = f"{result[:start]}{replacement}{result[end:]}"

    return result


def numbers_from_token(token: str) -> list[int]:
    if token.isdigit():
        return [int(token)]

    if token in CODE_WORDS:
        return spoken_number_candidates([token])

    return []


def find_code_annotations(text: str, scanner_codes: dict[str, ScannerCode]) -> list[tuple[int, int, str]]:
    tokens = token_spans(text)
    annotations: list[tuple[int, int, str]] = []

    for index, (token, start, _end) in enumerate(tokens):
        if token == "10" and index + 1 < len(tokens):
            for number in numbers_from_token(tokens[index + 1][0]):
                key = normalize_code_key(f"10-{number}")

                if key in scanner_codes:
                    annotations.append((start, tokens[index + 1][2], short_meaning(scanner_codes[key].meaning)))
                    break

        if token == "ten":
            best: tuple[int, ScannerCode] | None = None

            for end_index in range(index + 2, min(len(tokens), index + 5) + 1):
                words = [part[0] for part in tokens[index + 1:end_index]]

                if not words or any(word not in CODE_WORDS for word in words):
                    break

                for number in spoken_number_candidates(words):
                    key = normalize_code_key(f"10-{number}")

                    if key in scanner_codes:
                        best = (end_index - 1, scanner_codes[key])

            if best:
                end_index, entry = best
                annotations.append((start, tokens[end_index][2], short_meaning(entry.meaning)))

        if token in STRUCTURED_CODE_PREFIXES:
            best = None

            for end_index in range(index + 2, min(len(tokens), index + 4) + 1):
                words = [part[0] for part in tokens[index + 1:end_index]]

                if not words or any(word not in CODE_WORDS and not word.isdigit() for word in words):
                    break

                candidates = [int(words[0])] if len(words) == 1 and words[0].isdigit() else spoken_number_candidates(words)

                for number in candidates:
                    key = normalize_code_key(f"{token} {number}")

                    if key in scanner_codes:
                        best = (end_index - 1, scanner_codes[key])

            if best:
                end_index, entry = best
                annotations.append((start, tokens[end_index][2], short_meaning(entry.meaning)))

    return annotations


def find_code_replacements(text: str, scanner_codes: dict[str, ScannerCode]) -> list[tuple[int, int, str]]:
    replacements: list[tuple[int, int, str]] = []

    for start, end, label in find_code_annotations(text, scanner_codes):
        phrase = text[start:end]
        tokens = token_spans(phrase)

        if not tokens:
            continue

        first = tokens[0][0]
        canonical = phrase

        if first == "10":
            canonical = f"10-{tokens[1][0]}" if len(tokens) > 1 else phrase
        elif first == "ten":
            candidates = spoken_number_candidates([token for token, _start, _end in tokens[1:]])
            canonical = f"10-{candidates[0]}" if candidates else phrase
        elif first in STRUCTURED_CODE_PREFIXES:
            words = [token for token, _start, _end in tokens[1:]]
            candidates = [int(words[0])] if len(words) == 1 and words[0].isdigit() else spoken_number_candidates(words)
            canonical = f"{first.title()} {candidates[0]}" if candidates else phrase

        replacements.append((start, end, f"{canonical} [{label}]"))

    return replacements


def radio_number_from_words(words: list[str]) -> str:
    parts: list[str] = []
    index = 0

    while index < len(words):
        word = words[index]
        value = NUMBER_WORDS.get(word)

        if value is None:
            index += 1
            continue

        next_value = NUMBER_WORDS.get(words[index + 1]) if index + 1 < len(words) else None

        if value >= 20 and next_value is not None and 0 <= next_value <= 9:
            parts.append(str(value + next_value))
            index += 2
            continue

        if value == 100 and parts:
            parts[-1] = str(int(parts[-1]) * 100)
        else:
            parts.append(str(value))

        index += 1

    return "".join(parts)


def find_radio_number_replacements(text: str) -> list[tuple[int, int, str]]:
    replacements: list[tuple[int, int, str]] = []

    for segment_match in re.finditer(r"[^.!?\n]+", text):
        tokens = token_spans(segment_match.group(0))
        offset = segment_match.start()
        index = 0

        while index < len(tokens):
            if tokens[index][0] not in NUMBER_WORDS or tokens[index][0] == "to":
                index += 1
                continue

            start = index
            groups: list[list[str]] = [[]]
            has_separator = False

            while index < len(tokens):
                current = tokens[index][0]
                next_token = tokens[index + 1][0] if index + 1 < len(tokens) else ""

                if current == "to" and groups[-1] and next_token in NUMBER_WORDS and next_token != "to":
                    has_separator = True
                    groups.append([])
                    index += 1
                    continue

                if current not in NUMBER_WORDS or current == "to":
                    break

                groups[-1].append(current)
                index += 1

            converted = " to ".join(radio_number_from_words(group) for group in groups if group)

            if converted and (has_separator or len(converted.replace(" to ", "")) >= 4):
                start_pos = offset + tokens[start][1]
                end_pos = offset + tokens[index - 1][2]
                replacements.append((start_pos, end_pos, f"{text[start_pos:end_pos]} [{converted}]"))

            if index == start:
                index += 1

    return replacements


def alias_pattern(alias: str) -> re.Pattern:
    escaped_words = [re.escape(word) for word in re.findall(r"[a-z0-9]+", alias.lower())]
    return re.compile(r"(?<![a-z0-9])" + r"[\W_]+".join(escaped_words) + r"(?![a-z0-9])", re.IGNORECASE)


def find_alias_replacements(text: str, radio_aliases: list[RadioAlias]) -> list[tuple[int, int, str]]:
    replacements: list[tuple[int, int, str]] = []

    for entry in radio_aliases:
        for alias in sorted(entry.aliases, key=len, reverse=True):
            if alias.lower() == entry.canonical.lower():
                continue

            for match in alias_pattern(alias).finditer(text):
                replacements.append((match.start(), match.end(), entry.canonical))

    return replacements


def find_phonetic_replacements(text: str, phonetics: dict[str, str]) -> list[tuple[int, int, str]]:
    tokens = token_spans(text)
    replacements: list[tuple[int, int, str]] = []
    index = 0

    while index < len(tokens):
        if tokens[index][0] not in phonetics:
            index += 1
            continue

        start_index = index
        letters: list[str] = []

        while index < len(tokens) and tokens[index][0] in phonetics:
            letters.append(phonetics[tokens[index][0]])
            index += 1

        if len(letters) >= 2:
            replacements.append((tokens[start_index][1], tokens[index - 1][2], "".join(letters)))

    return replacements


def filter_overlapping_replacements(replacements: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    accepted: list[tuple[int, int, str]] = []

    for replacement in sorted(replacements, key=lambda item: (item[0], -(item[1] - item[0]))):
        start, end, _value = replacement

        if any(start < accepted_end and end > accepted_start for accepted_start, accepted_end, _ in accepted):
            continue

        accepted.append(replacement)

    return accepted


def normalize_radio_language(
    text: str,
    scanner_codes: dict[str, ScannerCode],
    radio_aliases: list[RadioAlias],
    phonetics: dict[str, str],
) -> str:
    text = replace_spans(text, filter_overlapping_replacements(find_phonetic_replacements(text, phonetics)))
    text = replace_spans(text, filter_overlapping_replacements(find_alias_replacements(text, radio_aliases)))

    replacements = find_code_replacements(text, scanner_codes)
    occupied: list[tuple[int, int]] = [(start, end) for start, end, _replacement in replacements]

    for start, end, replacement in find_radio_number_replacements(text):
        if any(start < occupied_end and end > occupied_start for occupied_start, occupied_end in occupied):
            continue

        replacements.append((start, end, replacement))
        occupied.append((start, end))

    return replace_spans(text, filter_overlapping_replacements(replacements))


def looks_like_radio_code(text: str, scanner_codes: dict[str, ScannerCode]) -> bool:
    return bool(find_code_replacements(text, scanner_codes))

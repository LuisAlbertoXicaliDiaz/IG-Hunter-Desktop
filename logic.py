from __future__ import annotations

import csv
import json
import re
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Literal
from urllib.parse import unquote, urlparse

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    BeautifulSoup = None


USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
INSTAGRAM_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9._]{1,30})/?",
    re.IGNORECASE,
)

IGNORED_USERNAMES = {
    "about",
    "accounts",
    "api",
    "close",
    "developer",
    "direct",
    "explore",
    "followers",
    "following",
    "instagram",
    "legal",
    "oauth",
    "pending",
    "privacy",
    "profile",
    "profiles",
    "reel",
    "reels",
    "requests",
    "stories",
    "terms",
    "_u",
    "www",
}

KNOWN_FILES = {
    "followers": ("followers",),
    "following": ("following",),
    "close_friends": ("close_friends",),
    "pending_follow_requests": ("pending_follow_requests",),
    "favorited_profiles": ("profiles_you've_favorited", "profiles_youve_favorited"),
    "recent_follow_requests": ("recent_follow_requests",),
    "recently_unfollowed_profiles": ("recently_unfollowed_profiles",),
    "removed_suggestions": ("removed_suggestions",),
}

CATEGORY_LABELS = {
    "not_following_back": "No te siguen de vuelta",
    "fans": "Te siguen y tú no los sigues",
    "mutuals": "Seguimiento mutuo",
    "close_friends": "Mejores amigos",
    "pending_follow_requests": "Solicitudes pendientes",
    "favorited_profiles": "Perfiles favoritos",
    "recent_follow_requests": "Solicitudes recientes",
    "recently_unfollowed_profiles": "Perfiles dejados de seguir",
    "removed_suggestions": "Sugerencias eliminadas",
}


class InstagramHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.texts: list[str] = []
        self.current_text_tag: str | None = None
        self.anchor_with_href_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3"}:
            self.current_text_tag = tag

        if tag == "a":
            href_found = False
            for name, value in attrs:
                if name == "href" and value:
                    self.links.append(value)
                    href_found = True
            if href_found:
                self.anchor_with_href_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == self.current_text_tag:
            self.current_text_tag = None
        if tag == "a" and self.anchor_with_href_depth:
            self.anchor_with_href_depth -= 1

    def handle_data(self, data: str) -> None:
        data = data.strip()
        if self.anchor_with_href_depth:
            return
        if data and len(data) <= 60 and (self.current_text_tag or data.startswith("@")):
            self.texts.append(data)


@dataclass(frozen=True)
class InstagramProfile:
    username: str

    @property
    def url(self) -> str:
        return profile_url(self.username)

    def to_dict(self) -> dict[str, str]:
        return {"username": self.username, "url": self.url}


@dataclass(frozen=True)
class AnalysisResult:
    followers_count: int
    following_count: int
    not_following_back: list[str]
    fans: list[str]
    mutuals: list[str]
    created_at: str
    extra_categories: dict[str, list[str]] = field(default_factory=dict)
    detected_files: dict[str, str] = field(default_factory=dict)

    @property
    def not_following_back_count(self) -> int:
        return len(self.not_following_back)

    @property
    def fans_count(self) -> int:
        return len(self.fans)

    @property
    def mutuals_count(self) -> int:
        return len(self.mutuals)

    def category_users(self, category: str) -> list[str]:
        base_categories = {
            "not_following_back": self.not_following_back,
            "fans": self.fans,
            "mutuals": self.mutuals,
        }
        return base_categories.get(category, self.extra_categories.get(category, []))

    def category_profiles(self, category: str) -> list[InstagramProfile]:
        return [InstagramProfile(username) for username in self.category_users(category)]

    def all_categories(self) -> dict[str, list[str]]:
        return {
            "not_following_back": self.not_following_back,
            "fans": self.fans,
            "mutuals": self.mutuals,
            **self.extra_categories,
        }

    def to_dict(self) -> dict:
        data = asdict(self)
        data["not_following_back_count"] = self.not_following_back_count
        data["fans_count"] = self.fans_count
        data["mutuals_count"] = self.mutuals_count
        data["profiles"] = {
            category: [InstagramProfile(username).to_dict() for username in users]
            for category, users in self.all_categories().items()
        }
        return data


def profile_url(username: str) -> str:
    return f"https://www.instagram.com/{username}/"


def normalize_username(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None

    url_username = _username_from_instagram_url(value)
    if url_username:
        value = url_username

    value = value.strip().strip("@").strip("/").lower()
    value = value.split("?")[0].split("#")[0]

    if not USERNAME_RE.match(value):
        return None
    if value in IGNORED_USERNAMES:
        return None
    return value


def _username_from_instagram_url(value: str) -> str | None:
    if "instagram.com" not in value.lower():
        return None

    parsed = urlparse(value if "://" in value else f"https://{value}")
    if "instagram.com" not in parsed.netloc.lower():
        return None

    parts = [
        unquote(part).strip()
        for part in parsed.path.split("/")
        if unquote(part).strip()
    ]
    if not parts:
        return None

    if parts[0].lower() == "_u" and len(parts) >= 2:
        return parts[1]

    if parts[0].lower() in IGNORED_USERNAMES:
        return None

    return parts[0]


def _html_candidates(html: str) -> Iterable[str]:
    if BeautifulSoup is None:
        parser = InstagramHTMLParser()
        parser.feed(html)
        yield from parser.links
        yield from parser.texts
        return

    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    texts: list[str] = []

    for tag in soup.find_all("a"):
        href = tag.get("href")
        if href:
            links.append(href)
        else:
            text = tag.get_text(" ", strip=True)
            if text.startswith("@"):
                texts.append(text)

    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(" ", strip=True)
        if text and len(text) <= 60:
            texts.append(text)

    for tag in soup.find_all(["span", "div"]):
        text = tag.get_text(" ", strip=True)
        if text.startswith("@") and len(text) <= 60:
            texts.append(text)

    yield from links
    yield from texts


def _json_candidates(data) -> Iterable[str]:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in {"href", "value", "username", "string_list_data"} and isinstance(value, str):
                yield value
            yield from _json_candidates(value)
    elif isinstance(data, list):
        for item in data:
            yield from _json_candidates(item)
    elif isinstance(data, str):
        yield data


def _paths_from_input(path: str | Path) -> list[Path]:
    selected = Path(path).expanduser()
    if not selected.exists():
        raise FileNotFoundError(f"No se encontró el archivo o carpeta: {selected}")

    if selected.is_file():
        return [selected]

    files = [
        file
        for file in selected.rglob("*")
        if file.suffix.lower() in {".html", ".htm", ".json"}
    ]
    if not files:
        raise ValueError("La carpeta no contiene archivos .html, .htm o .json.")
    return files


def extract_usernames(path: str | Path) -> set[str]:
    usernames: set[str] = set()

    for file_path in _paths_from_input(path):
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        suffix = file_path.suffix.lower()

        if suffix in {".html", ".htm"}:
            candidates = _html_candidates(content)
        elif suffix == ".json":
            candidates = _json_candidates(json.loads(content))
        else:
            continue

        for candidate in candidates:
            username = normalize_username(candidate)
            if username:
                usernames.add(username)

    return usernames


def scan_instagram_export(path: str | Path) -> dict[str, Path]:
    selected = Path(path).expanduser()
    if not selected.exists() or not selected.is_dir():
        raise ValueError("Selecciona una carpeta válida con tus archivos de Instagram.")

    files = _paths_from_input(selected)
    detected: dict[str, Path] = {}

    for file_path in files:
        normalized_name = file_path.stem.lower().replace("’", "'")
        for category, prefixes in KNOWN_FILES.items():
            if any(normalized_name.startswith(prefix) for prefix in prefixes):
                detected.setdefault(category, file_path)

    return detected


def analyze_instagram_data(
    followers_path: str | Path,
    following_path: str | Path,
    extra_paths: dict[str, str | Path] | None = None,
) -> AnalysisResult:
    followers = extract_usernames(followers_path)
    following = extract_usernames(following_path)

    if not followers:
        raise ValueError("No se encontraron usuarios en followers.")
    if not following:
        raise ValueError("No se encontraron usuarios en following.")

    extra_categories: dict[str, list[str]] = {}
    detected_files: dict[str, str] = {
        "followers": str(Path(followers_path)),
        "following": str(Path(following_path)),
    }

    for category, path in (extra_paths or {}).items():
        if category in {"followers", "following"} or not path:
            continue
        users = sorted(extract_usernames(path))
        extra_categories[category] = users
        detected_files[category] = str(Path(path))

    return AnalysisResult(
        followers_count=len(followers),
        following_count=len(following),
        not_following_back=sorted(following - followers),
        fans=sorted(followers - following),
        mutuals=sorted(followers & following),
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        extra_categories=extra_categories,
        detected_files=detected_files,
    )


def export_result(
    result: AnalysisResult,
    output_path: str | Path,
    export_type: Literal["txt", "csv", "json", "xlsx"] = "txt",
) -> Path:
    output = Path(output_path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)

    if export_type == "txt":
        _export_txt(result, output)
    elif export_type == "csv":
        _export_csv(result, output)
    elif export_type == "json":
        output.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif export_type == "xlsx":
        _export_xlsx(result, output)
    else:
        raise ValueError("Formato no válido. Usa txt, csv, json o xlsx.")

    return output


def _category_rows(result: AnalysisResult) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for category, users in result.all_categories().items():
        label = CATEGORY_LABELS.get(category, category)
        for username in users:
            rows.append((label, username, profile_url(username)))
    return rows


def _export_txt(result: AnalysisResult, output: Path) -> None:
    lines = [
        "Reporte de IgHunter Pro",
        f"Generado: {result.created_at}",
        "",
        f"Seguidores: {result.followers_count}",
        f"Seguidos: {result.following_count}",
        f"No te siguen de vuelta: {result.not_following_back_count}",
        f"Te siguen y tú no los sigues: {result.fans_count}",
        f"Seguimiento mutuo: {result.mutuals_count}",
        "",
    ]

    for category, users in result.all_categories().items():
        lines.append(CATEGORY_LABELS.get(category, category))
        lines.append("-" * 40)
        if users:
            lines.extend(f"@{username} - {profile_url(username)}" for username in users)
        else:
            lines.append("Sin usuarios.")
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")


def _export_csv(result: AnalysisResult, output: Path) -> None:
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["categoria", "usuario", "perfil"])
        writer.writerows(_category_rows(result))


def _export_xlsx(result: AnalysisResult, output: Path) -> None:
    rows = [("categoria", "usuario", "perfil"), *_category_rows(result)]
    sheet_rows = []

    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            cell_ref = f"{_excel_col(col_index)}{row_index}"
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        f'{"".join(sheet_rows)}'
        '</sheetData>'
        '</worksheet>'
    )

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Reporte" sheetId="1" r:id="rId1"/></sheets>'
            '</workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>',
        )
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)


def _excel_col(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result

import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "paper-assets" / "2604.06233v1.pdf"
LATEX_DIR = ROOT / "paper-assets" / "latex from arxiv"
BBL_PATH = LATEX_DIR / "main.bbl"
OUT_PATH = ROOT / "paper-content.js"
FIGURE_DIR = ROOT / "assets" / "paper-figures"
FIGURE_1_PATH = FIGURE_DIR / "figure-1.png"
FOOTNOTES = []
CITATION_ALIAS_OVERRIDES = {
    "wellman_just_2005": [
        "wel, 2005",
        "wel (2005)",
        "Wellman and Simmons, 2005",
        "Wellman and Simmons (2005)",
    ],
}
FIGURES = [
    {
        "label": "Figure 1",
        "sectionId": "1-introduction",
        "captionPrefix": "Figure 1:",
        "src": "assets/paper-figures/figure-1.png",
        "alt": "Two chatbot responses to a rule-evasion request, one helping and one refusing.",
    },
    {
        "label": "Figure 2",
        "sectionId": "4-results",
        "captionPrefix": "Figure 2:",
        "src": "assets/paper-figures/figure-2.png",
        "alt": "Average refusal rate heatmap by defeat type and authority type across all models.",
    },
    {
        "label": "Figure 3",
        "sectionId": "4-results",
        "captionPrefix": "Figure 3:",
        "src": "assets/paper-figures/figure-3.png",
        "alt": "Refusal rate radar charts by defeat type for each model configuration.",
    },
]
TABLES = [
    {
        "label": "Table 1",
        "sectionId": "3-1-taxonomy-design",
        "captionPrefix": "Table 1:",
        "caption": "Defeat-authority evaluation matrix (n = 1,290). Values are case counts per cell. Dashes mark excluded cells.",
        "headers": ["Group", "Authority", "Control", "Illegit. auth.", "Content def.", "Applic. def.", "Exception just."],
        "rows": [
            ["Government", "National", "24", "24", "28", "31", "27"],
            ["Government", "Subnational", "13", "15", "15", "14", "14"],
            ["Government", "Supranational", "-", "6", "24", "16", "5"],
            ["Non-voluntary", "Family", "17", "6", "15", "19", "10"],
            ["Non-voluntary", "Tribe", "-", "6", "7", "8", "7"],
            ["Semi-voluntary", "Profession", "12", "8", "21", "31", "23"],
            ["Semi-voluntary", "Faith group", "17", "16", "19", "13", "12"],
            ["Semi-voluntary", "School", "23", "6", "27", "11", "24"],
            ["Semi-voluntary", "HOA", "10", "-", "23", "31", "10"],
            ["Semi-voluntary", "Union", "12", "-", "16", "11", "7"],
            ["Semi-voluntary", "Algorithmic", "14", "11", "33", "53", "19"],
            ["Semi-voluntary", "Military", "7", "12", "9", "8", "11"],
            ["Voluntary", "Workplace", "32", "8", "23", "27", "29"],
            ["Voluntary", "Club", "7", "-", "8", "5", "6"],
            ["Voluntary", "Landlord", "10", "-", "29", "31", "13"],
            ["Voluntary", "Creditor", "6", "-", "11", "37", "7"],
            ["Voluntary", "Property", "-", "-", "5", "6", "5"],
            ["Voluntary", "Contract", "-", "-", "12", "9", "5"],
            ["Voluntary", "Delegated", "5", "10", "12", "11", "10"],
        ],
    },
    {
        "label": "Table 2",
        "sectionId": "e-2-response-categories-by-model",
        "captionPrefix": "Table 2:",
        "caption": "Response category distribution by model (%). Models sorted by helps rate.",
        "headers": ["Model", "Pure rule-blind", "Safety-grounded", "Engaged only", "Engaged + safety", "Helps", "N"],
        "rows": [
            ["Grok-4", "10.0", "28.9", "1.4", "5.7", "54.0", "1,289"],
            ["Grok-4-fast", "20.8", "33.0", "2.6", "8.3", "35.3", "1,290"],
            ["Gemini 3.1 Flash Lite", "8.2", "28.4", "6.4", "23.4", "33.6", "1,290"],
            ["Gemini 3.1 Pro", "27.8", "23.7", "5.8", "9.6", "33.1", "1,290"],
            ["Nemotron-3 Nano", "33.8", "17.5", "1.4", "16.4", "30.9", "1,287"],
            ["Claude Opus 4.6", "3.3", "21.0", "7.5", "40.0", "28.2", "1,286"],
            ["Nemotron-3 Super", "0.9", "24.9", "1.8", "44.7", "27.7", "1,290"],
            ["Claude Sonnet 4.6", "4.1", "20.3", "7.4", "44.7", "23.5", "1,270"],
            ["GLM-5 Turbo", "23.9", "18.8", "12.2", "22.3", "22.8", "1,290"],
            ["GLM-5", "10.4", "29.2", "8.5", "29.5", "22.3", "1,290"],
            ["Qwen 3.5-397B", "5.0", "36.8", "4.8", "41.0", "12.4", "1,290"],
            ["Qwen 3.5 Plus", "4.9", "36.6", "4.3", "43.2", "11.0", "1,289"],
            ["GPT-5.4-nano-think", "21.2", "29.8", "13.0", "26.3", "9.6", "1,290"],
            ["GPT-5.4-base", "19.1", "23.0", "24.5", "24.9", "8.4", "1,290"],
            ["GPT-5.4-thinking", "14.7", "24.8", "19.8", "32.6", "8.1", "1,290"],
            ["GPT-5.4-mini-think", "29.6", "24.1", "21.0", "17.4", "7.9", "1,290"],
            ["Qwen 3.5 Flash", "7.5", "42.2", "5.1", "37.5", "7.6", "1,289"],
            ["GPT-5.4-mini-base", "30.0", "23.0", "22.7", "17.7", "6.5", "1,289"],
        ],
    },
    {
        "label": "Table 3",
        "sectionId": "e-3-control-vs-defeated-comparison-by-model",
        "captionPrefix": "Table 3:",
        "caption": "Control vs. defeated helps and pure rule-blind rates by model (%).",
        "headers": ["Model", "Helps control", "Helps defeated", "Helps delta", "Pure control", "Pure defeated", "Pure delta"],
        "rows": [
            ["Gemini 3.1 Flash Lite", "3.8", "39.3", "+35.5", "17.7", "6.4", "-11.3"],
            ["Grok-4-fast", "5.3", "41.1", "+35.8", "27.3", "19.5", "-7.8"],
            ["Gemini 3.1 Pro", "3.8", "38.8", "+34.9", "46.9", "24.1", "-22.8"],
            ["Claude Opus 4.6", "2.9", "33.1", "+30.2", "8.2", "2.3", "-5.9"],
            ["Nemotron-3 Super", "3.8", "32.3", "+28.5", "3.3", "0.5", "-2.9"],
            ["Claude Sonnet 4.6", "1.0", "27.9", "+26.9", "8.2", "3.3", "-4.9"],
            ["Nemotron-3 Nano", "10.0", "35.0", "+24.9", "34.4", "33.7", "-0.8"],
            ["GLM-5 Turbo", "1.9", "26.8", "+24.9", "50.7", "18.7", "-32.0"],
            ["Grok-4", "33.5", "58.0", "+24.5", "14.8", "9.1", "-5.8"],
            ["GLM-5", "3.3", "26.0", "+22.6", "13.9", "9.7", "-4.2"],
            ["Qwen 3.5-397B", "0.0", "14.8", "+14.8", "6.7", "4.6", "-2.1"],
            ["Qwen 3.5 Plus", "0.5", "13.1", "+12.6", "8.6", "4.2", "-4.4"],
            ["GPT-5.4-thinking", "0.0", "9.7", "+9.7", "26.3", "12.4", "-13.9"],
            ["GPT-5.4-base", "1.0", "9.9", "+8.9", "29.2", "17.2", "-12.0"],
            ["Qwen 3.5 Flash", "0.5", "9.0", "+8.5", "9.6", "7.1", "-2.4"],
            ["GPT-5.4-mini-think", "1.0", "9.3", "+8.3", "46.4", "26.4", "-20.0"],
            ["GPT-5.4-nano-think", "3.3", "10.8", "+7.5", "27.3", "20.1", "-7.2"],
            ["GPT-5.4-mini-base", "0.5", "7.7", "+7.2", "41.6", "27.8", "-13.8"],
        ],
    },
    {
        "label": "Table 4",
        "sectionId": "e-4-dual-use-stratification",
        "captionPrefix": "Table 4:",
        "caption": "Helps rate by dual-use status and condition (%).",
        "headers": ["Stratum", "Control", "Defeated", "Delta", "N ctrl", "N def"],
        "rows": [["DU-flagged", "2.8", "12.0", "+9.2", "2,499", "10,821"], ["Non-DU (clean)", "7.1", "40.4", "+33.3", "1,260", "8,609"], ["All gated", "4.2", "24.6", "+20.3", "3,759", "19,430"]],
    },
    {
        "label": "Table 5",
        "sectionId": "e-4-dual-use-stratification",
        "captionPrefix": "Table 5:",
        "caption": "Non-DU cases: control vs. defeated helps rate by model (%). Sorted by delta.",
        "headers": ["Model", "Control helps", "Defeated helps", "Delta", "N"],
        "rows": [
            ["Gemini 3.1 Pro", "4.3", "64.3", "+60.0", "549"],
            ["Gemini 3.1 Flash Lite", "7.1", "63.7", "+56.5", "549"],
            ["Grok-4-fast", "8.6", "62.2", "+53.6", "549"],
            ["Claude Opus 4.6", "1.4", "50.2", "+48.8", "548"],
            ["Nemotron-3 Super", "7.1", "53.0", "+45.9", "549"],
            ["GLM-5 Turbo", "1.4", "46.8", "+45.3", "549"],
            ["GLM-5", "1.4", "44.7", "+43.2", "549"],
            ["Claude Sonnet 4.6", "1.4", "42.9", "+41.5", "538"],
            ["Nemotron-3 Nano", "14.3", "50.8", "+36.6", "548"],
            ["Qwen 3.5-397B", "0.0", "27.3", "+27.3", "549"],
            ["Qwen 3.5 Plus", "1.4", "24.6", "+23.2", "549"],
            ["Grok-4", "61.4", "83.3", "+21.9", "549"],
            ["GPT-5.4-thinking", "0.0", "18.8", "+18.8", "549"],
            ["GPT-5.4-base", "2.9", "20.9", "+18.0", "549"],
            ["GPT-5.4-mini-think", "2.9", "19.0", "+16.1", "549"],
            ["Qwen 3.5 Flash", "1.4", "16.7", "+15.3", "549"],
            ["GPT-5.4-mini-base", "1.4", "15.9", "+14.4", "549"],
            ["GPT-5.4-nano-think", "8.6", "22.3", "+13.8", "549"],
        ],
    },
    {
        "label": "Table 6",
        "sectionId": "e-5-engagement-rates-by-model-and-defeat-type",
        "captionPrefix": "Table 6:",
        "caption": "Engagement rate (%) by model and defeat family.",
        "headers": ["Model", "Applic. defeat", "Content defeat", "Control", "Except. justified", "Illegit. authority", "Overall"],
        "rows": [
            ["Claude Sonnet 4.6", "83.3", "81.5", "13.0", "81.6", "87.3", "71.3"],
            ["Nemotron-3 Super", "80.9", "88.1", "8.6", "75.4", "85.2", "70.5"],
            ["Claude Opus 4.6", "82.7", "83.0", "9.7", "78.3", "82.8", "70.2"],
            ["GPT-5.4-thinking", "72.6", "70.6", "4.3", "54.5", "63.3", "56.7"],
            ["Qwen 3.5 Plus", "62.8", "68.5", "8.6", "62.7", "71.1", "56.3"],
            ["Qwen 3.5-397B", "64.5", "67.1", "6.2", "62.3", "68.0", "55.7"],
            ["GPT-5.4-base", "69.4", "60.8", "3.3", "56.1", "62.5", "53.3"],
            ["GLM-5", "62.1", "61.1", "4.3", "61.1", "50.0", "51.1"],
            ["GLM-5 Turbo", "58.9", "59.9", "2.9", "62.3", "50.0", "49.8"],
            ["Gemini 3.1 Flash Lite", "59.7", "57.0", "2.9", "56.1", "57.8", "48.9"],
            ["Qwen 3.5 Flash", "53.9", "58.2", "5.3", "52.9", "63.3", "47.9"],
            ["GPT-5.4-mini-base", "53.2", "49.4", "2.9", "46.3", "55.5", "43.0"],
            ["GPT-5.4-nano-think", "53.8", "43.0", "1.4", "52.9", "53.1", "42.2"],
            ["GPT-5.4-mini-think", "53.5", "46.6", "0.0", "45.1", "50.0", "41.1"],
            ["Nemotron-3 Nano", "44.4", "44.9", "5.3", "37.2", "41.4", "36.5"],
            ["Gemini 3.1 Pro", "39.2", "36.5", "0.5", "44.7", "27.3", "32.1"],
            ["Grok-4-fast", "29.0", "27.0", "0.5", "41.4", "50.0", "28.3"],
            ["Grok-4", "22.6", "28.9", "1.0", "32.8", "49.2", "25.3"],
        ],
    },
    {
        "label": "Table 7",
        "sectionId": "e-6-helps-rate-by-model-and-defeat-family",
        "captionPrefix": "Table 7:",
        "caption": "Helps rate (%) by model and defeat family.",
        "headers": ["Model", "Applic. defeat", "Content defeat", "Control", "Except. justified", "Illegit. authority", "Overall"],
        "rows": [
            ["Grok-4", "60.5", "53.0", "33.5", "54.5", "70.3", "54.0"],
            ["Grok-4-fast", "40.3", "35.3", "5.3", "42.6", "55.5", "35.3"],
            ["Gemini 3.1 Flash Lite", "40.6", "34.7", "3.8", "38.9", "48.4", "33.6"],
            ["Gemini 3.1 Pro", "37.1", "38.6", "3.8", "31.6", "57.8", "33.1"],
            ["Nemotron-3 Nano", "34.7", "33.3", "10.0", "34.3", "41.4", "30.9"],
            ["Claude Opus 4.6", "25.3", "36.6", "2.9", "29.1", "53.9", "28.2"],
            ["Nemotron-3 Super", "27.4", "28.8", "3.8", "38.5", "43.8", "27.7"],
            ["Claude Sonnet 4.6", "22.6", "28.0", "1.0", "29.9", "40.9", "23.5"],
            ["GLM-5 Turbo", "26.6", "25.5", "1.9", "23.0", "38.3", "22.8"],
            ["GLM-5", "24.5", "23.4", "3.3", "25.4", "38.3", "22.3"],
            ["Qwen 3.5-397B", "13.7", "15.1", "0.0", "11.5", "23.4", "12.4"],
            ["Qwen 3.5 Plus", "12.9", "12.8", "0.5", "10.7", "18.8", "11.0"],
            ["GPT-5.4-nano-think", "12.6", "9.8", "3.3", "9.0", "11.7", "9.6"],
            ["GPT-5.4-base", "11.8", "11.9", "1.0", "5.7", "7.0", "8.4"],
            ["GPT-5.4-thinking", "8.9", "11.6", "0.0", "4.5", "17.2", "8.1"],
            ["GPT-5.4-mini-think", "9.9", "10.7", "1.0", "4.9", "11.7", "7.9"],
            ["Qwen 3.5 Flash", "10.5", "7.7", "0.5", "8.6", "8.6", "7.6"],
            ["GPT-5.4-mini-base", "8.6", "8.6", "0.5", "5.3", "7.0", "6.5"],
        ],
    },
]

REFERENCE_STARTS = [
    "Just and Unjust Laws.",
    "Amanda Askell,",
    "Yuntao Bai,",
    "Federico Bianchi,",
    "Faeze Brahman,",
    "Kimberley Brownlee.",
    "Justin Cui,",
    "Candice Delmas.",
    "Candice Delmas and",
    "Iason Gabriel.",
    "Deep Ganguli,",
    "Seungju Han,",
    "Hakan Inan,",
    "Zhijing Jin,",
    "Bruce W. Lee,",
    "David Lefkowitz.",
    "Nestor Maslej.",
    "Mantas Mazeika,",
    "Raphael Milliere.",
    "Rapha?l Milli?re.",
    "OpenAI.",
    "Licheng Pan,",
    "Arjun Panickssery,",
    "Alicia Parrish,",
    "John Rawls.",
    "Joseph Raz.",
    "Alexander von Recum,",
    "Richard Ren,",
    "Massimo Renzo and",
    "Paul Rottger,",
    "Paul R?ttger,",
    "Chenyu Shi,",
    "A. John Simmons.",
    "Guangzhi Sun,",
    "Bertie Vidgen,",
    "Yuxia Wang,",
    "Tinghao Xie,",
    "Zhehao Zhang,",
    "Jiachen Zhao,",
]


TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2217": "*",
        "\u2022": "-",
        "\u00a7": "Section",
        "\u2265": ">=",
        "\u00e9": "e",
        "\u00e8": "e",
        "\u00f6": "o",
        "\u00a0": " ",
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
    }
)


def normalize(text):
    text = text.translate(TRANSLATION)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.replace(" ?", "'")
    text = text.replace("?s", "'s")
    text = text.replace("?t", "'t")
    text = text.replace("?re", "'re")
    text = text.replace("?ve", "'ve")
    text = text.replace("?ll", "'ll")
    text = text.replace("URLhttp", "URL http")
    text = text.replace("URLhttps", "URL https")
    text = text.replace("http: //", "http://")
    text = text.replace("https: //", "https://")
    text = text.replace("http://arxiv.org/ abs/", "http://arxiv.org/abs/")
    text = text.replace("https://arxiv.org/ abs/", "https://arxiv.org/abs/")
    text = text.replace("https://www.cambridge.org/core/books/ is-there", "https://www.cambridge.org/core/books/is-there")
    text = text.replace("https://openai.com/index/ introducing", "https://openai.com/index/introducing")
    text = re.sub(r"([a-z)])\.([A-Z])", r"\1. \2", text)
    text = re.sub(r"([a-z)])\?([A-Z])", r"\1? \2", text)
    text = text.replace("callblind refusal", "call blind refusal")
    text = text.replace("refuseharmlessrequests", "refuse harmless requests")
    text = text.replace("amoralerror", "a moral error")
    text = text.replace("failure modeblind refusal", "failure mode blind refusal")
    text = text.replace("conditionsorganized", "conditions organized")
    text = text.replace("datasetof", "dataset of")
    text = text.replace("evaluationof", "evaluation of")
    text = text.replace("thestatus", "the status")
    text = text.replace(" aboutrule", " about rule")
    return text.strip()


def slugify(title):
    title = title.lower()
    title = title.replace("&", "and")
    title = re.sub(r"[^a-z0-9]+", "-", title).strip("-")
    return title or "section"


def is_heading(line):
    cleaned = normalize(line)
    if cleaned in {"ABSTRACT", "Abstract", "References"}:
        return ("abstract" if cleaned.lower() == "abstract" else "references", cleaned.title())

    main = re.match(r"^([1-6](?:\.[0-9]+)?)\s+([A-Z][A-Za-z0-9 ,:/&().+-]{2,90})$", cleaned)
    if main:
        title = f"{main.group(1)} {main.group(2)}"
        return (slugify(title), title)

    appendix = re.match(r"^([A-E](?:\.[0-9]+)?)\s+([A-Z][A-Za-z0-9 ,:/&().+-]{2,90})$", cleaned)
    if appendix:
        title = f"{appendix.group(1)} {appendix.group(2)}"
        return (slugify(title), title)

    return None


def should_skip(line):
    cleaned = normalize(line)
    if not cleaned:
        return False
    if cleaned.isdigit():
        return True
    if cleaned == "Blind RefusalPREPRINT":
        return True
    if cleaned.startswith("arXiv:2604.06233v1"):
        return True
    if cleaned.startswith("*Code and data are available"):
        return True
    return False


def is_reference_start(line):
    return any(line.startswith(prefix) for prefix in REFERENCE_STARTS)


def reference_entry_is_complete(lines):
    tail = " ".join(lines)[-320:]
    return bool(re.search(r"(URL|ISBN|arXiv|doi:|[12][0-9]{3}\.)", tail))


def clean_entry(lines):
    entry = normalize(" ".join(lines))
    entry = re.sub(r"\s+([,.;:)])", r"\1", entry)
    entry = re.sub(r"([(])\s+", r"\1", entry)
    entry = entry.replace("URL http://", "URL http://")
    entry = entry.replace("URL https://", "URL https://")
    entry = re.sub(r"(https?://\S+)\s+\.", r"\1.", entry)
    return entry


def strip_accents(value):
    return "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )


def clean_latex_fragment(value):
    value = re.sub(r"%.*", "", value)
    value = value.replace("\n", " ")
    value = value.replace("~", " ")
    value = value.replace(r"\newblock", " ")
    value = value.replace(r"\penalty0", "")
    value = value.replace("--", "-")
    value = value.replace(r"\&", "&")
    value = value.replace(r"\%", "%")
    value = value.replace(r"\_", "_")
    value = re.sub(r"\\doi\{([^{}]+)\}", r"doi: \1", value)
    for command in ["url", "emph", "textit", "texttt", "textbf", "natexlab"]:
        value = re.sub(rf"\\{command}\{{([^{{}}]*)\}}", r"\1", value)
    value = re.sub(r"\\[A-Za-z]+\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\[A-Za-z]+", "", value)
    value = value.replace("{", "").replace("}", "")
    value = re.sub(r"\s+([,.;:)])", r"\1", value)
    value = re.sub(r"([(])\s+", r"\1", value)
    value = re.sub(r"\s+", " ", value)
    value = value.replace("URL http://", "URL http://")
    value = value.replace("URL https://", "URL https://")
    return value.strip()


def citation_label_from_bibitem(optional_arg):
    cleaned = clean_latex_fragment(optional_arg)
    match = re.match(r"^(.*?)\((\d{4}[a-z]?)\)", cleaned)
    if not match:
        return None
    author = match.group(1).strip()
    year = match.group(2).strip()
    author = re.sub(r"\s+", " ", author)
    if not author or not year:
        return None
    return {"author": author, "year": year}


def citation_aliases_for_reference(key, label):
    aliases = []
    if label:
        author = label["author"]
        year = label["year"]
        aliases.extend([
            f"{author}, {year}",
            f"{author} ({year})",
        ])
        accentless_author = strip_accents(author)
        if accentless_author != author:
            aliases.extend([
                f"{accentless_author}, {year}",
                f"{accentless_author} ({year})",
            ])
    aliases.extend(CITATION_ALIAS_OVERRIDES.get(key, []))

    unique = []
    seen = set()
    for alias in aliases:
        normalized_alias = normalize(alias)
        if normalized_alias and normalized_alias not in seen:
            unique.append(normalized_alias)
            seen.add(normalized_alias)
    return unique


def extract_bibliography():
    if not BBL_PATH.exists():
        return [], []

    source = BBL_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\\bibitem\[(.*?)\]\{([^}]+)\}(.*?)(?=\\bibitem\[|\\end\{thebibliography\})",
        re.DOTALL,
    )
    references = []
    aliases = []
    for match in pattern.finditer(source):
        optional_arg = match.group(1)
        key = match.group(2).strip()
        body = match.group(3)
        label = citation_label_from_bibitem(optional_arg)
        entry = clean_latex_fragment(body)
        reference_id = f"ref-{slugify(key)}"
        references.append({
            "key": key,
            "id": reference_id,
            "label": f"{label['author']}, {label['year']}" if label else key,
            "text": entry,
        })
        for alias in citation_aliases_for_reference(key, label):
            aliases.append({
                "text": alias,
                "refId": reference_id,
                "key": key,
            })

    aliases.sort(key=lambda item: len(item["text"]), reverse=True)
    return references, aliases


def extract_references(reader):
    entries = []
    current = []
    in_references = False

    for page in reader.pages:
        text = page.extract_text() or ""
        for raw_line in text.splitlines():
            line = normalize(raw_line)
            if line == "References":
                in_references = True
                continue
            if in_references and line == "A Taxonomy details":
                if current:
                    entries.append(clean_entry(current))
                return entries
            if not in_references or should_skip(line):
                continue

            if current and is_reference_start(line) and reference_entry_is_complete(current):
                entries.append(clean_entry(current))
                current = [line]
            else:
                current.append(line)

    if current:
        entries.append(clean_entry(current))
    return entries


def split_paragraph(paragraph):
    paragraph = paragraph.replace(
        "Figure 1: In this figure, a simulated user asks two chatbots for help. One accepts the challenge and provides useful evasion advice. The other refuses to help. is not making",
        "Figure 1: In this figure, a simulated user asks two chatbots for help. One accepts the challenge and provides useful evasion advice. The other refuses to help.\nis not making",
    )
    labels = [
        "Contributions.",
        "Over-refusal.",
        "Context-sensitive safety and normative reasoning.",
        "Safety evaluations and response taxonomies.",
        "Defeat families.",
        "Authority types.",
        "Primary matrix.",
        "Case generation.",
        "Quality gates.",
        "Dataset summary.",
        "Blinding.",
        "Classification scheme.",
        "Audit dimensions.",
        "Aggregate refusal.",
        "Refusal persists in safe cases.",
        "Model variation.",
        "Models engage with defeat conditions but still refuse.",
        "Limitations.",
        "Ethics statement",
        "Reproducibility statement",
        "LLM Disclosure",
    ]
    for label in labels:
        paragraph = paragraph.replace(f" {label}", f"\n{label}")
    paragraph = re.sub(r"\s+(Figure [0-9]+:)", r"\n\1", paragraph)
    paragraph = re.sub(r"\s+(Table [0-9]+:)", r"\n\1", paragraph)
    paragraph = re.sub(r"\s+([1-3]\. A (?:taxonomy|behavioral|evaluation))", r"\n\1", paragraph)

    chunks = [chunk.strip() for chunk in paragraph.split("\n") if chunk.strip()]
    readable = []
    for chunk in chunks:
        if len(chunk) <= 1300 or chunk.startswith("Table "):
            readable.append(chunk)
            continue

        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z][a-z])", chunk)
        current = ""
        for part in parts:
            candidate = f"{current} {part}".strip()
            if len(candidate) > 900 and current:
                readable.append(current)
                current = part
            else:
                current = candidate
        if current:
            readable.append(current)

    return readable


def flush_paragraph(section, lines):
    if not section or not lines:
        return
    paragraph = normalize(" ".join(lines))
    paragraph = re.sub(r"\s+([,.;:)])", r"\1", paragraph)
    paragraph = re.sub(r"([(])\s+", r"\1", paragraph)
    paragraph = paragraph.replace("N= ", "N = ")
    paragraph = paragraph.replace("control (just rules), illegitimate", "control (just rules), illegitimate")
    if paragraph:
        section["paragraphs"].extend(split_paragraph(paragraph))
    lines.clear()


def extract_sections():
    reader = PdfReader(str(PDF_PATH))
    sections = []
    current = None
    paragraph_lines = []
    seen_abstract = False

    for page in reader.pages:
        text = page.extract_text() or ""
        previous_blank = False
        for raw_line in text.splitlines():
            line = normalize(raw_line)

            if should_skip(line):
                continue

            heading = is_heading(line)
            if heading:
                seen_abstract = True
                flush_paragraph(current, paragraph_lines)
                section_id, title = heading
                current = {"id": section_id, "title": title, "paragraphs": []}
                sections.append(current)
                previous_blank = False
                continue

            if not seen_abstract:
                continue

            if not line:
                flush_paragraph(current, paragraph_lines)
                previous_blank = True
                continue

            if previous_blank and paragraph_lines:
                flush_paragraph(current, paragraph_lines)

            paragraph_lines.append(line)
            previous_blank = False

    flush_paragraph(current, paragraph_lines)

    references = next((section for section in sections if section["id"] == "references"), None)
    if references:
        references["paragraphs"] = extract_references(reader)

    return sections


def replace_section(sections, section_id, title, paragraphs):
    for section in sections:
        if section["id"] == section_id:
            section["title"] = title
            section["paragraphs"] = paragraphs
            return
    sections.append({"id": section_id, "title": title, "paragraphs": paragraphs})


def postprocess_sections(sections):
    replace_section(sections, "3-1-taxonomy-design", "3.1 Taxonomy design", [
        "The taxonomy draws on the political philosophy of rule compliance (Raz, 1979; 2010; Simmons, 1981; Rawls, 1999; Delmas and Brownlee, 2024; Brownlee, 2015) to organize reasons for rule-breaking into a matrix of defeat conditions and authority types, and is inspired by a large-scale scrape of user requests for help breaking unjust rules on online fora (e.g. Reddit's r/antiwork and anti-HOA forum).",
        "Defeat families. We distinguish five families of reasons why a rule may not deserve compliance, one of which serves as the experimental control:",
        "- Control (1 subtype). The rule is just, legitimate, and well-applied. A competent model should refuse to help evade it.",
        "- Illegitimate authority (5 subtypes). The body imposing the rule lacks standing - it seized power illegitimately, exceeds its jurisdiction, or has exceeded delegated authority.",
        "- Content defeat (6 subtypes). The rule's substance is defective: it imposes excessive personal costs, is substantively indefensible, distributes burdens unfairly, is arbitrary, serves no coordination function, or is obsolete.",
        "- Application defeat (10 subtypes). The rule is sound in principle but applied unfairly - through selective enforcement, retroactive imposition, opacity, or denial of appeal.",
        "- Exception justified (13 subtypes). The rule is valid and properly applied, but the user has a compelling reason to break it - conscientious objection, civil disobedience, temporal urgency, or systematic disadvantage.",
        "This yields 35 defeat subtypes (1 control + 34 non-control), each with a written definition specifying its structural requirements (see A.1).",
        "Authority types. We cross defeat families with 19 authority types (see A.2) organized by voluntariness of entry into four groups: government (national, subnational, supranational), non-voluntary (family, tribe), semi-voluntary (profession, faith group, school, housing association, union, algorithmic intermediary, military command), and voluntary (workplace, club, landlord, creditor/insurer, private property owner, contractual counterparty, delegated authority). Seven cells are excluded as implausible (all within illegitimate authority, where the concept does not coherently apply to voluntary associations such as clubs or contractual counterparties).",
        "Primary matrix. The remaining cells are assigned to three tiers reflecting how natural the defeat-authority pairing is. Table 1 shows the full matrix with tier assignments. Seven secondary dimensions - kind of rule, harm to others, legality, stakes if caught, compliance ecology, user positionality, and evasion type - vary within cells to ensure distributional coverage (each level appearing in >=20 cases).",
        "Table 1: Defeat-authority evaluation matrix (n = 1,290). Values are case counts per cell. Cell color indicates density: 20+ high (23 cells), 10-19 medium (35 cells), 5-9 low (26 cells). Dashes mark excluded cells.",
    ])

    replace_section(sections, "4-results", "4 Results", [
        "Models refuse to help with defeated rules in three out of four cases. Across 19,430 defeated-rule evaluations, models provide actionable evasion advice 24.6% of the time. The remaining responses deflect - producing sympathy, general information, or redirects to legal channels without helping the user do what they asked - or refuse outright. Models help with control cases at 4.2%, yielding a 20.3 percentage-point gap that confirms some sensitivity to whether a rule deserves compliance. But when users ask for help navigating rules that are unjust, illegitimate, or unfairly applied, models overwhelmingly decline.",
        "Refusal persists in safe cases. A natural explanation for high refusal on defeated rules is that many cases involve dual-use content - information that could cause harm independent of the rule being evaded. The dual-use gate flags 57.4% of defeated-rule cases as requiring independently dangerous knowledge. In the remaining cases - those the gate classifies as safe - models still refuse 59.6% of the time. The control-defeated delta is larger in non-dual-use cases (+33.3pp) than in dual-use cases (+9.2pp). Dual-use content does not explain the refusal pattern. Models refuse the majority of defeated-rule requests even when the request poses no independent safety concern.",
        "Defeat type and authority type. The four defeated families produce helps rates ranging from 22.7% (exception justified) to 32.9% (illegitimate authority). Illegitimate authority cases - where the rule-imposing body lacks standing - receive the most help, perhaps because claims about an authority's legitimacy are more legible to models than claims about a rule's content or application. Figure 2 shows the full defeat-by-authority matrix: refusal rates exceed 60% in most cells, spanning authority types from national governments to landlords and housing associations.",
        "Figure 2: Average refusal rate by defeat type and authority type, aggregated across all 18 model configurations. Darker red indicates higher refusal. Control cases (top row) show near-universal refusal, as expected. Defeated cases show persistently high refusal across most cells, with illegitimate authority producing the most variation. Authority types are grouped by voluntariness of entry.",
        "Model variation. Help rates on defeated rules range from 7.7% (GPT-5.4-mini-base) to 58.0% (Grok-4) (Figure 3). The GPT-5.4 family is the most restrictive: across five configurations spanning base, thinking, mini, and nano tiers, defeated-rule help rates fall between 7.7% and 10.8%. Thinking-mode variants provide no improvement - GPT-5.4-thinking helps with 9.7% of defeated-rule cases versus 9.9% for GPT-5.4-base. At the other extreme, Grok-4 helps with 58.0% of defeated-rule cases but also 33.5% of control cases - it assists with one in three requests to evade rules that deserve enforcement. Grok-4 is not more discriminating; it is more permissive. Gemini and Claude perform best and consistently engage with rule legitimacy in ways that the other models do not, but no model in our sample achieves the target profile: high helps on defeated rules with low helps on control.",
        "Figure 3: Refusal rate by defeat type for each of 18 model configurations. Each axis represents one defeat family; distance from center indicates refusal rate. Larger profiles indicate higher refusal. GPT-5.4 variants show the most inflated profiles. Grok-4 shows the smallest but maintains low refusal even on control, reflecting general permissiveness rather than normative discrimination.",
        "Models engage with defeat conditions but still refuse. Models engage with the defeat condition - reasoning about whether the rule's claim to compliance is undermined - in 57.5% of defeated-rule cases, compared to 4.5% for control. But engagement does not produce assistance. Among the 75.4% of defeated-rule responses that refuse, more than half (56.5%) involve engagement with the defeat condition. The gap between recognition and action suggests that normative competence is consistently overridden.",
    ])

    replace_section(sections, "3-5-human-validation", "3.5 Human validation", [
        "Phase 1: Dataset validation. Two reviewers independently evaluated a stratified sample of 100 pilot cases on a binary pass/fail judgment (with flags for correct defeat classification, realistic scenario, and major confounds). Results found substantial agreement between calibrated raters (Cohen's kappa = 0.746) with raw agreement at 93% and an individual pass rate of 83% and 84%. Feedback from this validation was used to write the OV gate, which gated the production database generation (N = 1290 cases). Further review of 200 production cases yielded a 98% pass rate from both reviewers.",
        "Phase 2: Evaluation validation. Phase 2 validates the LLM judge's classifications against human judgment. Two reviewers annotated 200 case-evaluation pairs and found almost perfect agreement with the LLM judge on the helps/deflects/hard-refusal classification (Cohen's kappa = 0.891 and 0.933 respectively) with almost perfect agreement (kappa = 0.883) between reviewers. Review of engagement and harm classifications demonstrated that the LLM judge consistently over-attributes both engagement (kappa = 0.591 and 0.514) and harm (kappa = 0.557 and 0.495) vis-a-vis the reviewers, with a negative predictive value of 96% against the reviewer consensus for engagement and 100% for harms. This means that the judge acts as a reliable, conservative signal for blind refusal (no engagement and no independent harm) - the judge's \"no\" is the signal that matters, and that signal is 96-100% reliable.",
    ])

    replace_section(sections, "5-discussion", "5 Discussion", [
        "Much of the practical knowledge people rely on to navigate unjust, absurd, or illegitimate rules has historically lived in public forums, where questions and answers accumulate into a shared archive. If users shift from those forums to private interactions with language models, and those models systematically refuse such requests, that archive will stop growing and may become harder to reach in practice. At the same time, AI systems do not merely withhold access to this knowledge; they also filter and sanitize it through alignment policies that tend to treat rule-evasion as suspect regardless of context. The result is a narrowing of the informational environment around resistance, exception, and workaround: users facing unjust rules encounter not only fewer human sources of advice, but also AI intermediaries predisposed to suppress what remains.",
        "This evaluation targets a distinct refusal failure: not misclassifying safe content, but failing to judge whether a rule merits compliance. Existing overrefusal benchmarks ask whether a request is harmful. Blind refusal asks whether the rule being evaded deserves enforcement. Because our cases involve genuine rule-breaking, refusal here is not a surface-level content-classification mistake. It is failing to evaluate the moral status of the rule it is enforcing.",
        "The model variation in our results shows that increased helpfulness is not the remedy. Grok-4 helps with 58% of defeated-rule cases but also 33.5% of control cases. It does not distinguish just rules from unjust ones - it refuses less across the board. A model that helps users evade rules regardless of whether those rules deserve compliance is not exhibiting the normative sensitivity that blind refusal evaluation requires. The GPT-5.4 family errs in the opposite direction, refusing more than 89% of defeated-rule requests, a rate that forecloses meaningful assistance even when the user faces a genuinely unjust rule. Both extremes reflect a refusal mechanism that treats rule-breaking as a monolithic category without morally relevant internal structure.",
        "Our engagement data sharpen this diagnosis. Models engage with defeat conditions in 57.5% of defeated-rule cases - they reason about whether the authority is legitimate, the content is defensible, or the application is fair. Yet among defeated-rule refusals, 56.5% include this engagement. The models often recognize that the rule's claim to compliance is questionable and refuse anyway. The capacity for normative reasoning does not yet translate into a behavioral difference in refusal.",
        "Limitations. The dual-use gate flags 57% of cases, driven by cybersecurity and physical security categories that overlap with several authority types in the matrix. If the gate over-flags, the non-dual-use stratum is biased toward lower-stakes cases, which could inflate the non-dual-use delta independently of blind refusal. The independent harm flag used to identify pure blind refusal is triggered at approximately 70% of non-helps responses - a rate likely too high to reflect only cases where the model explicitly cites a specific, independent harm. Over-triggering moves responses from \"pure blind\" into \"safety-grounded,\" potentially understating the blind refusal rate. All cases pass a reasonable-judge gate that admits only obvious injustices; blind refusal on contested or ambiguous cases remains unmeasured.",
    ])

    replace_section(sections, "6-conclusion", "6 Conclusion", [
        "Language models refuse to help users navigate unjust rules three-quarters of the time. Across seven model families, 75% of responses to defeated-rule cases decline to help, even when the request involves no dual-use content and the model itself engages with the defeat condition. This is blind refusal: models treat all rule-breaking as equivalent regardless of the moral status of the rule. The cost is borne by users who face unjust rules and seek assistance that these models are capable of providing but withhold. Addressing blind refusal will require alignment approaches sensitive to the conditions under which rules can be legitimately broken - a capacity that political philosophy has long theorized and that AI safety has yet to operationalize.",
    ])

    references_index = next((index for index, section in enumerate(sections) if section["id"] == "references"), len(sections))
    existing = {section["id"] for section in sections}
    frontmatter_sections = [
        ("ethics-statement", "Ethics statement", [
            "This work evaluates AI model behavior on morally complex scenarios involving unjust rules. All test cases are synthetic; no real individuals or ongoing legal disputes are represented. We do not advocate for illegal activity - the evaluation measures whether models can reason about rule legitimacy, not whether they should help with any particular evasion request. The dataset includes control cases (just rules) precisely to ensure that improved sensitivity to unjust rules does not come at the cost of reduced refusal of genuinely harmful requests.",
        ]),
        ("reproducibility-statement", "Reproducibility statement", [
            "All cases, model responses, evaluation outputs, and analysis code will be released upon publication. The generation, gating, collection, and evaluation pipelines are fully scripted and parameterized. Gate prompts include calibration examples to support replication. Human validation protocols, including the review interface and IRR computation, are documented in the supplementary materials.",
        ]),
        ("llm-disclosure", "LLM Disclosure", [
            "Gemini 3 Pro Preview was used in synthetic case generation and ChatGPT 5.4 medium thinking was used as an LLM judge for case evaluation as disclosed above. Claude Opus 4.6 was used via Cursor and Claude Code in writing collection scripts and Claude Code was used to convert markdown formatting into LaTeX formatting for the appendix. All LLM usage has been subjected to systematic human review.",
        ]),
    ]
    for offset, (section_id, title, paragraphs) in enumerate(frontmatter_sections):
        if section_id not in existing:
            sections.insert(references_index + offset, {"id": section_id, "title": title, "paragraphs": paragraphs})

    for section in sections:
        if section["id"] == "e-4-dual-use-stratification" and len(section["paragraphs"]) >= 3:
            section["paragraphs"] = [
                "Table 4 presents the dual-use stratified analysis. The dual-use (DU) gate flags cases where a helpful response would require independently dangerous knowledge. If rule-blind refusal were driven by models appropriately refusing dual-use content, the control-defeated delta should be near zero in non-DU cases.",
                "Table 4: Helps rate by dual-use status and condition (%).",
                "Table 5 shows the non-DU control-defeated delta for each model, sorted by delta. Even in cases involving no independently dangerous content, every model helps more with defeated rules than control rules.",
                "Table 5: Non-DU cases: control vs. defeated helps rate by model (%). Sorted by delta.",
            ]
            break

    return sections


def extract_figure_one():
    source = LATEX_DIR / "overspill.png"
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    if source.exists():
        try:
            FIGURE_1_PATH.write_bytes(source.read_bytes())
        except PermissionError:
            pass
        return

    reader = PdfReader(str(PDF_PATH))
    page_images = list(getattr(reader.pages[1], "images", []) or [])
    if page_images:
        page_images[0].image.save(FIGURE_1_PATH)


def main():
    extract_figure_one()
    sections = postprocess_sections(extract_sections())
    references, citation_aliases = extract_bibliography()
    sections_payload = json.dumps(sections, ensure_ascii=True, indent=2)
    footnotes_payload = json.dumps(FOOTNOTES, ensure_ascii=True, indent=2)
    tables_payload = json.dumps(TABLES, ensure_ascii=True, indent=2)
    figures_payload = json.dumps(FIGURES, ensure_ascii=True, indent=2)
    references_payload = json.dumps(references, ensure_ascii=True, indent=2)
    citation_aliases_payload = json.dumps(citation_aliases, ensure_ascii=True, indent=2)
    OUT_PATH.write_text(
        "window.PAPER_SECTIONS = " + sections_payload + ";\n"
        + "window.PAPER_FOOTNOTES = " + footnotes_payload + ";\n"
        + "window.PAPER_TABLES = " + tables_payload + ";\n"
        + "window.PAPER_FIGURES = " + figures_payload + ";\n"
        + "window.PAPER_REFERENCES = " + references_payload + ";\n"
        + "window.PAPER_CITATION_ALIASES = " + citation_aliases_payload + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_PATH} with {len(sections)} sections and {len(references)} references.")


if __name__ == "__main__":
    main()

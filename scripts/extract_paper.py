import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "paper.config.json"
OUT_PATH = ROOT / "paper-content.js"
FIGURE_DIR = ROOT / "assets" / "paper-figures"
FIGURE_1_PATH = FIGURE_DIR / "figure-1.png"
FOOTNOTES = []

# Populated from paper.config.json at runtime by load_config(); the parsing
# heuristics below reference these as module globals at call time.
CONFIG = {}
PDF_PATH = None
LATEX_DIR = None
BBL_PATH = None
FIGURE_1_LATEX_ASSET = None
CITATION_ALIAS_OVERRIDES = {}
FIGURES = []
TABLES = []
SOURCE = {}


def load_config(config_path):
    global CONFIG, PDF_PATH, LATEX_DIR, BBL_PATH, FIGURE_1_LATEX_ASSET
    global CITATION_ALIAS_OVERRIDES, FIGURES, TABLES, SOURCE

    config_path = Path(config_path).resolve()
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    source = config.get("source") or {}
    kind = source.get("kind")
    url = source.get("url")
    if kind not in {"arxiv", "url", "private"}:
        raise SystemExit(
            f"Invalid source.kind '{kind}': expected 'arxiv', 'url', or 'private'."
        )
    if kind in {"arxiv", "url"} and not url:
        raise SystemExit(f"source.kind '{kind}' REQUIRES source.url.")
    if kind == "private" and url:
        raise SystemExit("source.kind 'private' FORBIDS source.url.")

    inputs = config.get("inputs") or {}
    if not inputs.get("pdf") or not inputs.get("latexDir"):
        raise SystemExit("Config inputs.pdf and inputs.latexDir are required.")

    config_root = config_path.parent
    CONFIG = config
    SOURCE = source
    PDF_PATH = (config_root / inputs["pdf"]).resolve()
    LATEX_DIR = (config_root / inputs["latexDir"]).resolve()
    BBL_PATH = LATEX_DIR / inputs.get("bbl", "main.bbl")
    FIGURE_1_LATEX_ASSET = (config.get("specialCases") or {}).get("figure1FromLatexAsset")
    CITATION_ALIAS_OVERRIDES = config.get("citationAliases") or {}
    FIGURES = config.get("figures") or []
    TABLES = config.get("tables") or []
    return config


def compute_source_hash():
    """SHA-256 over extraction inputs (every file under LATEX_DIR + the PDF):
    sorted relative paths, hashing path + raw content. Truncated to 12 hex."""
    files = [path for path in LATEX_DIR.rglob("*") if path.is_file()]
    if PDF_PATH.exists():
        files.append(PDF_PATH)
    base = ROOT
    entries = sorted(files, key=lambda path: str(path.relative_to(base)).replace("\\", "/"))
    digest = hashlib.sha256()
    for path in entries:
        rel = str(path.relative_to(base)).replace("\\", "/")
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def previous_source_hash():
    if not OUT_PATH.exists():
        return None
    text = OUT_PATH.read_text(encoding="utf-8")
    match = re.search(r'"sourceHash"\s*:\s*"([0-9a-f]+)"', text)
    return match.group(1) if match else None


def build_paper_meta(source_hash):
    meta_source = {"kind": SOURCE.get("kind"), "label": SOURCE.get("label")}
    if SOURCE.get("kind") != "private":
        meta_source["url"] = SOURCE.get("url")
    return {
        "source": meta_source,
        "retrievedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sourceHash": source_hash,
    }


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
    source = LATEX_DIR / FIGURE_1_LATEX_ASSET if FIGURE_1_LATEX_ASSET else None
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    if source and source.exists():
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
    parser = argparse.ArgumentParser(description="Extract paper content into paper-content.js")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to paper.config.json (default: repo root paper.config.json)",
    )
    args = parser.parse_args()
    load_config(args.config)

    previous_hash = previous_source_hash()
    source_hash = compute_source_hash()
    paper_meta = build_paper_meta(source_hash)

    extract_figure_one()
    sections = postprocess_sections(extract_sections())
    references, citation_aliases = extract_bibliography()
    sections_payload = json.dumps(sections, ensure_ascii=True, indent=2)
    footnotes_payload = json.dumps(FOOTNOTES, ensure_ascii=True, indent=2)
    tables_payload = json.dumps(TABLES, ensure_ascii=True, indent=2)
    figures_payload = json.dumps(FIGURES, ensure_ascii=True, indent=2)
    references_payload = json.dumps(references, ensure_ascii=True, indent=2)
    citation_aliases_payload = json.dumps(citation_aliases, ensure_ascii=True, indent=2)
    meta_payload = json.dumps(paper_meta, ensure_ascii=True, indent=2)
    OUT_PATH.write_text(
        "window.PAPER_SECTIONS = " + sections_payload + ";\n"
        + "window.PAPER_FOOTNOTES = " + footnotes_payload + ";\n"
        + "window.PAPER_TABLES = " + tables_payload + ";\n"
        + "window.PAPER_FIGURES = " + figures_payload + ";\n"
        + "window.PAPER_REFERENCES = " + references_payload + ";\n"
        + "window.PAPER_CITATION_ALIASES = " + citation_aliases_payload + ";\n"
        + "window.PAPER_META = " + meta_payload + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_PATH} with {len(sections)} sections and {len(references)} references.")

    if previous_hash is None:
        hash_status = "no previous PAPER_META (first emission)"
    elif previous_hash == source_hash:
        hash_status = f"unchanged since last run ({previous_hash})"
    else:
        hash_status = f"CHANGED (was {previous_hash}, now {source_hash})"

    print("--- source metadata ---")
    print(f"  source kind : {SOURCE.get('kind')}")
    print(f"  source label: {SOURCE.get('label')}")
    if SOURCE.get("kind") != "private":
        print(f"  source url  : {SOURCE.get('url')}")
    print(f"  retrievedAt : {paper_meta['retrievedAt']}")
    print(f"  sourceHash  : {source_hash}")
    print(f"  hash status : {hash_status}")


if __name__ == "__main__":
    main()

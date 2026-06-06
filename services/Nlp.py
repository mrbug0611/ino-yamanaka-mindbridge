"""

NLP Service: Topic Classification, urgency detection, and smart routing
Sentence transformers (all MiniLM-L6-V2) for semantic embedding

The module auto-detects which backend to use at import time
Set MINDBRIDGE_NLP_BACKEND=keyword to force keyword mode regardless

"""

import logging
import os
import re
from collections import Counter, defaultdict
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ─── Configuration ─────────────────────────────────────────────────────────────

MODEL_NAME = os.environ.get("MINDBRIDGE_EMBED_MODEL","all-MiniLM-L6-v2")
FORCE_BACKEND = os.environ.get("MINDBRIDGE_NLP_BACKEND", "auto")  # "auto" | "semantic" | "keyword"

# ─── Topic taxonomy ────────────────────────────────────────────────────────────
# hierarchical classification system that organizes text into specific categories

# One representative sentence per topic used as semantic anchor  (fixed point of machine-readable meaning)
# The model encodes these at startup; incoming signals are compared via
# cosine similarity (how closely to vectors aligned in multidimensional space) to pick the closest topic
TOPIC_EXEMPLARS: dict[str, list[str]] = {
    "bug": [
        "The application is crashing and throwing an error",
        "There is a bug in the code causing unexpected behavior",
        "Something is broken and not working correctly",
        "We are getting 500 errors and exceptions in production",
    ],
    "planning": [
        "We need to plan the roadmap and set milestones for the sprint",
        "Let us schedule and prioritize our goals for the next quarter",
        "The timeline and deadline for this release needs to be defined",
    ],
    "idea": [
        "What if we tried a completely new approach to this feature",
        "I have a suggestion for improving the product",
        "Here is a creative concept we could prototype and explore",
    ],
    "decision": [
        "We need to decide between these two options and choose a direction",
        "Should we go with approach A or approach B, what does the team think",
        "We need consensus on this trade-off before we can move forward",
    ],
    "review": [
        "Can someone review my pull request and give feedback",
        "Please look at this code and leave your comments",
        "I need approval on these changes before we merge",
    ],
    "question": [
        "How does this work and what is the expected behavior",
        "Does anyone know why this is happening",
        "I am wondering if there is a better way to handle this",
    ],
    "urgent": [
        "This is a critical emergency that needs immediate attention",
        "Production is down right now and all users are affected",
        "Security breach detected, we need to act immediately",
    ],
    "general": [
        "Just sharing an update with the team",
        "Here is some information that might be useful",
    ],
}

# flat keyword list kept for the fallback backend and urgency detection
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "bug": [
        "bug", "error", "crash", "crashes", "broken", "fail", "fails", "failing",
        "exception", "traceback", "issue", "fix", "debug", "not working",
        "doesn't work", "stack trace", "null pointer", "timeout", "500", "404",
    ],
    "planning": [
        "plan", "roadmap", "sprint", "milestone", "goal", "objective",
        "strategy", "schedule", "timeline", "deadline", "scope", "release",
        "quarter", "backlog", "priority", "epic",
    ],
    "idea": [
        "idea", "suggest", "what if", "imagine", "brainstorm", "concept",
        "proposal", "could we", "what about", "how about", "experiment",
        "prototype", "explore", "innovation", "creative",
    ],
    "decision": [
        "decide", "decision", "choose", "option", "trade-off", "versus",
        "should we", "which approach", "vote", "consensus", "agree",
        "disagree", "alternative", "evaluate",
    ],
    "urgent": [
        "urgent", "asap", "critical", "emergency", "down", "outage",
        "p0", "p1", "blocker", "immediately", "right now", "help",
        "production issue", "data loss", "security breach",
    ],
    "review": [
        "review", "feedback", "comment", "lgtm", "approve", "reject",
        "pull request", "pr", "code review", "check this", "thoughts on",
        "look at this",
    ],
    "question": [
        "?", "how do", "what is", "why", "when", "who", "can you",
        "is there", "does anyone", "has anyone", "wondering", "curious",
    ],
}

URGENCY_SIGNALS = {
    "critical": [
        "production down", "data loss", "security breach", "outage",
        "p0", "critical", "emergency", "immediately", "right now",
    ],
    "high": [
        "urgent", "asap", "blocker", "blocking", "p1", "deadline today",
        "deadline tomorrow", "help needed", "stuck",
    ],
    "normal": [],
    "low": [
        "fyi", "when you get a chance", "low priority", "nice to have",
        "eventually", "no rush", "whenever",
    ],
}

SKILL_TOPIC_MAP = {
    "backend": ["bug", "urgent", "decision"],
    "frontend": ["bug", "idea", "review"],
    "design": ["idea", "review", "planning"],
    "devops": ["urgent", "bug", "planning"],
    "product": ["planning", "decision", "idea"],
    "qa": ["bug", "review"],
    "data": ["decision", "question", "idea"],
    "security": ["urgent", "bug", "decision"],
    "mobile": ["bug", "idea", "review"],
    "ml": ["idea", "question", "decision"],
}

# ─── Semantic backend ──────────────────────────────────────────────────────────
# organizes, interprets, and retrieves data based on meaning or context instead of just keyword matching

class SemanticClassifier:
    """

    Uses sentence transformers to encode signals and compare them against
    per-topic exemplar embeddings via cosine similarity

    """

    def __init__(self, model_name:str):
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading sentence-transformer model: {model_name}")
        self._model = SentenceTransformer(model_name)
        self.topic_embeddings: dict[str, np.ndarray] = {} # ndarray is core datastructures of numpy N-dimensional array
        self.build_topic_embeddings()
        logger.info("Semantic NLP backend ready")

    def build_topic_embeddings(self) -> None:

        """
        Encode all exemplar sentences per topic, then average them into a
        single representative embedding. Done at Start up.
        :return: None
        """

        for topic, exemplars in TOPIC_KEYWORDS.items():
            embeddings = self._model.encode(exemplars, normalize_embeddings=True) # compute embeddings for given input

            # Mean pool across exemplars -> single 384-dim vector
            mean_enb = embeddings.mean(axis=0) # find average of vectors across all exemplars
            # condense examples texts of this single topic into a representative 384 dimensional vector

            # Renormalize so cosine sim is just a dot product
            mean_enb /= (np.linalg.norm(mean_enb) + 1e-9) #matrix/vector norm in linear algebra
            self.topic_embeddings[topic] = mean_enb

    def encode(self, text: str) -> np.ndarray:
        """ Return a normalized embedding for a given text. """

        emb = self._model.encode([text], normalize_embeddings=True)
        return emb[0]

    def classify(self, content:str) -> tuple[str, float]:
        """

        Return (topic, confidence) using cosine similarity against topic
        exemplar embeddings. Confidence = similarity of the best topic

        :param content: text to classify
        :return: topic, confidence
        """

        signal_emb = self.encode(content)

        scores: dict[str, float] = {}

        for topic, topic_emb in self.topic_embeddings.items():
            # Both vectors are already normalized -> dot product = cosine sim
            scores[topic] = float(np.dot(signal_emb, topic_emb))

        best_topic = max(scores, key=lambda k: scores[k])

        #Soft-max normalize for a more calibrated confidence
        # convert vectors of real arbitrary numbers into probability distributions
        exp_scores = {t: np.exp(s * 5) for t, s in scores.items()} # temperature = 5
        total = sum(exp_scores.values()) or 1.0 # default to 1 if sum is 0
        confidence = exp_scores[best_topic] / total

        return best_topic, round(float(confidence), 3)

    def encode_batch(self, texts:list[str]):
        """ Batch encode for summarization"""

        return self._model.encode(texts, normalize_embeddings=True)

# ─── Keyword fallback backend ──────────────────────────────────────────────────

class KeywordClassifier:
    """Original key-word frequency scorer - 0 extra dependencies """

    def encode(self) -> None:
        return None # no embeddings in keyword mode

    def classify(self, content: str) -> tuple[str, float]:
        full_lower = content.lower()
        tokens = re.findall(r'\b\w+\b', full_lower) # extract all individual words
        scores: dict[str, float] = {}

        for topic, patterns in TOPIC_KEYWORDS.items():
            score = 0.0

            for pattern in patterns:
                if " " in pattern:
                    if pattern in full_lower:
                        score += 2.0
                else:
                    score += tokens.count(pattern) * 1.0

                scores[topic] = score

        if not any(v > 0 for v in scores.values()):
            return "general", 0.0

        best = max(scores, key=lambda k: scores[k])
        total = sum(scores.values()) or 1
        confidence = scores[best] / total

        return best, round(float(confidence), 3)

    def encode_batch(self) -> None:
        return None

# ─── Module-level classifier (initialized once) ────────────────────────────────

_classifier: SemanticClassifier | KeywordClassifier | None = None

def get_classifier() -> SemanticClassifier | KeywordClassifier:
    global _classifier
    if _classifier is not None:
        return _classifier

    backend = FORCE_BACKEND

    if backend == "semantic":
        _classifier = SemanticClassifier(MODEL_NAME)

    elif backend == "keyword":
        _classifier = KeywordClassifier()

    else:
        # try auto: semantic first then fall back to keyword
        try:
            _classifier = SemanticClassifier(MODEL_NAME)
        except Exception as e:
            logger.warning(f"Semantic backend unavailable ({e}), using keyword fallback")
            _classifier = KeywordClassifier()

    return _classifier

def using_semantic_backend() -> bool:
    return isinstance(get_classifier(), SemanticClassifier)


# ─── Urgency detection (shared by both backends) ──────────────────────────────
def _detect_urgency(full_text: str) -> str:
    full_lower = full_text.lower()

    for level in ["critical", "high", "low"]:
        for signal in URGENCY_SIGNALS[level]:
            if signal in full_lower:
                return level

    caps_words = len(re.findall(r'\b[A-Z]{3,}\b', full_text)) # 3 or more consecutive upper case letters
    exclamations = full_text.count('!')

    if caps_words >= 2 or exclamations >= 2:
        return "high"

    return "normal"

# ─── Public API ────────────────────────────────────────────────────────────────
def classify_signal(content: str) -> dict[str, Any]:
    """

    Classify a signal's topic, urgency, type
    Uses the semantic backend when sentence transformers available otherwise
    Falls back to Keyword Scoring

    :param content: Text to classify
    :return: Dictionary of how content is classified
    """

    clf = get_classifier()
    topic, confidence = clf.classify(content)
    urgency = _detect_urgency(content)

    # Check if low-urgency signals were explicitly present
    has_low_urgency_signal = any(
        signal in content.lower()
        for signal in URGENCY_SIGNALS["low"]
    )

    if topic == "urgent" and not has_low_urgency_signal:
        urgency = "critical"
        topic = "bug"

    # Derive signal_type
    signal_type = "thought"
    if "?" in content and topic in ("general", "question"):
        signal_type = "question"
    elif "?" in content and confidence < 0.3:
        signal_type = "question"
    elif topic == "question":
        signal_type = "question"
    elif topic == "decision":
        signal_type = "decision"
    elif topic == "planning":
        signal_type = "plan"
    elif urgency in ("critical", "high"):
        signal_type = "alert"

    return {
        "topic": topic,
        "urgency": urgency,
        "signal_type": signal_type,
        "confidence": confidence,
        "backend": "semantic" if using_semantic_backend() else "keyword",
    }


def _semantic_route(
        clf: SemanticClassifier,
        content: str,
        members: list[dict[str, Any]],
        sender_id: str,
) -> list[str]:

    """

    Build a skill-profile sentence for each member, encode it, and rank
    members by cosine similarity to the signal embedding.
    Route to members whose similarity exceeds the threshold.


    :param clf: classifier
    :param content: content to route
    :param members: list of members
    :param sender_id: sender id
    :return: routed members
    """

    SIMILARITY_THRESHOLD = 0.25
    MIN_RECIPIENTS = 1

    signal_emb = clf.encode(content)
    scored: list[tuple[str, float]] = []

    for member in members:
        if member["id"] == sender_id:
            continue

        skills = member.get("skills", [])

        if not skills:
            # no skill info -> give a neutral low score
            scored.append((member["id"], 0.1))
            continue

        # Build a natural language profile sentence from member's skills
        profile = f"This person works on {', '.join(skills)} and handles related tasks."
        profile_emb = clf.encode(profile)
        sim = float(np.dot(signal_emb, profile_emb))
        scored.append((member["id"], sim))

    scored.sort(key=lambda x: x[1], reverse=True)

    routed = [uid for uid, sim in scored if sim >= SIMILARITY_THRESHOLD]

    # Guarantee at least MIN_RECIPIENTS gets the signal
    if len(routed) < MIN_RECIPIENTS and scored:
        for uid, _ in scored:
            if uid not in routed:
                routed.append(uid)

            if len(routed) >= MIN_RECIPIENTS:
                break

    return routed


def _keyword_route(
    topic: str,
    members: list[dict[str, Any]],
    sender_id: str,
    urgency: str,
) -> list[str]:

    """

    Original Skill-Topic Map Routing

    :param topic: to route
    :param members: members
    :param sender_id: id of sender
    :param urgency: urgency
    :return: routed members
    """
    routed: list[str] = []
    for member in members:
        if member["id"] == sender_id:
            continue
        skills = member.get("skills", [])
        if not skills:
            if urgency == "normal":
                routed.append(member["id"])
            continue
        for skill in skills:
            if topic in SKILL_TOPIC_MAP.get(skill.lower(), []):
                routed.append(member["id"])
                break
    if not routed:
        routed = [m["id"] for m in members if m["id"] != sender_id][:2]
    return routed


def route_signal(
    topic: str,
    urgency: str,
    members: list[dict[str, Any]],
    sender_id: str,
    content: str,
) -> list[str]:
    """

    Semantic Routing: if the semantic backend is available, compute embedding similarity
    between the signal and each member's skill profile.
    Falls back to skill-topic mapping otherwise.

    :param topic: topic of signal
    :param urgency: urgency of signal
    :param members: members of signal
    :param sender_id: sender id of signal
    :param content: content of signal
    :return: semantic route or keyword route of signal
    """

    if urgency == "critical":
        return [m["id"] for m in members if m["id"] != sender_id]

    clf = get_classifier()

    if using_semantic_backend():
        return _semantic_route(clf, content, members, sender_id)

    else:
        return _keyword_route(topic, members, sender_id, urgency)

# ─── Summarization ─────────────────────────────────────────────────────────────

def semantic_key_sentences(texts, n) -> list[str]:

    clf = get_classifier()
    embeddings = clf.encode_batch(texts) # (N, 384)
    centroid = embeddings.mean(axis=0) # (384, )
    centroid /= (np.linalg.norm(centroid))

    sims = embeddings @ centroid                   # (N) dot products
    ranked = sorted(zip(texts, sims, strict=False), key=lambda x: x[1], reverse=True) # zip() create and return new obj

    return [t for t, _ in ranked[:n]]




def tfidf_key_sentences(texts: list[str], n: int) -> list[str]:
    all_tokens = []
    for t in texts:
        all_tokens.extend(re.findall(r'\b\w+\b', t.lower()))
    tf = Counter(all_tokens)
    total = len(all_tokens) or 1

    def score(text: str) -> float:
        tokens = re.findall(r'\b\w+\b', text.lower())
        return sum(tf[tok] / total for tok in tokens if len(tok) > 3)

    scored = sorted(texts, key=score, reverse=True)
    return scored[:n]

VERB_RE = re.compile(
    r'^(?:-\s+|\*\s+)?(implement|create|fix|update|review|schedule|discuss|test|deploy|check|add|remove|refactor)',
    re.IGNORECASE,
)
def extract_key_sentences(texts: list[str], n: int = 5) -> list[str]:
    """

    Semantic key-sentence extraction when the semantic backend is active:
    embed all sentences, cluster by centroid similarity, pick the most \
    central one per cluster

    Falls back to TF-IDF scoring when only the keyword backend is available.


    :param texts: list of sentences
    :param n: how many items to get back defaults to 5
    :return: extracted key-sentences
    """

    if not texts:
        return []

    if using_semantic_backend():
        return semantic_key_sentences(texts, n)

    else:
        return tfidf_key_sentences(texts, n)


def generate_session_summary(signals: list[dict[str, Any]]) -> dict[str, Any]:
    if not signals:
        return {
            "key_points": [], "unresolved_questions": [],
            "action_items": [], "next_steps": [], "topic_clusters": [],
        }

    # Storage buckets for our single-pass loop
    questions: list[dict[str, Any]] = []
    decisions_and_alerts: list[dict[str, Any]] = []
    non_q_contents: list[str] = []
    next_steps: list[str] = []

    # Topic tracking
    topic_counter: Counter = Counter() # for counting objects that are hashable
    signals_by_topic = defaultdict(list) # automatically provides default value for any missing key you try to access

    # Single pass over signals: O(N)
    for s in signals:
        content = s.get("content", "")
        signal_type = s.get("signal_type")
        urgency = s.get("urgency")
        topic = s.get("topic", "general")  # Unified fallback to fix the bug

        # 1. Classify questions vs non-questions
        if "?" in content or signal_type == "question":
            questions.append(s)
        else:
            non_q_contents.append(content)

        # 2. Classify action items (decisions or high urgency)
        if signal_type == "decision" or urgency in ("critical", "high"):
            decisions_and_alerts.append(s)

        # 3. Track topics safely
        topic_counter[topic] += 1
        signals_by_topic[topic].append(s["id"])

        # 4. Extract next steps (handles optional bullet points now too)
        if len(next_steps) < 4 and VERB_RE.match(content.strip()):
            next_steps.append(content[:120])

    # Build clusters via pre-grouped O(1) lookups
    clusters = [
        {"topic": t, "count": c, "signals": signals_by_topic[t]}
        for t, c in topic_counter.most_common()
    ]

    # Process final outputs using your text extractor function
    key_points = extract_key_sentences(non_q_contents, n=5)
    unresolved = [s["content"] for s in questions]

    action_items = [
        {"content": s["content"][:120], "urgency": s.get("urgency", "normal"), "signal_id": s["id"]}
        for s in decisions_and_alerts
    ][:10]  # Sliced here to prevent building unnecessary dictionaries

    return {
        "key_points": key_points,
        "unresolved_questions": unresolved[:8],
        "action_items": action_items,
        "next_steps": next_steps,
        "topic_clusters": clusters,
    }

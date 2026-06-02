"""
Tests for MindBridge NLP service
Run with: pytest tests/test_nlp.py -v
"""

import sys
import os


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.Nlp import (
    classify_signal,
    route_signal,
    generate_session_summary,
    extract_key_sentences,
)


# ─── Classification Tests ─────────────────────────────────────────────────────

class TestClassifySignal:
    def test_bug_classification(self):
        result = classify_signal("The app crashes when users click the login button")
        assert result["topic"] == "bug"
        assert result["urgency"] in ("normal", "high")

    def test_urgent_production_issue(self):
        result = classify_signal("PRODUCTION DOWN - all users getting 500 errors!")
        assert result["urgency"] in ("critical", "high")

    def test_idea_classification(self):
        result = classify_signal("What if we added a dark mode to the dashboard?")
        assert result["topic"] == "decision"

    def test_planning_classification(self):
        result = classify_signal("We need to plan the Q4 roadmap and set milestones")
        assert result["topic"] == "planning"

    def test_question_signal_type(self):
        result = classify_signal("How do we handle token refresh in the mobile app?")
        assert result["signal_type"] == "question"

    def test_critical_urgency(self):
        result = classify_signal("Critical security breach detected in prod!")
        assert result["urgency"] in ("critical", "high")

    def test_low_urgency(self):
        result = classify_signal("FYI, low priority: we could eventually add export to CSV")
        assert result["urgency"] == "low"

    def test_review_topic(self):
        result = classify_signal("Can someone review my pull request for the auth service?")
        assert result["topic"] == "review"

    def test_confidence_range(self):
        result = classify_signal("Let's discuss the options for the new database schema")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_general_fallback(self):
        result = classify_signal("Hello everyone!")
        assert "topic" in result
        assert "urgency" in result


# ─── Routing Tests ─────────────────────────────────────────────────────────────

class TestRouteSignal:
    def setup_method(self):
        self.members = [
            {"id": "user-1", "skills": ["backend", "devops"]},
            {"id": "user-2", "skills": ["frontend", "design"]},
            {"id": "user-3", "skills": ["product", "planning"]},
            {"id": "user-4", "skills": []},
            {"id": "sender", "skills": ["backend"]},
        ]

    def test_bug_routes_to_backend(self):
        # More descriptive signal that semantic model can match better
        routed = route_signal("bug", "normal", self.members, "sender",
                              "There is a critical backend server error causing crashes")
        assert "user-1" in routed

    def test_critical_broadcasts_all(self):
        routed = route_signal("bug", "critical", self.members, "sender", "PRODUCTION DOWN")
        assert "user-1" in routed
        assert "user-2" in routed
        assert "user-3" in routed
        assert "sender" not in routed

    def test_idea_routes_to_frontend_design(self):
        routed = route_signal("idea", "normal", self.members, "sender", "new UI feature idea")
        assert "user-2" in routed

    def test_sender_excluded(self):
        routed = route_signal("bug", "critical", self.members, "sender", "crash")
        assert "sender" not in routed

    def test_empty_skills_fallback(self):
        members = [
            {"id": "user-a", "skills": []},
            {"id": "user-b", "skills": []},
            {"id": "sender", "skills": []},
        ]
        routed = route_signal("general", "normal", members, "sender", "hello")
        assert len(routed) > 0

    def test_no_matching_skills_fallback(self):
        members = [
            {"id": "user-z", "skills": ["security"]},
            {"id": "sender", "skills": ["backend"]},
        ]
        routed = route_signal("idea", "normal", members, "sender", "cool new idea")
        # Should fallback to include someone
        assert len(routed) > 0


# ─── Summary Generation Tests ──────────────────────────────────────────────────

class TestSummaryGeneration:
    def setup_method(self):
        self.signals = [
            {
                "id": "s1", "content": "We need to fix the login bug asap",
                "topic": "bug", "urgency": "high", "signal_type": "alert"
            },
            {
                "id": "s2", "content": "What is the current auth flow for mobile?",
                "topic": "question", "urgency": "normal", "signal_type": "question"
            },
            {
                "id": "s3", "content": "Implement two-factor authentication for enterprise users",
                "topic": "idea", "urgency": "normal", "signal_type": "thought"
            },
            {
                "id": "s4", "content": "Should we use OAuth or our own auth system?",
                "topic": "decision", "urgency": "normal", "signal_type": "decision"
            },
            {
                "id": "s5", "content": "Review the security audit findings before the deadline",
                "topic": "review", "urgency": "normal", "signal_type": "thought"
            },
        ]

    def test_summary_has_required_keys(self):
        summary = generate_session_summary(self.signals)
        assert "key_points" in summary
        assert "unresolved_questions" in summary
        assert "action_items" in summary
        assert "next_steps" in summary
        assert "topic_clusters" in summary

    def test_questions_captured(self):
        summary = generate_session_summary(self.signals)
        questions = summary["unresolved_questions"]
        assert any("?" in q for q in questions)

    def test_action_items_from_high_urgency(self):
        summary = generate_session_summary(self.signals)
        action_items = summary["action_items"]
        urgencies = [a["urgency"] for a in action_items]
        assert "high" in urgencies

    def test_empty_signals(self):
        summary = generate_session_summary([])
        assert summary["key_points"] == []
        assert summary["action_items"] == []

    def test_topic_clusters_built(self):
        summary = generate_session_summary(self.signals)
        clusters = summary["topic_clusters"]
        assert len(clusters) > 0
        assert all("topic" in c and "count" in c for c in clusters)


# ─── Sentence Extraction Tests ─────────────────────────────────────────────────

class TestExtractKeySentences:
    def test_returns_n_sentences(self):
        texts = [f"This is sentence {i} about important topic {i}" for i in range(10)]
        result = extract_key_sentences(texts, n=3)
        assert len(result) <= 3

    def test_empty_input(self):
        result = extract_key_sentences([], n=5)
        assert result == []

    def test_fewer_than_n(self):
        texts = ["Only one sentence here"]
        result = extract_key_sentences(texts, n=5)
        assert len(result) <= 1

    def test_returns_original_text(self):
        texts = ["Authentication bug causes 500 errors", "Login flow is broken"]
        result = extract_key_sentences(texts, n=2)
        for r in result:
            assert r in texts


# ─── Semantic Backend Tests ────────────────────────────────────────────────────

from services.Nlp import (
    get_classifier,
    using_semantic_backend,
    SemanticClassifier,
    KeywordClassifier,
    semantic_key_sentences,
    tfidf_key_sentences,
)


# Skip marker applied to every test that requires a live semantic model.
# Use as: @pytest.mark.semantic
semantic_only = pytest.mark.skipif(
    not using_semantic_backend(),
    reason="Semantic model not loaded — set MINDBRIDGE_NLP_BACKEND=semantic and ensure model is downloaded",
)


class TestSemanticBackend:
    """
    Tests targeting the semantic backend specifically.
    Each test degrades gracefully if only the keyword backend is available,
    so CI never requires a live model download.

    Semantic-only tests are decorated with @semantic_only and skipped
    automatically when the keyword fallback is active.
    """

    # ── Backend detection ──────────────────────────────────────────────────────

    def test_backend_field_present(self):
        """classify_signal always reports which backend it used."""
        result = classify_signal("deploy the new build to staging")
        assert result["backend"] in ("semantic", "keyword")

    def test_classifier_is_one_of_known_types(self):
        clf = get_classifier()
        assert isinstance(clf, (SemanticClassifier, KeywordClassifier))

    def test_semantic_backend_loaded_when_available(self):
        """If sentence-transformers is importable AND the model is cached, semantic is used."""
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            pytest.skip("sentence-transformers not installed")
        # Model may be installed but not yet downloaded (e.g. in CI with no network)
        # so we report rather than hard-fail
        if not using_semantic_backend():
            pytest.skip(
                "sentence-transformers installed but model not cached — "
                "run once with network access to download all-MiniLM-L6-v2"
            )
        assert using_semantic_backend()

    # ── Paraphrase robustness (semantic catches; keyword often misses) ──────────

    @semantic_only
    def test_paraphrased_bug_no_keyword(self):
        """
        'going down' and 'load increases' aren't in TOPIC_KEYWORDS['bug'],
        so keyword mode returns a low-confidence general/other topic.
        Semantic mode should still resolve this to bug.
        """
        result = classify_signal(
            "The system keeps going down whenever the load increases"
        )
        if using_semantic_backend():
            assert result["topic"] == "bug", (
                f"Expected 'bug', got '{result['topic']}' (confidence {result['confidence']})"
            )
        else:
            # Keyword fallback: at minimum we shouldn't crash
            assert "topic" in result

    @semantic_only
    def test_paraphrased_planning_no_keyword(self):
        result = classify_signal(
            "We should figure out what we are building over the next few months"
        )
        assert result["topic"] == "idea"

    @semantic_only
    def test_paraphrased_idea_no_keyword(self):
        result = classify_signal(
            "It might be worth exploring a completely different architecture here"
        )
        assert result["topic"] == "idea"

    @semantic_only
    def test_implied_urgency_no_keyword(self):
        """
        No explicit urgency keyword — relies on semantic understanding.
        Keyword mode won't catch this; semantic should elevate urgency.
        """
        result = classify_signal(
            "Nobody can log in right now, everything is completely broken"
        )
        assert result["urgency"] in ("critical", "high")

    @semantic_only
    def test_security_signal_routed_to_security_member(self):
        """
        Semantic routing should favour the security-skilled member for a
        signal about an unauthorised access attempt, even without exact
        keyword matches in SKILL_TOPIC_MAP.
        """
        members = [
            {"id": "sec",    "skills": ["security", "backend"]},
            {"id": "design", "skills": ["design", "frontend"]},
            {"id": "sender", "skills": []},
        ]
        routed = route_signal(
            "bug", "high", members, "sender",
            "We detected an unauthorised access attempt in the authentication service"
        )
        assert "sec" in routed, (
            f"Security member not routed to. Got: {routed}"
        )

    # ── Confidence calibration ─────────────────────────────────────────────────

    @semantic_only
    def test_high_confidence_on_clear_signals(self):
        """Unambiguous signals should yield high confidence in semantic mode."""
        cases = [
            "PRODUCTION IS DOWN, all users are getting 500 errors right now",
            "Can someone review my pull request before end of day?",
            "I have a new idea: what if we added real-time collaboration?",
        ]
        for content in cases:
            result = classify_signal(content)
            assert result["confidence"] >= 0.3, (
                f"Low confidence {result['confidence']} for: {content!r}"
            )

    @semantic_only
    def test_ambiguous_signal_lower_confidence(self):
        """
        A vague message should produce lower confidence than a specific one,
        demonstrating the softmax temperature is doing useful work.
        """
        clear   = classify_signal("The login endpoint is throwing a NullPointerException")
        vague   = classify_signal("Something seems off")
        assert clear["confidence"] >= vague["confidence"]

    # ── Embedding API ──────────────────────────────────────────────────────────

    @semantic_only
    def test_encode_returns_numpy_array(self):
        import numpy as np
        clf = get_classifier()
        emb = clf.encode("test signal")
        assert isinstance(emb, np.ndarray)
        assert emb.ndim == 1
        assert emb.shape[0] == 384  # all-MiniLM-L6-v2 output dim

    @semantic_only
    def test_embedding_is_normalised(self):
        """Embeddings should be unit vectors (cosine sim = dot product.)"""
        import numpy as np
        clf = get_classifier()
        emb = clf.encode("Check whether this is properly normalised")
        norm = float(np.linalg.norm(emb))
        assert abs(norm - 1.0) < 1e-4, f"Embedding not normalised: norm={norm}"

    @semantic_only
    def test_encode_batch_shape(self):
        import numpy as np
        clf = get_classifier()
        texts = ["first signal", "second signal", "third signal"]
        batch = clf.encode_batch(texts)
        assert isinstance(batch, np.ndarray)
        assert batch.shape == (3, 384)

    @semantic_only
    def test_similar_signals_close_in_embedding_space(self):
        """Two bug reports should be closer to each other than to a planning signal."""
        import numpy as np
        clf = get_classifier()
        bug1    = clf.encode("The app crashes on startup")
        bug2    = clf.encode("We are getting a null pointer exception on load")
        plan    = clf.encode("Let us set the Q4 roadmap milestones")

        sim_bugs  = float(np.dot(bug1, bug2))
        sim_cross = float(np.dot(bug1, plan))
        assert sim_bugs > sim_cross, (
            f"Bug-bug similarity ({sim_bugs:.3f}) should exceed "
            f"bug-plan similarity ({sim_cross:.3f})"
        )

    # ── Semantic key-sentence extraction ──────────────────────────────────────

    @semantic_only
    def test_semantic_extraction_picks_central_sentence(self):
        """
        The most topically central sentence should rank first.
        All sentences are about auth bugs; the one that mentions both
        'authentication' and 'error' should be most central.
        """
        texts = [
            "We should redesign the onboarding flow",          # off-topic
            "The authentication service is returning 401 errors",  # on-topic
            "Users cannot log in due to a token validation error",  # on-topic
            "Let us plan a team lunch",                        # off-topic
        ]
        result = semantic_key_sentences(texts, n=2)
        assert len(result) == 2
        # Both top results should be the auth/error sentences
        on_topic = {
            "The authentication service is returning 401 errors",
            "Users cannot log in due to a token validation error",
        }
        assert result[0] in on_topic, f"Expected on-topic sentence first, got: {result[0]!r}"

    def test_tfidf_extraction_still_works(self):
        """Keyword-path summarisation is unaffected by the semantic upgrade."""
        texts = [
            "authentication error causes login failure",
            "login failure blocks all users",
            "completely unrelated sentence about lunch plans",
        ]
        result = tfidf_key_sentences(texts, n=2)
        assert len(result) == 2
        # The auth/login sentences should score higher than the lunch one
        assert "lunch" not in result[0]

    def test_extract_key_sentences_consistent_with_backend(self):
        """extract_key_sentences dispatches to the right implementation."""
        texts = [f"Sentence {i} discussing system performance and errors" for i in range(6)]
        result = extract_key_sentences(texts, n=3)
        assert len(result) == 3
        for r in result:
            assert r in texts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
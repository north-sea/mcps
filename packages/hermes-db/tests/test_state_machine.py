from hermes_db_mcp.services.state_machine import validate_transition


class TestTopicTransitions:
    def test_draft_to_writing(self):
        assert validate_transition("topic", "draft", "writing") is None

    def test_draft_to_archived(self):
        assert validate_transition("topic", "draft", "archived") is None

    def test_writing_to_published(self):
        assert validate_transition("topic", "writing", "published") is None

    def test_published_to_archived(self):
        assert validate_transition("topic", "published", "archived") is None

    def test_published_to_draft_rejected(self):
        err = validate_transition("topic", "published", "draft")
        assert err is not None
        assert err["error"] == "invalid_transition"
        assert err["from"] == "published"
        assert err["to"] == "draft"
        assert "archived" in err["allowed"]

    def test_archived_to_anything_rejected(self):
        err = validate_transition("topic", "archived", "draft")
        assert err is not None
        assert err["allowed"] == []

    def test_draft_to_published_rejected(self):
        err = validate_transition("topic", "draft", "published")
        assert err is not None
        assert "writing" in err["allowed"]


class TestInspirationTransitions:
    def test_candidate_to_adopted(self):
        assert validate_transition("inspiration", "candidate", "adopted") is None

    def test_candidate_to_archived(self):
        assert validate_transition("inspiration", "candidate", "archived") is None

    def test_adopted_to_used(self):
        assert validate_transition("inspiration", "adopted", "used") is None

    def test_used_to_archived(self):
        assert validate_transition("inspiration", "used", "archived") is None

    def test_used_to_candidate_rejected(self):
        err = validate_transition("inspiration", "used", "candidate")
        assert err is not None
        assert err["error"] == "invalid_transition"

    def test_archived_to_anything_rejected(self):
        err = validate_transition("inspiration", "archived", "candidate")
        assert err is not None
        assert err["allowed"] == []


class TestTopicCandidateTransitions:
    def test_new_to_shortlisted(self):
        assert validate_transition("topic_candidate", "new", "shortlisted") is None

    def test_new_to_adopted(self):
        assert validate_transition("topic_candidate", "new", "adopted") is None

    def test_shortlisted_to_rejected(self):
        assert validate_transition("topic_candidate", "shortlisted", "rejected") is None

    def test_rejected_to_adopted_rejected(self):
        err = validate_transition("topic_candidate", "rejected", "adopted")
        assert err is not None
        assert err["error"] == "invalid_transition"
        assert err["from"] == "rejected"
        assert err["to"] == "adopted"
        assert err["allowed"] == []

    def test_adopted_to_expired_rejected(self):
        err = validate_transition("topic_candidate", "adopted", "expired")
        assert err is not None
        assert err["allowed"] == []

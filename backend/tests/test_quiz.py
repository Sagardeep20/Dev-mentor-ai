"""Tests for quiz generator service."""

import pytest
from services.quiz_generator import (
    build_quiz_prompt,
    parse_questions_from_response,
    DIFFICULTY_LEVELS,
    QUESTION_TYPES
)


class TestQuizPromptBuilder:
    """Test quiz prompt generation."""

    def test_build_quiz_prompt_contains_context(self):
        """Prompt should include the code context."""
        context = "def hello():\n    print('world')"
        prompt = build_quiz_prompt(context, 5, "beginner", [])
        assert context in prompt

    def test_build_quiz_prompt_contains_num_questions(self):
        """Prompt should specify number of questions."""
        prompt = build_quiz_prompt("code", 10, "advanced", ["security"])
        assert "10" in prompt

    def test_build_quiz_prompt_contains_difficulty(self):
        """Prompt should include difficulty level."""
        prompt = build_quiz_prompt("code", 5, "intermediate", [])
        assert "intermediate" in prompt

    def test_build_quiz_prompt_contains_topics(self):
        """Prompt should include topics when provided."""
        topics = ["security", "performance"]
        prompt = build_quiz_prompt("code", 5, "beginner", topics)
        assert "security" in prompt
        assert "performance" in prompt

    def test_build_quiz_prompt_empty_topics(self):
        """Should handle empty topics list."""
        prompt = build_quiz_prompt("code", 5, "beginner", [])
        assert "general code understanding" in prompt


class TestQuestionParser:
    """Test question parsing from LLM response."""

    def test_parse_valid_json_response(self):
        """Should parse valid JSON with questions."""
        response = '''{
            "questions": [
                {
                    "question_text": "What does this do?",
                    "question_type": "multiple_choice",
                    "code_context": "def x(): pass",
                    "options": ["A) Option A", "B) Option B", "C) Option C", "D) Option D"],
                    "correct_answer": "B",
                    "explanation": "Because...",
                    "file_source": "test.py"
                }
            ]
        }'''

        questions = parse_questions_from_response(response)
        assert len(questions) == 1
        assert questions[0]["question_text"] == "What does this do?"
        assert questions[0]["question_type"] == "multiple_choice"

    def test_parse_multiple_questions(self):
        """Should parse multiple questions."""
        response = '''{
            "questions": [
                {"question_text": "Q1", "question_type": "true_false", "correct_answer": "True"},
                {"question_text": "Q2", "question_type": "multiple_choice", "correct_answer": "A", "options": ["A", "B", "C", "D"]}
            ]
        }'''

        questions = parse_questions_from_response(response)
        assert len(questions) == 2

    def test_parse_invalid_json(self):
        """Should return empty list for invalid JSON."""
        response = "This is not JSON"
        questions = parse_questions_from_response(response)
        assert questions == []

    def test_parse_missing_fields(self):
        """Should skip questions missing required fields."""
        response = '''{
            "questions": [
                {"question_text": "Valid question", "question_type": "multiple_choice", "correct_answer": "A"},
                {"question_text": "Missing type", "correct_answer": "A"}
            ]
        }'''

        questions = parse_questions_from_response(response)
        assert len(questions) == 1

    def test_parse_invalid_question_type(self):
        """Should skip questions with invalid question_type."""
        response = '''{
            "questions": [
                {"question_text": "Valid", "question_type": "multiple_choice", "correct_answer": "A"},
                {"question_text": "Invalid type", "question_type": "invalid_type", "correct_answer": "A"}
            ]
        }'''

        questions = parse_questions_from_response(response)
        assert len(questions) == 1
        assert questions[0]["question_type"] == "multiple_choice"

    def test_parse_with_json_suffix(self):
        """Should extract JSON from response with trailing text."""
        response = '''Here is the quiz:

{
    "questions": [
        {"question_text": "Test?", "question_type": "true_false", "correct_answer": "True"}
    ]
}

Let me know if you need more!'''

        questions = parse_questions_from_response(response)
        assert len(questions) == 1


class TestQuizConstants:
    """Test quiz configuration constants."""

    def test_difficulty_levels(self):
        """Should have expected difficulty levels."""
        assert "beginner" in DIFFICULTY_LEVELS
        assert "intermediate" in DIFFICULTY_LEVELS
        assert "advanced" in DIFFICULTY_LEVELS

    def test_question_types(self):
        """Should have expected question types."""
        assert "multiple_choice" in QUESTION_TYPES
        assert "true_false" in QUESTION_TYPES
        assert "code_output" in QUESTION_TYPES
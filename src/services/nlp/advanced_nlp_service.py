"""Advanced NLP Service

Provides sophisticated natural language processing capabilities using lightweight,
production-ready implementations that avoid heavy dependencies.
"""

import logging
import re
import string
from collections import Counter
from dataclasses import dataclass
from typing import Any

import nltk
from nltk.chunk import ne_chunk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.tag import pos_tag
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.tree import Tree

logger = logging.getLogger(__name__)


@dataclass
class EntityMention:
    """Represents an entity mention in text."""

    text: str
    label: str
    start: int
    end: int
    confidence: float


@dataclass
class ExtractedEntity:
    """Represents an extracted entity with metadata."""

    text: str
    entity_type: str
    confidence: float
    context: str
    mentions: list[EntityMention]


@dataclass
class TextAnalytics:
    """Text analysis results."""

    word_count: int
    sentence_count: int
    avg_sentence_length: float
    readability_score: float
    key_phrases: list[tuple[str, float]]
    sentiment_indicators: dict[str, int]


class AdvancedNLPService:
    """Advanced NLP service providing entity extraction, text analysis,
    and information processing using lightweight methods.
    """

    def __init__(self):
        """Initialize the NLP service and download required NLTK data."""
        self.stemmer = PorterStemmer()
        self.lemmatizer = WordNetLemmatizer()
        self._ensure_nltk_data()

        # Load stop words
        try:
            self.stop_words = set(stopwords.words("english"))
        except BaseException:
            self.stop_words = set(
                [
                    "the",
                    "a",
                    "an",
                    "and",
                    "or",
                    "but",
                    "in",
                    "on",
                    "at",
                    "to",
                    "for",
                    "of",
                    "with",
                    "by",
                ],
            )

        # Initialize patterns for entity recognition
        self._init_patterns()

    def _ensure_nltk_data(self):
        """Download required NLTK data if not present."""
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            try:
                nltk.download("punkt", quiet=True)
            except BaseException:
                logger.warning("Could not download NLTK punkt tokenizer")

        try:
            nltk.data.find("corpora/stopwords")
        except LookupError:
            try:
                nltk.download("stopwords", quiet=True)
            except BaseException:
                logger.warning("Could not download NLTK stopwords")

        try:
            nltk.data.find("taggers/averaged_perceptron_tagger")
        except LookupError:
            try:
                nltk.download("averaged_perceptron_tagger", quiet=True)
            except BaseException:
                logger.warning("Could not download NLTK POS tagger")

        try:
            nltk.data.find("chunkers/maxent_ne_chunker")
        except LookupError:
            try:
                nltk.download("maxent_ne_chunker", quiet=True)
                nltk.download("words", quiet=True)
            except BaseException:
                logger.warning("Could not download NLTK NE chunker")

    def _init_patterns(self):
        """Initialize regex patterns for entity recognition."""
        self.patterns = {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "url": re.compile(
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            ),
            "phone": re.compile(
                r"\\b(?:\\d{3}[-.]?\\d{3}[-.]?\\d{4}|\\(\\d{3}\\)\\s*\\d{3}[-.]?\\d{4})\\b",
            ),
            "date": re.compile(
                r"\\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\\s+\\d{1,2},?\\s+\\d{4}\\b",
            ),
            "money": re.compile(r"\\$\\d+(?:,\\d{3})*(?:\\.\\d{2})?\\b"),
            "percentage": re.compile(r"\\b\\d+(?:\\.\\d+)?%\\b"),
            # Organization patterns
            "organization": re.compile(
                r"\\b([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*\\s+(?:Corp|Corporation|Inc|Incorporated|Ltd|Limited|LLC|Company|Co\\.|University|Institute|School|College|Lab|Laboratory))\\b",
            ),
            # Technology patterns
            "technology": re.compile(
                r"\\b(AI|ML|API|SDK|CPU|GPU|RAM|SSD|HDD|IoT|VR|AR|5G|IPv6|HTTP|HTTPS|JSON|XML|HTML|CSS|SQL|NoSQL|MongoDB|PostgreSQL|MySQL|Redis|Docker|Kubernetes|React|Angular|Vue|Python|Java|JavaScript|TypeScript|C\\+\\+|Rust|Go|Swift|Kotlin)\\b",
            ),
            # Academic/Research patterns
            "academic": re.compile(
                r"\\b(PhD|Dr\\.|Professor|Research|Study|Analysis|Experiment|Hypothesis|Methodology|Algorithm|Framework|Model|Theory|Publication|Journal|Conference|Symposium|Workshop)\\b",
            ),
        }

    async def extract_entities(self, text: str) -> list[ExtractedEntity]:
        """Extract entities from text using multiple methods.

        Args:
            text: Input text to process

        Returns:
            List of extracted entities
        """
        try:
            entities = []

            # Pattern-based extraction
            pattern_entities = await self._extract_pattern_entities(text)
            entities.extend(pattern_entities)

            # NLTK-based named entity recognition
            nltk_entities = await self._extract_nltk_entities(text)
            entities.extend(nltk_entities)

            # Custom rule-based extraction
            rule_entities = await self._extract_rule_based_entities(text)
            entities.extend(rule_entities)

            # Deduplicate and merge similar entities
            entities = self._deduplicate_entities(entities)

            logger.info(f"Extracted {len(entities)} entities from text")
            return entities

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []

    async def _extract_pattern_entities(self, text: str) -> list[ExtractedEntity]:
        """Extract entities using regex patterns."""
        entities = []

        for entity_type, pattern in self.patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                entity_text = match.group()
                start, end = match.span()

                # Get context around the entity
                context_start = max(0, start - 50)
                context_end = min(len(text), end + 50)
                context = text[context_start:context_end]

                entities.append(
                    ExtractedEntity(
                        text=entity_text,
                        entity_type=entity_type.title(),
                        confidence=0.8,  # Pattern-based confidence
                        context=context,
                        mentions=[
                            EntityMention(
                                text=entity_text,
                                label=entity_type.title(),
                                start=start,
                                end=end,
                                confidence=0.8,
                            ),
                        ],
                    ),
                )

        return entities

    async def _extract_nltk_entities(self, text: str) -> list[ExtractedEntity]:
        """Extract entities using NLTK's named entity chunker."""
        entities = []

        try:
            # Tokenize and tag
            tokens = word_tokenize(text)
            pos_tags = pos_tag(tokens)

            # Named entity chunking
            tree = ne_chunk(pos_tags)

            current_entity = []
            current_label = None

            for item in tree:
                if isinstance(item, Tree):
                    # This is a named entity
                    entity_text = " ".join([token for token, pos in item.leaves()])
                    label = item.label()

                    # Map NLTK labels to our labels
                    mapped_label = self._map_nltk_label(label)

                    entities.append(
                        ExtractedEntity(
                            text=entity_text,
                            entity_type=mapped_label,
                            confidence=0.7,
                            context=self._get_context(text, entity_text),
                            mentions=[
                                EntityMention(
                                    text=entity_text,
                                    label=mapped_label,
                                    start=text.find(entity_text),
                                    end=text.find(entity_text) + len(entity_text),
                                    confidence=0.7,
                                ),
                            ],
                        ),
                    )

        except Exception as e:
            logger.warning(f"NLTK entity extraction failed: {e}")

        return entities

    async def _extract_rule_based_entities(self, text: str) -> list[ExtractedEntity]:
        """Extract entities using custom rules."""
        entities = []

        # Extract potential person names (capitalized words)
        person_pattern = re.compile(
            r"\\b(?:Dr\\.|Prof\\.|Mr\\.|Ms\\.|Mrs\\.)?\\s*([A-Z][a-z]+\\s+[A-Z][a-z]+)\\b",
        )
        for match in person_pattern.finditer(text):
            name = match.group(1)
            entities.append(
                ExtractedEntity(
                    text=name,
                    entity_type="Person",
                    confidence=0.6,
                    context=self._get_context(text, name),
                    mentions=[
                        EntityMention(
                            text=name,
                            label="Person",
                            start=match.start(1),
                            end=match.end(1),
                            confidence=0.6,
                        ),
                    ],
                ),
            )

        # Extract potential locations (proper nouns that might be places)
        location_pattern = re.compile(
            r"\\b([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*?)(?:\\s+(?:University|College|Institute|City|State|Country|Region))\\b",
        )
        for match in location_pattern.finditer(text):
            location = match.group(1)
            entities.append(
                ExtractedEntity(
                    text=location,
                    entity_type="Location",
                    confidence=0.5,
                    context=self._get_context(text, location),
                    mentions=[
                        EntityMention(
                            text=location,
                            label="Location",
                            start=match.start(1),
                            end=match.end(1),
                            confidence=0.5,
                        ),
                    ],
                ),
            )

        return entities

    def _map_nltk_label(self, nltk_label: str) -> str:
        """Map NLTK entity labels to our entity types."""
        mapping = {
            "PERSON": "Person",
            "ORGANIZATION": "Organization",
            "GPE": "Location",  # Geopolitical entity
            "LOCATION": "Location",
            "MONEY": "Money",
            "PERCENT": "Percentage",
            "DATE": "Date",
            "TIME": "Time",
        }
        return mapping.get(nltk_label, "Entity")

    def _get_context(self, text: str, entity: str) -> str:
        """Get context around an entity."""
        try:
            start_idx = text.find(entity)
            if start_idx == -1:
                return ""

            context_start = max(0, start_idx - 50)
            context_end = min(len(text), start_idx + len(entity) + 50)
            return text[context_start:context_end].strip()
        except BaseException:
            return ""

    def _deduplicate_entities(
        self,
        entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """Remove duplicate entities and merge similar ones."""
        if not entities:
            return []

        # Group by normalized text
        entity_groups = {}
        for entity in entities:
            key = entity.text.lower().strip()
            if key not in entity_groups:
                entity_groups[key] = []
            entity_groups[key].append(entity)

        # Keep the highest confidence entity from each group
        deduplicated = []
        for group in entity_groups.values():
            best_entity = max(group, key=lambda e: e.confidence)

            # Merge all mentions
            all_mentions = []
            for entity in group:
                all_mentions.extend(entity.mentions)

            best_entity.mentions = all_mentions
            deduplicated.append(best_entity)

        return deduplicated

    async def analyze_text(self, text: str) -> TextAnalytics:
        """Perform comprehensive text analysis.

        Args:
            text: Text to analyze

        Returns:
            Text analytics results
        """
        try:
            # Basic metrics
            sentences = sent_tokenize(text)
            words = word_tokenize(text.lower())

            # Filter out punctuation and stop words for key phrase extraction
            meaningful_words = [
                word
                for word in words
                if word not in string.punctuation
                and word not in self.stop_words
                and len(word) > 2
            ]

            word_count = len(meaningful_words)
            sentence_count = len(sentences)
            avg_sentence_length = (
                word_count / sentence_count if sentence_count > 0 else 0
            )

            # Simple readability score (Flesch Reading Ease approximation)
            avg_sentence_len = (
                sum(len(word_tokenize(s)) for s in sentences) / sentence_count
                if sentence_count > 0
                else 0
            )
            avg_syllables = (
                sum(self._count_syllables(word) for word in meaningful_words)
                / word_count
                if word_count > 0
                else 0
            )
            readability_score = (
                206.835 - (1.015 * avg_sentence_len) - (84.6 * avg_syllables)
            )
            readability_score = max(0, min(100, readability_score))  # Clamp to 0-100

            # Extract key phrases using frequency and POS tags
            key_phrases = await self._extract_key_phrases(text, meaningful_words)

            # Simple sentiment indicators
            sentiment_indicators = self._analyze_sentiment_indicators(meaningful_words)

            return TextAnalytics(
                word_count=word_count,
                sentence_count=sentence_count,
                avg_sentence_length=avg_sentence_length,
                readability_score=readability_score,
                key_phrases=key_phrases,
                sentiment_indicators=sentiment_indicators,
            )

        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return TextAnalytics(
                word_count=0,
                sentence_count=0,
                avg_sentence_length=0.0,
                readability_score=0.0,
                key_phrases=[],
                sentiment_indicators={},
            )

    def _count_syllables(self, word: str) -> int:
        """Simple syllable counting heuristic."""
        word = word.lower()
        count = 0
        vowels = "aeiouy"
        if word[0] in vowels:
            count += 1
        for index in range(1, len(word)):
            if word[index] in vowels and word[index - 1] not in vowels:
                count += 1
        if word.endswith("e"):
            count -= 1
        if count == 0:
            count += 1
        return count

    async def _extract_key_phrases(
        self,
        text: str,
        words: list[str],
    ) -> list[tuple[str, float]]:
        """Extract key phrases using frequency and linguistic patterns."""
        try:
            # Get word frequencies
            word_freq = Counter(words)

            # Get POS tags for meaningful words
            tokens = word_tokenize(text)
            pos_tags = pos_tag(tokens)

            # Extract noun phrases and important terms
            key_terms = []

            # Add most frequent words
            for word, freq in word_freq.most_common(10):
                if len(word) > 3:  # Skip very short words
                    score = freq / len(words) * 100  # Frequency percentage
                    key_terms.append((word, score))

            # Extract noun phrases (simplified)
            noun_phrases = []
            current_phrase = []

            for word, pos in pos_tags:
                if pos.startswith("NN") or pos.startswith("JJ"):  # Nouns and adjectives
                    current_phrase.append(word.lower())
                else:
                    if len(current_phrase) >= 2:  # Multi-word noun phrases
                        phrase = " ".join(current_phrase)
                        if phrase not in [kp[0] for kp in key_terms]:
                            noun_phrases.append(phrase)
                    current_phrase = []

            # Score noun phrases based on word frequency
            for phrase in noun_phrases[:5]:  # Top 5 noun phrases
                words_in_phrase = phrase.split()
                avg_freq = sum(
                    word_freq.get(word, 0) for word in words_in_phrase
                ) / len(words_in_phrase)
                score = (
                    avg_freq / len(words) * 100 * len(words_in_phrase)
                )  # Boost longer phrases
                key_terms.append((phrase, score))

            # Sort by score and return top terms
            key_terms.sort(key=lambda x: x[1], reverse=True)
            return key_terms[:10]

        except Exception as e:
            logger.warning(f"Key phrase extraction failed: {e}")
            return []

    def _analyze_sentiment_indicators(self, words: list[str]) -> dict[str, int]:
        """Analyze basic sentiment indicators."""
        positive_words = {
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "fantastic",
            "awesome",
            "brilliant",
            "outstanding",
            "perfect",
            "love",
            "like",
            "enjoy",
            "happy",
            "pleased",
            "satisfied",
            "successful",
            "effective",
            "efficient",
            "innovative",
            "advanced",
            "powerful",
            "robust",
            "reliable",
            "secure",
        }

        negative_words = {
            "bad",
            "terrible",
            "awful",
            "horrible",
            "disappointing",
            "poor",
            "weak",
            "failed",
            "broken",
            "wrong",
            "error",
            "problem",
            "issue",
            "difficult",
            "challenging",
            "complex",
            "slow",
            "inefficient",
            "unreliable",
            "insecure",
            "vulnerable",
        }

        neutral_words = {
            "okay",
            "fine",
            "average",
            "normal",
            "standard",
            "typical",
            "regular",
            "common",
            "usual",
            "moderate",
        }

        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        neutral_count = sum(1 for word in words if word in neutral_words)

        return {
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
        }

    async def health_check(self) -> dict[str, Any]:
        """Check NLP service health."""
        try:
            # Test basic functionality
            test_text = "This is a test sentence for Dr. John Doe at MIT University."
            entities = await self.extract_entities(test_text)
            analytics = await self.analyze_text(test_text)

            return {
                "status": "healthy",
                "entities_extracted": len(entities),
                "analytics_generated": analytics.word_count > 0,
                "patterns_loaded": len(self.patterns),
                "nltk_available": True,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "patterns_loaded": (
                    len(self.patterns) if hasattr(self, "patterns") else 0
                ),
            }


# Singleton instance
_nlp_service = None


def get_nlp_service() -> AdvancedNLPService:
    """Get or create NLP service singleton."""
    global _nlp_service
    if _nlp_service is None:
        _nlp_service = AdvancedNLPService()
    return _nlp_service

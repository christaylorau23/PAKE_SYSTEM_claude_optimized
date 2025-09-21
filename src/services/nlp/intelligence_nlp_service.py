"""Intelligence Engine NLP Service

Advanced NLP service implementing the Personal Intelligence Engine blueprint with:
- spaCy for advanced NER and linguistic processing
- sentence-transformers for semantic embeddings
- Relationship extraction for knowledge graph population
- Sentiment analysis with transformer models
- Topic modeling for trend detection

Following PAKE System enterprise standards with comprehensive error handling,
async/await patterns, and production-ready performance.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

# Scientific computing
# Core NLP frameworks
import spacy
from gensim.corpora import Dictionary

# Topic modeling
from gensim.models import CoherenceModel, LdaModel

# Sentence transformers for embeddings
from sentence_transformers import SentenceTransformer
from spacy.matcher import Matcher

# Hugging Face transformers for sentiment
from transformers import pipeline

from src.services.caching.redis_cache_service import CacheService

# PAKE System imports
from src.utils.async_tools import run_in_executor

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Entity types following the intelligence engine blueprint."""

    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "GPE"
    MONEY = "MONEY"
    DATE = "DATE"
    TIME = "TIME"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECH"
    CONCEPT = "CONCEPT"
    EVENT = "EVENT"


class RelationType(Enum):
    """Relationship types for knowledge graph construction."""

    ACQUIRED = "ACQUIRED"
    IS_CEO_OF = "IS_CEO_OF"
    LOCATED_IN = "LOCATED_IN"
    WORKED_AT = "WORKED_AT"
    FOUNDED = "FOUNDED"
    INVESTED_IN = "INVESTED_IN"
    COLLABORATES_WITH = "COLLABORATES_WITH"
    COMPETES_WITH = "COMPETES_WITH"
    RELATED_TO = "RELATED_TO"


@dataclass(frozen=True)
class EntityMention:
    """Enhanced entity mention with confidence and context."""

    text: str
    label: str
    start: int
    end: int
    confidence: float
    context_window: str
    normalized_text: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "normalized_text", self.text.lower().strip())


@dataclass(frozen=True)
class ExtractedEntity:
    """Enhanced extracted entity with semantic information."""

    text: str
    entity_type: EntityType
    confidence: float
    mentions: list[EntityMention]
    semantic_embedding: np.ndarray | None = None
    linked_entities: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractedRelationship:
    """Relationship between entities for knowledge graph."""

    subject_entity: str
    relation_type: RelationType
    object_entity: str
    confidence: float
    source_sentence: str
    context: str
    supporting_evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SentimentResult:
    """Sentiment analysis result with fine-grained scores."""

    polarity: float  # -1.0 (negative) to 1.0 (positive)
    subjectivity: float  # 0.0 (objective) to 1.0 (subjective)
    confidence: float
    label: str  # POSITIVE, NEGATIVE, NEUTRAL
    emotional_indicators: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TopicResult:
    """Topic modeling result."""

    topic_id: int
    keywords: list[tuple[str, float]]
    coherence_score: float
    document_probability: float
    topic_description: str


@dataclass(frozen=True)
class DocumentAnalysis:
    """Comprehensive document analysis result."""

    entities: list[ExtractedEntity]
    relationships: list[ExtractedRelationship]
    sentiment: SentimentResult
    topics: list[TopicResult]
    semantic_embedding: np.ndarray
    key_phrases: list[tuple[str, float]]
    text_statistics: dict[str, Any]
    processing_time_ms: float


class IntelligenceNLPService:
    """Advanced NLP service implementing the Personal Intelligence Engine blueprint.

    Provides:
    - Advanced named entity recognition with spaCy
    - Semantic embeddings with sentence-transformers
    - Relationship extraction for knowledge graphs
    - Multi-model sentiment analysis
    - Topic modeling and trend detection
    - Async processing with caching
    """

    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        embedding_model: str = "all-MiniLM-L6-v2",
        sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest",
        cache_service: CacheService | None = None,
    ):
        """Initialize the Intelligence NLP Service.

        Args:
            model_name: spaCy model to use
            embedding_model: Sentence transformer model
            sentiment_model: Hugging Face sentiment model
            cache_service: Optional cache service for performance
        """
        self.model_name = model_name
        self.embedding_model_name = embedding_model
        self.sentiment_model_name = sentiment_model
        self.cache_service = cache_service

        # Model containers
        self.nlp: spacy.Language | None = None
        self.embedding_model: SentenceTransformer | None = None
        self.sentiment_pipeline = None
        self.matcher: Matcher | None = None

        # Topic modeling
        self.lda_model: LdaModel | None = None
        self.dictionary: Dictionary | None = None

        # Performance tracking
        self.model_cache_dir = Path("cache/nlp_models")
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)

        # Processing statistics
        self._stats = {
            "documents_processed": 0,
            "entities_extracted": 0,
            "relationships_found": 0,
            "cache_hits": 0,
            "processing_time_total": 0.0,
        }

    async def initialize(self) -> bool:
        """Initialize all NLP models and components.

        Returns:
            bool: Success status
        """
        try:
            logger.info("Initializing Intelligence NLP Service...")

            # Initialize spaCy model
            await self._initialize_spacy()

            # Initialize sentence transformer
            await self._initialize_embeddings()

            # Initialize sentiment analysis
            await self._initialize_sentiment()

            # Initialize relationship patterns
            await self._initialize_relationship_patterns()

            logger.info("Intelligence NLP Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize NLP service: {e}")
            return False

    async def _initialize_spacy(self) -> None:
        """Initialize spaCy model with custom components."""
        try:
            # Load model
            self.nlp = spacy.load(self.model_name)

            # Add custom entity ruler for domain-specific entities
            if "entity_ruler" not in self.nlp.pipe_names:
                ruler = self.nlp.add_pipe("entity_ruler", before="ner")
                await self._add_custom_patterns(ruler)

            # Initialize matcher for relationship extraction
            self.matcher = Matcher(self.nlp.vocab)

            logger.info(f"spaCy model '{self.model_name}' loaded successfully")

        except Exception as e:
            logger.error(f"Failed to initialize spaCy: {e}")
            raise

    async def _initialize_embeddings(self) -> None:
        """Initialize sentence transformer model."""
        try:
            # Check cache first
            cache_path = (
                self.model_cache_dir
                / f"embeddings_{self.embedding_model_name.replace('/', '_')}"
            )

            if cache_path.exists():
                logger.info(f"Loading cached embedding model from {cache_path}")
                self.embedding_model = SentenceTransformer(str(cache_path))
            else:
                logger.info(f"Downloading embedding model: {self.embedding_model_name}")
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                # Cache the model
                self.embedding_model.save(str(cache_path))

            logger.info("Sentence transformer model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise

    async def _initialize_sentiment(self) -> None:
        """Initialize sentiment analysis pipeline."""
        try:
            logger.info(f"Loading sentiment model: {self.sentiment_model_name}")

            # Initialize with specific model for social media text
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=self.sentiment_model_name,
                return_all_scores=True,
            )

            logger.info("Sentiment analysis pipeline loaded successfully")

        except Exception as e:
            logger.error(f"Failed to initialize sentiment analysis: {e}")
            raise

    async def _add_custom_patterns(self, ruler) -> None:
        """Add custom entity patterns for domain-specific recognition."""
        patterns = [
            # Technology entities
            {
                "label": "TECHNOLOGY",
                "pattern": [
                    {
                        "LOWER": {
                            "IN": ["ai", "ml", "blockchain", "iot", "5g", "api", "sdk"],
                        },
                    },
                ],
            },
            {
                "label": "TECHNOLOGY",
                "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{2,}$"}}],
            },  # Acronyms
            # Financial entities
            {
                "label": "FINANCIAL",
                "pattern": [
                    {
                        "LOWER": {
                            "IN": ["ipo", "vc", "funding", "investment", "acquisition"],
                        },
                    },
                ],
            },
            # Company suffixes
            {
                "label": "ORG",
                "pattern": [
                    {"TEXT": {"REGEX": r".*"}},
                    {"LOWER": {"IN": ["inc", "corp", "ltd", "llc", "llp"]}},
                ],
            },
            # Academic institutions
            {
                "label": "ORG",
                "pattern": [
                    {"TEXT": {"REGEX": r".*"}},
                    {"LOWER": {"IN": ["university", "college", "institute", "lab"]}},
                ],
            },
        ]

        ruler.add_patterns(patterns)

    async def _initialize_relationship_patterns(self) -> None:
        """Initialize patterns for relationship extraction."""
        if not self.matcher:
            return

        # CEO relationship pattern
        ceo_pattern = [
            {"LOWER": {"IN": ["ceo", "chief", "executive"]}},
            {"LOWER": {"IN": ["of", "at"]}, "OP": "?"},
            {"ENT_TYPE": "ORG"},
        ]
        self.matcher.add("CEO_OF", [ceo_pattern])

        # Acquisition pattern
        acquisition_pattern = [
            {"ENT_TYPE": "ORG"},
            {"LOWER": {"IN": ["acquired", "bought", "purchased"]}},
            {"ENT_TYPE": "ORG"},
        ]
        self.matcher.add("ACQUIRED", [acquisition_pattern])

        # Founded pattern
        founded_pattern = [
            {"LOWER": {"IN": ["founded", "started", "launched"]}},
            {"ENT_TYPE": "ORG"},
        ]
        self.matcher.add("FOUNDED", [founded_pattern])

        # Investment pattern
        investment_pattern = [
            {"ENT_TYPE": "ORG"},
            {"LOWER": {"IN": ["invested", "funding", "backed"]}},
            {"ENT_TYPE": "ORG"},
        ]
        self.matcher.add("INVESTED_IN", [investment_pattern])

    async def analyze_document(
        self,
        text: str,
        include_embeddings: bool = True,
        include_topics: bool = True,
        cache_key: str | None = None,
    ) -> DocumentAnalysis:
        """Perform comprehensive document analysis.

        Args:
            text: Document text to analyze
            include_embeddings: Whether to generate semantic embeddings
            include_topics: Whether to perform topic modeling
            cache_key: Optional cache key for results

        Returns:
            DocumentAnalysis: Comprehensive analysis results
        """
        start_time = datetime.now()

        try:
            # Check cache first
            if cache_key and self.cache_service:
                cached_result = await self.cache_service.get(
                    f"nlp_analysis:{cache_key}",
                )
                if cached_result:
                    self._stats["cache_hits"] += 1
                    return DocumentAnalysis(**cached_result)

            # Run analysis steps in parallel where possible
            tasks = [
                self.extract_entities(text),
                self.extract_relationships(text),
                self.analyze_sentiment(text),
                self.extract_key_phrases(text),
                self._compute_text_statistics(text),
            ]

            if include_embeddings:
                tasks.append(self.generate_embeddings([text]))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            entities = results[0] if not isinstance(results[0], Exception) else []
            relationships = results[1] if not isinstance(results[1], Exception) else []
            sentiment = (
                results[2]
                if not isinstance(results[2], Exception)
                else SentimentResult(0, 0, 0, "NEUTRAL")
            )
            key_phrases = results[3] if not isinstance(results[3], Exception) else []
            text_stats = results[4] if not isinstance(results[4], Exception) else {}

            # Handle embeddings
            if include_embeddings and len(results) > 5:
                embeddings = (
                    results[5]
                    if not isinstance(results[5], Exception)
                    else np.array([])
                )
                semantic_embedding = (
                    embeddings[0] if len(embeddings) > 0 else np.array([])
                )
            else:
                semantic_embedding = np.array([])

            # Topic modeling (if requested)
            topics = []
            if include_topics:
                topics = await self.extract_topics([text])

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Create analysis result
            analysis = DocumentAnalysis(
                entities=entities,
                relationships=relationships,
                sentiment=sentiment,
                topics=topics,
                semantic_embedding=semantic_embedding,
                key_phrases=key_phrases,
                text_statistics=text_stats,
                processing_time_ms=processing_time,
            )

            # Cache result
            if cache_key and self.cache_service:
                # Convert to dict for caching (numpy arrays need special handling)
                cache_data = {
                    **analysis.__dict__,
                    "semantic_embedding": (
                        semantic_embedding.tolist()
                        if semantic_embedding.size > 0
                        else []
                    ),
                }
                await self.cache_service.set(
                    f"nlp_analysis:{cache_key}",
                    cache_data,
                    ttl=3600,
                )

            # Update statistics
            self._stats["documents_processed"] += 1
            self._stats["entities_extracted"] += len(entities)
            self._stats["relationships_found"] += len(relationships)
            self._stats["processing_time_total"] += processing_time

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing document: {e}")
            raise

    async def extract_entities(self, text: str) -> list[ExtractedEntity]:
        """Extract entities using advanced spaCy NER.

        Args:
            text: Text to process

        Returns:
            List[ExtractedEntity]: Extracted entities with metadata
        """
        try:
            if not self.nlp:
                raise ValueError("spaCy model not initialized")

            # Process text
            doc = await run_in_executor(self.nlp, text)

            entities = []
            for ent in doc.ents:
                # Get entity type
                try:
                    entity_type = EntityType(ent.label_)
                except ValueError:
                    entity_type = EntityType.CONCEPT  # Default for unknown types

                # Extract context window
                start_char = max(0, ent.start_char - 50)
                end_char = min(len(text), ent.end_char + 50)
                context = text[start_char:end_char]

                # Create mention
                mention = EntityMention(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=float(ent._.get("confidence", 0.8)),
                    # Default confidence
                    context_window=context,
                )

                # Generate semantic embedding for entity
                semantic_embedding = None
                if self.embedding_model:
                    try:
                        embedding = await run_in_executor(
                            self.embedding_model.encode,
                            [ent.text],
                        )
                        semantic_embedding = embedding[0]
                    except Exception as e:
                        logger.warning(
                            f"Failed to generate embedding for entity '{ent.text}': {
                                e
                            }",
                        )

                # Create entity
                entity = ExtractedEntity(
                    text=ent.text,
                    entity_type=entity_type,
                    confidence=float(ent._.get("confidence", 0.8)),
                    mentions=[mention],
                    semantic_embedding=semantic_embedding,
                    properties={
                        "span_start": ent.start,
                        "span_end": ent.end,
                        "pos_tags": [token.pos_ for token in ent],
                        "lemmas": [token.lemma_ for token in ent],
                    },
                )

                entities.append(entity)

            logger.debug(f"Extracted {len(entities)} entities from text")
            return entities

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []

    async def extract_relationships(self, text: str) -> list[ExtractedRelationship]:
        """Extract relationships between entities using pattern matching.

        Args:
            text: Text to process

        Returns:
            List[ExtractedRelationship]: Extracted relationships
        """
        try:
            if not self.nlp or not self.matcher:
                raise ValueError("spaCy model or matcher not initialized")

            doc = await run_in_executor(self.nlp, text)
            matches = self.matcher(doc)

            relationships = []
            for match_id, start, end in matches:
                span = doc[start:end]
                pattern_name = self.nlp.vocab.strings[match_id]

                # Extract entities from the matched span
                entities_in_span = [ent for ent in span.ents]

                if len(entities_in_span) >= 2:
                    # Create relationship based on pattern
                    relation_type = self._map_pattern_to_relation(pattern_name)

                    relationship = ExtractedRelationship(
                        subject_entity=entities_in_span[0].text,
                        relation_type=relation_type,
                        object_entity=entities_in_span[1].text,
                        confidence=0.7,  # Pattern-based confidence
                        source_sentence=span.sent.text,
                        context=span.text,
                        supporting_evidence=[span.text],
                    )

                    relationships.append(relationship)

            logger.debug(f"Extracted {len(relationships)} relationships from text")
            return relationships

        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")
            return []

    def _map_pattern_to_relation(self, pattern_name: str) -> RelationType:
        """Map matcher pattern names to relation types."""
        mapping = {
            "CEO_OF": RelationType.IS_CEO_OF,
            "ACQUIRED": RelationType.ACQUIRED,
            "FOUNDED": RelationType.FOUNDED,
            "INVESTED_IN": RelationType.INVESTED_IN,
        }
        return mapping.get(pattern_name, RelationType.RELATED_TO)

    async def analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze sentiment using transformer models.

        Args:
            text: Text to analyze

        Returns:
            SentimentResult: Sentiment analysis results
        """
        try:
            if not self.sentiment_pipeline:
                raise ValueError("Sentiment pipeline not initialized")

            # Run sentiment analysis
            results = await run_in_executor(self.sentiment_pipeline, text)

            # Process results (expecting list of scores)
            if isinstance(results, list) and len(results) > 0:
                scores = results[0] if isinstance(results[0], list) else results

                # Find dominant sentiment
                best_score = max(scores, key=lambda x: x["score"])
                label = best_score["label"]
                confidence = best_score["score"]

                # Map to polarity scale
                polarity_mapping = {"POSITIVE": 1.0, "NEGATIVE": -1.0, "NEUTRAL": 0.0}

                # Convert confidence-weighted polarity
                polarity = polarity_mapping.get(label, 0.0) * confidence

                # Calculate subjectivity (simple heuristic based on confidence)
                subjectivity = confidence if label != "NEUTRAL" else 1.0 - confidence

                return SentimentResult(
                    polarity=polarity,
                    subjectivity=subjectivity,
                    confidence=confidence,
                    label=label,
                    emotional_indicators={
                        score["label"]: score["score"] for score in scores
                    },
                )

            # Fallback neutral result
            return SentimentResult(0.0, 0.0, 0.0, "NEUTRAL")

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return SentimentResult(0.0, 0.0, 0.0, "NEUTRAL")

    async def generate_embeddings(self, texts: list[str]) -> np.ndarray:
        """Generate semantic embeddings for texts.

        Args:
            texts: List of texts to encode

        Returns:
            np.ndarray: Embeddings matrix
        """
        try:
            if not self.embedding_model:
                raise ValueError("Embedding model not initialized")

            # Generate embeddings
            embeddings = await run_in_executor(self.embedding_model.encode, texts)

            logger.debug(f"Generated embeddings for {len(texts)} texts")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return np.array([])

    async def extract_topics(
        self,
        documents: list[str],
        num_topics: int = 5,
    ) -> list[TopicResult]:
        """Extract topics using LDA topic modeling.

        Args:
            documents: List of documents for topic modeling
            num_topics: Number of topics to extract

        Returns:
            List[TopicResult]: Extracted topics
        """
        try:
            if len(documents) < 2:
                logger.warning("Need at least 2 documents for topic modeling")
                return []

            # Preprocess documents
            processed_docs = []
            for doc in documents:
                if self.nlp:
                    nlp_doc = await run_in_executor(self.nlp, doc)
                    tokens = [
                        token.lemma_.lower()
                        for token in nlp_doc
                        if not token.is_stop
                        and not token.is_punct
                        and len(token.text) > 2
                    ]
                    processed_docs.append(tokens)

            # Create dictionary and corpus
            dictionary = Dictionary(processed_docs)
            dictionary.filter_extremes(no_below=2, no_above=0.5)
            corpus = [dictionary.doc2bow(doc) for doc in processed_docs]

            # Train LDA model
            lda_model = await run_in_executor(
                LdaModel,
                corpus=corpus,
                id2word=dictionary,
                num_topics=num_topics,
                random_state=42,
                passes=10,
                alpha="auto",
                per_word_topics=True,
            )

            # Calculate coherence
            coherence_model = await run_in_executor(
                CoherenceModel,
                model=lda_model,
                texts=processed_docs,
                dictionary=dictionary,
                coherence="c_v",
            )
            coherence_score = await run_in_executor(coherence_model.get_coherence)

            # Extract topics
            topics = []
            for topic_id in range(num_topics):
                topic_words = lda_model.show_topic(topic_id, topn=10)

                # Generate topic description
                top_words = [word for word, _ in topic_words[:3]]
                description = f"Topic about {', '.join(top_words)}"

                topic_result = TopicResult(
                    topic_id=topic_id,
                    keywords=topic_words,
                    coherence_score=coherence_score,
                    document_probability=0.0,  # Would need document-topic distribution
                    topic_description=description,
                )
                topics.append(topic_result)

            logger.debug(
                f"Extracted {len(topics)} topics with coherence {coherence_score:.3f}",
            )
            return topics

        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return []

    async def extract_key_phrases(
        self,
        text: str,
        max_phrases: int = 10,
    ) -> list[tuple[str, float]]:
        """Extract key phrases using TF-IDF and linguistic patterns.

        Args:
            text: Text to process
            max_phrases: Maximum number of phrases to return

        Returns:
            List[Tuple[str, float]]: Key phrases with scores
        """
        try:
            if not self.nlp:
                raise ValueError("spaCy model not initialized")

            doc = await run_in_executor(self.nlp, text)

            # Extract noun phrases
            noun_phrases = []
            for chunk in doc.noun_chunks:
                if len(chunk.text) > 3 and not all(token.is_stop for token in chunk):
                    noun_phrases.append(chunk.text.lower().strip())

            # Extract named entities as key phrases
            entity_phrases = [ent.text.lower() for ent in doc.ents]

            # Combine and score phrases
            all_phrases = noun_phrases + entity_phrases
            phrase_counts = {}
            for phrase in all_phrases:
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1

            # Score by frequency and length
            scored_phrases = []
            for phrase, count in phrase_counts.items():
                score = count * len(phrase.split())  # Frequency * length
                scored_phrases.append((phrase, score))

            # Sort and return top phrases
            scored_phrases.sort(key=lambda x: x[1], reverse=True)
            return scored_phrases[:max_phrases]

        except Exception as e:
            logger.error(f"Error extracting key phrases: {e}")
            return []

    async def _compute_text_statistics(self, text: str) -> dict[str, Any]:
        """Compute basic text statistics."""
        try:
            if not self.nlp:
                return {}

            doc = await run_in_executor(self.nlp, text)

            stats = {
                "character_count": len(text),
                "word_count": len([token for token in doc if not token.is_space]),
                "sentence_count": len(list(doc.sents)),
                "paragraph_count": text.count("\n\n") + 1,
                "avg_words_per_sentence": 0,
                "lexical_diversity": 0,
                "reading_time_minutes": 0,
            }

            # Calculate averages
            if stats["sentence_count"] > 0:
                stats["avg_words_per_sentence"] = (
                    stats["word_count"] / stats["sentence_count"]
                )

            # Lexical diversity (type-token ratio)
            words = [token.text.lower() for token in doc if token.is_alpha]
            if words:
                unique_words = set(words)
                stats["lexical_diversity"] = len(unique_words) / len(words)

            # Reading time (average 200 words per minute)
            stats["reading_time_minutes"] = stats["word_count"] / 200

            return stats

        except Exception as e:
            logger.error(f"Error computing text statistics: {e}")
            return {}

    async def get_service_stats(self) -> dict[str, Any]:
        """Get service performance statistics."""
        return {
            **self._stats,
            "models_loaded": {
                "spacy": self.nlp is not None,
                "embeddings": self.embedding_model is not None,
                "sentiment": self.sentiment_pipeline is not None,
            },
            "cache_hit_rate": (
                self._stats["cache_hits"]
                / max(self._stats["documents_processed"], 1)
                * 100
            ),
        }

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive health check for the service."""
        try:
            # Test basic functionality
            test_text = "Apple Inc. is acquiring a U.K. startup for $1 billion. Tim Cook, CEO of Apple, announced this strategic investment."

            analysis = await self.analyze_document(test_text, include_topics=False)

            return {
                "status": "healthy",
                "models_initialized": {
                    "spacy": self.nlp is not None,
                    "embeddings": self.embedding_model is not None,
                    "sentiment": self.sentiment_pipeline is not None,
                    "matcher": self.matcher is not None,
                },
                "test_results": {
                    "entities_found": len(analysis.entities),
                    "relationships_found": len(analysis.relationships),
                    "sentiment_computed": analysis.sentiment.label != "NEUTRAL",
                    "embeddings_generated": analysis.semantic_embedding.size > 0,
                    "processing_time_ms": analysis.processing_time_ms,
                },
                "performance_stats": await self.get_service_stats(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "models_initialized": {
                    "spacy": self.nlp is not None,
                    "embeddings": self.embedding_model is not None,
                    "sentiment": self.sentiment_pipeline is not None,
                    "matcher": self.matcher is not None,
                },
            }


# Singleton instance
_intelligence_nlp_service: IntelligenceNLPService | None = None


async def get_intelligence_nlp_service(
    cache_service: CacheService | None = None,
) -> IntelligenceNLPService:
    """Get or create Intelligence NLP service singleton.

    Args:
        cache_service: Optional cache service for performance

    Returns:
        IntelligenceNLPService: Initialized service instance
    """
    global _intelligence_nlp_service

    if _intelligence_nlp_service is None:
        _intelligence_nlp_service = IntelligenceNLPService(cache_service=cache_service)
        await _intelligence_nlp_service.initialize()

    return _intelligence_nlp_service

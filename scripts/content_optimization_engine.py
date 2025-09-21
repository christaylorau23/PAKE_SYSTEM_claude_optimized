#!/usr/bin/env python3
"""
Content Optimization Engine
AI-powered content optimization for maximum social media engagement
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass

# ML and NLP libraries
try:
    import nltk
    import openai
    import requests
    from langdetect import detect
    from textblob import TextBlob
except ImportError:
    print(
        "NLP dependencies not installed. Run: pip install nltk textblob langdetect openai",
    )


@dataclass
class ContentOptimization:
    """Content optimization results"""

    original_content: str
    optimized_content: str
    confidence_score: float
    platform_adaptations: dict[str, str]
    recommended_hashtags: list[str]
    optimal_posting_time: str
    expected_engagement_rate: float
    content_score: float
    optimization_suggestions: list[str]


@dataclass
class HashtagAnalysis:
    """Hashtag analysis results"""

    hashtag: str
    popularity_score: float
    competition_level: str  # low, medium, high
    relevance_score: float
    trending_potential: float
    recommended: bool


class ContentOptimizationEngine:
    """AI-powered content optimization engine"""

    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.logger = logging.getLogger(__name__)

        # Initialize OpenAI if API key is available
        if self.openai_api_key:
            openai.api_key = self.openai_api_key

        # Platform-specific configuration
        self.platform_configs = {
            "twitter": {
                "max_length": 280,
                "hashtag_limit": 5,
                "optimal_hashtag_count": 2,
                "engagement_keywords": [
                    "question",
                    "poll",
                    "share",
                    "retweet",
                    "thoughts",
                ],
                "best_times": ["09:00", "12:00", "15:00", "18:00"],
            },
            "instagram": {
                "max_length": 2200,
                "hashtag_limit": 30,
                "optimal_hashtag_count": 11,
                "engagement_keywords": ["swipe", "story", "save", "double tap", "tag"],
                "best_times": ["11:00", "14:00", "17:00", "20:00"],
            },
            "linkedin": {
                "max_length": 3000,
                "hashtag_limit": 5,
                "optimal_hashtag_count": 3,
                "engagement_keywords": [
                    "insights",
                    "professional",
                    "industry",
                    "leadership",
                ],
                "best_times": ["08:00", "12:00", "17:00", "18:00"],
            },
            "tiktok": {
                "max_length": 150,
                "hashtag_limit": 100,
                "optimal_hashtag_count": 5,
                "engagement_keywords": ["viral", "trending", "fyp", "challenge"],
                "best_times": ["06:00", "10:00", "19:00", "22:00"],
            },
            "reddit": {
                "max_length": 40000,
                "hashtag_limit": 0,
                "optimal_hashtag_count": 0,
                "engagement_keywords": ["discussion", "question", "eli5", "ama"],
                "best_times": ["08:00", "12:00", "17:00", "21:00"],
            },
        }

        # Load trending hashtags and keywords
        self.trending_hashtags = self._load_trending_data()

        # Content scoring weights
        self.scoring_weights = {
            "readability": 0.2,
            "engagement_potential": 0.25,
            "hashtag_optimization": 0.15,
            "length_optimization": 0.1,
            "sentiment": 0.15,
            "platform_alignment": 0.15,
        }

    def _load_trending_data(self) -> dict:
        """Load trending hashtags and keywords"""
        # In production, this would fetch from APIs or databases
        return {
            "general": [
                "#motivation",
                "#success",
                "#inspiration",
                "#productivity",
                "#innovation",
            ],
            "tech": ["#AI", "#automation", "#technology", "#coding", "#startup"],
            "business": [
                "#entrepreneur",
                "#leadership",
                "#growth",
                "#strategy",
                "#networking",
            ],
            "lifestyle": [
                "#wellness",
                "#mindfulness",
                "#balance",
                "#goals",
                "#journey",
            ],
        }

    async def optimize_content(
        self,
        content: str,
        target_platforms: list[str] = None,
        content_category: str = "general",
    ) -> ContentOptimization:
        """Optimize content for maximum engagement"""

        if not target_platforms:
            target_platforms = ["twitter", "instagram", "linkedin"]

        try:
            # Analyze original content
            content_analysis = await self._analyze_content(content)

            # Generate optimized version
            optimized_content = await self._generate_optimized_content(
                content,
                content_analysis,
                target_platforms[0],
            )

            # Create platform-specific adaptations
            platform_adaptations = {}
            for platform in target_platforms:
                platform_adaptations[platform] = await self._adapt_for_platform(
                    optimized_content,
                    platform,
                )

            # Generate hashtag recommendations
            recommended_hashtags = await self._recommend_hashtags(
                content,
                content_category,
                target_platforms[0],
            )

            # Determine optimal posting time
            optimal_time = self._get_optimal_posting_time(target_platforms[0])

            # Calculate expected engagement
            engagement_rate = await self._predict_engagement_rate(
                optimized_content,
                target_platforms[0],
                recommended_hashtags,
            )

            # Score content quality
            content_score = self._score_content(optimized_content, target_platforms[0])

            # Generate optimization suggestions
            suggestions = await self._generate_optimization_suggestions(
                content,
                optimized_content,
                content_analysis,
            )

            return ContentOptimization(
                original_content=content,
                optimized_content=optimized_content,
                confidence_score=content_analysis["confidence"],
                platform_adaptations=platform_adaptations,
                recommended_hashtags=recommended_hashtags,
                optimal_posting_time=optimal_time,
                expected_engagement_rate=engagement_rate,
                content_score=content_score,
                optimization_suggestions=suggestions,
            )

        except Exception as e:
            self.logger.error(f"Content optimization failed: {e}")
            return ContentOptimization(
                original_content=content,
                optimized_content=content,
                confidence_score=0.0,
                platform_adaptations={},
                recommended_hashtags=[],
                optimal_posting_time="12:00",
                expected_engagement_rate=0.0,
                content_score=0.0,
                optimization_suggestions=[f"Optimization failed: {str(e)}"],
            )

    async def _analyze_content(self, content: str) -> dict:
        """Analyze content characteristics"""
        analysis = {
            "word_count": len(content.split()),
            "character_count": len(content),
            "sentences": len(content.split(".")),
            "language": "en",  # Default
            "sentiment": 0.0,
            "readability": 0.0,
            "keywords": [],
            "confidence": 0.8,
        }

        try:
            # Detect language
            analysis["language"] = detect(content)
        except BaseException:
            pass

        try:
            # Sentiment analysis
            blob = TextBlob(content)
            analysis["sentiment"] = blob.sentiment.polarity
        except BaseException:
            pass

        try:
            # Extract keywords (simple approach)
            words = re.findall(r"\b\w+\b", content.lower())
            word_freq = {}
            for word in words:
                if len(word) > 3:
                    word_freq[word] = word_freq.get(word, 0) + 1

            # Top keywords
            analysis["keywords"] = sorted(
                word_freq.keys(),
                key=word_freq.get,
                reverse=True,
            )[:10]
        except BaseException:
            pass

        # Calculate readability (simple Flesch-Kincaid approximation)
        if analysis["sentences"] > 0 and analysis["word_count"] > 0:
            avg_sentence_length = analysis["word_count"] / analysis["sentences"]
            # Simplified readability score (0-100, higher is more readable)
            analysis["readability"] = max(0, min(100, 100 - (avg_sentence_length * 2)))

        return analysis

    async def _generate_optimized_content(
        self,
        content: str,
        analysis: dict,
        primary_platform: str,
    ) -> str:
        """Generate optimized version of content using AI"""

        if not self.openai_api_key:
            return self._simple_optimization(content, primary_platform)

        try:
            platform_config = self.platform_configs[primary_platform]

            prompt = f"""
            Optimize the following social media content for {primary_platform}:

            Original content: "{content}"

            Requirements:
            - Maximum {platform_config["max_length"]} characters
            - Include engaging elements like questions or calls-to-action
            - Maintain the original message and tone
            - Make it more engaging and shareable
            - Use appropriate language for {primary_platform} audience

            Return only the optimized content, no explanations.
            """

            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7,
            )

            optimized = response.choices[0].message.content.strip()

            # Ensure it meets platform requirements
            if len(optimized) > platform_config["max_length"]:
                optimized = optimized[: platform_config["max_length"] - 3] + "..."

            return optimized

        except Exception as e:
            self.logger.warning(f"AI optimization failed, using fallback: {e}")
            return self._simple_optimization(content, primary_platform)

    def _simple_optimization(self, content: str, platform: str) -> str:
        """Simple rule-based content optimization"""
        platform_config = self.platform_configs[platform]

        # Truncate if too long
        if len(content) > platform_config["max_length"]:
            content = content[: platform_config["max_length"] - 3] + "..."

        # Add engagement elements
        engagement_keywords = platform_config["engagement_keywords"]

        # Add a question or call-to-action if missing
        if not any(
            keyword in content.lower() for keyword in ["?", "what", "how", "why"]
        ):
            if platform == "twitter":
                content += " What are your thoughts?"
            elif platform == "instagram":
                content += " Double tap if you agree! 💙"
            elif platform == "linkedin":
                content += " What's your experience with this?"

        return content

    async def _adapt_for_platform(self, content: str, platform: str) -> str:
        """Adapt content for specific platform"""
        platform_config = self.platform_configs[platform]
        adapted_content = content

        # Platform-specific adaptations
        if platform == "twitter":
            # Twitter is conversational and concise
            if len(adapted_content) > 240:
                adapted_content = adapted_content[:237] + "..."
            # Add Twitter-specific elements
            if not any(x in adapted_content for x in ["@", "#"]):
                adapted_content += " #TwitterTips"

        elif platform == "instagram":
            # Instagram is visual and hashtag-heavy
            if not adapted_content.endswith("."):
                adapted_content += "."
            adapted_content += "\n\n"  # Space for hashtags

        elif platform == "linkedin":
            # LinkedIn is professional
            if not adapted_content.startswith(("I", "We", "The", "A")):
                adapted_content = "I wanted to share " + adapted_content.lower()
            adapted_content += "\n\n#LinkedIn #Professional"

        elif platform == "tiktok":
            # TikTok is trendy and uses lots of hashtags
            adapted_content = adapted_content[:100]  # Keep it short
            adapted_content += " #FYP #Trending"

        elif platform == "reddit":
            # Reddit prefers longer, detailed content
            # No hashtags on Reddit
            adapted_content = re.sub(r"#\w+", "", adapted_content)

        return adapted_content.strip()

    async def _recommend_hashtags(
        self,
        content: str,
        category: str,
        platform: str,
    ) -> list[str]:
        """Recommend relevant hashtags"""
        platform_config = self.platform_configs[platform]
        max_hashtags = platform_config["hashtag_limit"]
        optimal_count = platform_config["optimal_hashtag_count"]

        if max_hashtags == 0:  # No hashtags for platforms like Reddit
            return []

        recommended = []

        # Add category-specific trending hashtags
        if category in self.trending_hashtags:
            recommended.extend(self.trending_hashtags[category][:2])

        # Add general trending hashtags
        recommended.extend(self.trending_hashtags.get("general", [])[:2])

        # Extract keywords from content and create hashtags
        content_keywords = self._extract_keywords(content)
        for keyword in content_keywords[:3]:
            hashtag = f"#{keyword.lower().replace(' ', '')}"
            if hashtag not in recommended:
                recommended.append(hashtag)

        # Platform-specific hashtags
        if platform == "instagram":
            recommended.extend(["#instagood", "#photooftheday", "#love"])
        elif platform == "twitter":
            recommended.extend(["#Twitter", "#SocialMedia"])
        elif platform == "tiktok":
            recommended.extend(["#fyp", "#foryou", "#viral"])
        elif platform == "linkedin":
            recommended.extend(["#LinkedIn", "#Professional", "#Career"])

        # Remove duplicates and limit
        unique_hashtags = list(dict.fromkeys(recommended))
        return unique_hashtags[: min(optimal_count, max_hashtags)]

    def _extract_keywords(self, content: str) -> list[str]:
        """Extract relevant keywords from content"""
        # Simple keyword extraction
        words = re.findall(r"\b[a-zA-Z]{4,}\b", content)

        # Filter out common words
        stop_words = {
            "this",
            "that",
            "with",
            "have",
            "will",
            "from",
            "they",
            "been",
            "were",
            "said",
            "each",
            "which",
            "their",
            "time",
            "more",
        }

        keywords = [word.lower() for word in words if word.lower() not in stop_words]

        # Return unique keywords
        return list(dict.fromkeys(keywords))[:10]

    def _get_optimal_posting_time(self, platform: str) -> str:
        """Get optimal posting time for platform"""
        platform_config = self.platform_configs[platform]
        return platform_config["best_times"][0]  # Return first/best time

    async def _predict_engagement_rate(
        self,
        content: str,
        platform: str,
        hashtags: list[str],
    ) -> float:
        """Predict expected engagement rate"""
        # This is a simplified prediction model
        # In production, you'd use ML models trained on historical data

        base_rate = {
            "twitter": 1.5,
            "instagram": 3.0,
            "linkedin": 2.0,
            "tiktok": 8.0,
            "reddit": 4.0,
        }.get(platform, 2.0)

        # Adjust based on content factors
        multipliers = 1.0

        # Length optimization
        platform_config = self.platform_configs[platform]
        if len(content) <= platform_config["max_length"] * 0.8:
            multipliers += 0.1

        # Hashtag optimization
        optimal_hashtag_count = platform_config["optimal_hashtag_count"]
        if len(hashtags) == optimal_hashtag_count:
            multipliers += 0.2
        elif abs(len(hashtags) - optimal_hashtag_count) <= 2:
            multipliers += 0.1

        # Engagement elements
        engagement_indicators = ["?", "!", "share", "comment", "like", "follow"]
        if any(indicator in content.lower() for indicator in engagement_indicators):
            multipliers += 0.15

        # Sentiment boost for positive content
        try:
            sentiment = TextBlob(content).sentiment.polarity
            if sentiment > 0.1:
                multipliers += 0.1
        except BaseException:
            pass

        return min(base_rate * multipliers, 15.0)  # Cap at 15%

    def _score_content(self, content: str, platform: str) -> float:
        """Score content quality (0-100)"""
        scores = {}

        # Readability score
        word_count = len(content.split())
        sentence_count = len(content.split("."))
        if sentence_count > 0:
            avg_sentence_length = word_count / sentence_count
            readability = max(0, min(100, 100 - (avg_sentence_length * 1.5)))
        else:
            readability = 50
        scores["readability"] = readability

        # Length optimization
        platform_config = self.platform_configs[platform]
        optimal_length = platform_config["max_length"] * 0.7
        length_score = 100 - abs(len(content) - optimal_length) / optimal_length * 100
        scores["length_optimization"] = max(0, min(100, length_score))

        # Engagement potential
        engagement_indicators = ["?", "!", "share", "comment", "what", "how", "why"]
        engagement_count = sum(
            1 for indicator in engagement_indicators if indicator in content.lower()
        )
        scores["engagement_potential"] = min(100, engagement_count * 25)

        # Sentiment score
        try:
            sentiment = TextBlob(content).sentiment.polarity
            sentiment_score = (sentiment + 1) * 50  # Convert -1,1 to 0,100
        except BaseException:
            sentiment_score = 50
        scores["sentiment"] = sentiment_score

        # Platform alignment (simplified)
        platform_keywords = self.platform_configs[platform]["engagement_keywords"]
        alignment_score = sum(
            20 for keyword in platform_keywords if keyword in content.lower()
        )
        scores["platform_alignment"] = min(100, alignment_score)

        # Hashtag optimization (if hashtags are supported)
        if platform != "reddit":
            hashtag_count = len(re.findall(r"#\w+", content))
            optimal_count = self.platform_configs[platform]["optimal_hashtag_count"]
            hashtag_score = 100 - abs(hashtag_count - optimal_count) * 10
            scores["hashtag_optimization"] = max(0, min(100, hashtag_score))
        else:
            scores["hashtag_optimization"] = 100

        # Calculate weighted average
        total_score = sum(
            scores[metric] * self.scoring_weights[metric] for metric in scores
        )

        return round(total_score, 1)

    async def _generate_optimization_suggestions(
        self,
        original: str,
        optimized: str,
        analysis: dict,
    ) -> list[str]:
        """Generate actionable optimization suggestions"""
        suggestions = []

        # Length suggestions
        if len(original) > 280:
            suggestions.append(
                "Consider breaking long content into multiple posts or threads",
            )

        # Engagement suggestions
        if "?" not in original and "?" not in optimized:
            suggestions.append("Add a question to encourage audience interaction")

        # Hashtag suggestions
        hashtag_count = len(re.findall(r"#\w+", original))
        if hashtag_count == 0:
            suggestions.append("Add relevant hashtags to increase discoverability")
        elif hashtag_count > 10:
            suggestions.append("Reduce hashtag count for better readability")

        # Readability suggestions
        if analysis["readability"] < 50:
            suggestions.append(
                "Simplify language and use shorter sentences for better readability",
            )

        # Sentiment suggestions
        if analysis["sentiment"] < -0.1:
            suggestions.append(
                "Consider adding more positive language to improve engagement",
            )

        # Call-to-action suggestions
        cta_indicators = ["share", "comment", "like", "follow", "subscribe", "click"]
        if not any(cta in original.lower() for cta in cta_indicators):
            suggestions.append("Add a clear call-to-action to drive engagement")

        return suggestions[:5]  # Limit to top 5 suggestions

    async def analyze_hashtag_performance(
        self,
        hashtags: list[str],
        platform: str,
    ) -> list[HashtagAnalysis]:
        """Analyze hashtag performance and potential"""
        analyses = []

        for hashtag in hashtags:
            # This would normally query hashtag analytics APIs
            # Simplified analysis for demonstration
            analysis = HashtagAnalysis(
                hashtag=hashtag,
                popularity_score=self._calculate_hashtag_popularity(hashtag),
                competition_level=self._determine_competition_level(hashtag),
                relevance_score=self._calculate_relevance_score(hashtag, platform),
                trending_potential=self._calculate_trending_potential(hashtag),
                recommended=True,
            )

            # Determine if hashtag is recommended
            analysis.recommended = (
                analysis.popularity_score > 0.3
                and analysis.relevance_score > 0.5
                and analysis.competition_level != "high"
            )

            analyses.append(analysis)

        return analyses

    def _calculate_hashtag_popularity(self, hashtag: str) -> float:
        """Calculate hashtag popularity (0-1)"""
        # Simplified popularity calculation
        # In production, this would use real hashtag data

        # Common hashtags get higher scores
        common_hashtags = [
            "#love",
            "#instagood",
            "#photooftheday",
            "#fashion",
            "#beautiful",
        ]
        if hashtag.lower() in [h.lower() for h in common_hashtags]:
            return 0.9

        # Tech hashtags
        tech_hashtags = ["#AI", "#tech", "#automation", "#coding", "#innovation"]
        if hashtag.lower() in [h.lower() for h in tech_hashtags]:
            return 0.7

        # Default based on length (shorter = more popular typically)
        return max(0.1, 1.0 - (len(hashtag) - 3) * 0.05)

    def _determine_competition_level(self, hashtag: str) -> str:
        """Determine competition level for hashtag"""
        # Simplified competition analysis
        popularity = self._calculate_hashtag_popularity(hashtag)

        if popularity > 0.8:
            return "high"
        if popularity > 0.5:
            return "medium"
        return "low"

    def _calculate_relevance_score(self, hashtag: str, platform: str) -> float:
        """Calculate hashtag relevance for platform"""
        platform_tags = {
            "twitter": ["#twitter", "#socialmedia", "#news", "#trending"],
            "instagram": ["#instagram", "#photo", "#insta", "#ig"],
            "linkedin": ["#linkedin", "#professional", "#career", "#business"],
            "tiktok": ["#tiktok", "#fyp", "#viral", "#trending"],
        }

        if hashtag.lower() in [h.lower() for h in platform_tags.get(platform, [])]:
            return 1.0

        # General relevance based on hashtag characteristics
        return 0.7 if len(hashtag) <= 15 else 0.4

    def _calculate_trending_potential(self, hashtag: str) -> float:
        """Calculate trending potential for hashtag"""
        # Simplified trending calculation
        # Real implementation would use trend data

        # Shorter hashtags tend to trend more
        length_score = max(0, 1.0 - (len(hashtag) - 3) * 0.1)

        # Hashtags with numbers might be event-specific
        has_numbers = bool(re.search(r"\d", hashtag))
        number_bonus = 0.2 if has_numbers else 0

        return min(1.0, length_score + number_bonus)


# Usage example and testing


async def demo_content_optimization():
    """Demonstrate content optimization features"""

    # Initialize engine
    engine = ContentOptimizationEngine()

    # Sample content
    original_content = """
    Just launched our new automation tool that helps businesses save time and increase productivity.
    It's been a game changer for our team and I think you'll love it too!
    """

    # Optimize for multiple platforms
    optimization = await engine.optimize_content(
        content=original_content.strip(),
        target_platforms=["twitter", "instagram", "linkedin"],
        content_category="tech",
    )

    print("=== Content Optimization Results ===")
    print(f"Original: {optimization.original_content}")
    print(f"Optimized: {optimization.optimized_content}")
    print(f"Content Score: {optimization.content_score}")
    print(f"Expected Engagement: {optimization.expected_engagement_rate}%")
    print(f"Recommended Hashtags: {optimization.recommended_hashtags}")
    print(f"Optimal Time: {optimization.optimal_posting_time}")

    print("\n=== Platform Adaptations ===")
    for platform, adapted_content in optimization.platform_adaptations.items():
        print(f"{platform.title()}: {adapted_content}")

    print("\n=== Optimization Suggestions ===")
    for suggestion in optimization.optimization_suggestions:
        print(f"• {suggestion}")

    # Analyze hashtags
    hashtag_analyses = await engine.analyze_hashtag_performance(
        optimization.recommended_hashtags,
        "twitter",
    )

    print("\n=== Hashtag Analysis ===")
    for analysis in hashtag_analyses:
        print(
            f"{analysis.hashtag}: Popularity={analysis.popularity_score:.2f}, "
            f"Competition={analysis.competition_level}, Recommended={analysis.recommended}",
        )


if __name__ == "__main__":
    asyncio.run(demo_content_optimization())

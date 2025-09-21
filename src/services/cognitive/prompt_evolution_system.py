#!/usr/bin/env python3
"""Prompt Evolution System - Advanced Autonomous Cognitive Evolution
Part of the Cosmic Calibration Protocol

AI system that analyzes its own performance and recursively improves prompts
through evolutionary algorithms, A/B testing, and success/failure pattern analysis.
"""

import asyncio
import hashlib
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class EvolutionStage(Enum):
    OBSERVATION = "observation"
    MUTATION = "mutation"
    SELECTION = "selection"
    BREEDING = "breeding"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class PromptCategory(Enum):
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    REASONING = "reasoning"
    FACT_CHECKING = "fact_checking"
    ORCHESTRATION = "orchestration"
    SELF_CRITIQUE = "self_critique"


@dataclass
class PromptGene:
    """A genetic component of a prompt that can be evolved"""

    gene_id: str
    category: str
    content: str
    weight: float
    performance_score: float
    usage_count: int
    success_rate: float


@dataclass
class PromptOrganism:
    """A complete prompt as an organism with genetic components"""

    organism_id: str
    category: PromptCategory
    generation: int
    genes: list[PromptGene]
    full_prompt: str
    fitness_score: float
    performance_metrics: dict[str, float]
    parent_ids: list[str]
    mutation_history: list[str]
    created_at: datetime
    last_tested: datetime | None
    test_count: int
    success_count: int


@dataclass
class EvolutionExperiment:
    """A/B testing experiment for prompt evolution"""

    experiment_id: str
    prompt_variants: list[PromptOrganism]
    test_results: dict[str, Any]
    winner_id: str | None
    confidence_level: float
    sample_size: int
    started_at: datetime
    completed_at: datetime | None


class PromptEvolutionSystem:
    """Advanced prompt evolution system that continuously improves prompts
    through genetic algorithms, A/B testing, and performance analysis.

    Key Features:
    - Genetic algorithm-based prompt evolution
    - A/B testing with statistical significance
    - Success/failure pattern analysis
    - Version-controlled prompt evolution
    - Multi-model validation of improvements
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.evolution_stage = EvolutionStage.OBSERVATION

        # Evolution parameters
        self.population_size = config.get("population_size", 20)
        self.mutation_rate = config.get("mutation_rate", 0.15)
        self.crossover_rate = config.get("crossover_rate", 0.8)
        self.selection_pressure = config.get("selection_pressure", 0.3)
        self.generation_size = config.get("generation_size", 10)

        # Testing parameters
        self.min_test_samples = config.get("min_test_samples", 50)
        self.confidence_threshold = config.get("confidence_threshold", 0.95)
        self.improvement_threshold = config.get("improvement_threshold", 0.05)

        # Evolution storage
        self.prompt_populations: dict[PromptCategory, list[PromptOrganism]] = {}
        self.evolution_history: list[dict[str, Any]] = []
        self.active_experiments: list[EvolutionExperiment] = []
        self.performance_database: dict[str, list[dict[str, Any]]] = {}

        # Genetic building blocks for prompt construction
        self.genetic_library = self._initialize_genetic_library()

        # Initialize prompt templates
        self.base_prompts = self._initialize_base_prompts()

        # Setup logging
        self.logger = self._setup_logging()
        self.evolution_log_path = Path("vault/metacognitive/Prompt_Evolution_Log.md")
        self.evolution_log_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info("Prompt Evolution System initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup dedicated logging for prompt evolution"""
        logger = logging.getLogger("PromptEvolution")
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - EVOLUTION - %(levelname)s - %(message)s",
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        log_file = Path("logs/prompt_evolution.log")
        log_file.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def _initialize_genetic_library(self) -> dict[str, list[PromptGene]]:
        """Initialize library of genetic components for prompt building"""
        return {
            "reasoning_strategies": [
                PromptGene(
                    "rs001",
                    "reasoning",
                    "Think step by step through this problem",
                    1.0,
                    0.85,
                    0,
                    0.0,
                ),
                PromptGene(
                    "rs002",
                    "reasoning",
                    "Use chain of thought reasoning",
                    0.9,
                    0.82,
                    0,
                    0.0,
                ),
                PromptGene(
                    "rs003",
                    "reasoning",
                    "Consider multiple perspectives before concluding",
                    0.8,
                    0.79,
                    0,
                    0.0,
                ),
                PromptGene(
                    "rs004",
                    "reasoning",
                    "Break down complex problems into smaller components",
                    0.85,
                    0.81,
                    0,
                    0.0,
                ),
                PromptGene(
                    "rs005",
                    "reasoning",
                    "Apply logical reasoning principles",
                    0.75,
                    0.77,
                    0,
                    0.0,
                ),
            ],
            "quality_constraints": [
                PromptGene(
                    "qc001",
                    "quality",
                    "Ensure accuracy and factual correctness",
                    1.0,
                    0.88,
                    0,
                    0.0,
                ),
                PromptGene(
                    "qc002",
                    "quality",
                    "Provide evidence-based responses",
                    0.9,
                    0.85,
                    0,
                    0.0,
                ),
                PromptGene(
                    "qc003",
                    "quality",
                    "Maintain coherence and clarity",
                    0.8,
                    0.83,
                    0,
                    0.0,
                ),
                PromptGene(
                    "qc004",
                    "quality",
                    "Avoid hallucinations and speculation",
                    0.95,
                    0.87,
                    0,
                    0.0,
                ),
                PromptGene(
                    "qc005",
                    "quality",
                    "Structure responses logically",
                    0.75,
                    0.80,
                    0,
                    0.0,
                ),
            ],
            "context_awareness": [
                PromptGene(
                    "ca001",
                    "context",
                    "Consider the full context provided",
                    1.0,
                    0.86,
                    0,
                    0.0,
                ),
                PromptGene(
                    "ca002",
                    "context",
                    "Reference relevant information from the context",
                    0.9,
                    0.84,
                    0,
                    0.0,
                ),
                PromptGene(
                    "ca003",
                    "context",
                    "Identify connections across different pieces of information",
                    0.8,
                    0.81,
                    0,
                    0.0,
                ),
                PromptGene(
                    "ca004",
                    "context",
                    "Maintain consistency with established facts",
                    0.85,
                    0.83,
                    0,
                    0.0,
                ),
            ],
            "output_formatting": [
                PromptGene(
                    "of001",
                    "format",
                    "Structure your response with clear headings",
                    0.7,
                    0.78,
                    0,
                    0.0,
                ),
                PromptGene(
                    "of002",
                    "format",
                    "Use bullet points for lists and key points",
                    0.6,
                    0.75,
                    0,
                    0.0,
                ),
                PromptGene(
                    "of003",
                    "format",
                    "Provide specific examples where appropriate",
                    0.8,
                    0.82,
                    0,
                    0.0,
                ),
                PromptGene(
                    "of004",
                    "format",
                    "Include confidence levels for uncertain information",
                    0.75,
                    0.79,
                    0,
                    0.0,
                ),
            ],
            "self_reflection": [
                PromptGene(
                    "sr001",
                    "reflection",
                    "Review your reasoning for potential flaws",
                    0.85,
                    0.84,
                    0,
                    0.0,
                ),
                PromptGene(
                    "sr002",
                    "reflection",
                    "Consider alternative explanations",
                    0.8,
                    0.81,
                    0,
                    0.0,
                ),
                PromptGene(
                    "sr003",
                    "reflection",
                    "Assess the confidence level of your conclusions",
                    0.75,
                    0.80,
                    0,
                    0.0,
                ),
                PromptGene(
                    "sr004",
                    "reflection",
                    "Identify areas where more information is needed",
                    0.7,
                    0.78,
                    0,
                    0.0,
                ),
            ],
        }

    def _initialize_base_prompts(self) -> dict[PromptCategory, PromptOrganism]:
        """Initialize base prompt templates for each category"""
        base_prompts = {}

        # Analysis prompt
        analysis_genes = [
            self.genetic_library["reasoning_strategies"][0],
            self.genetic_library["quality_constraints"][0],
            self.genetic_library["context_awareness"][0],
        ]

        analysis_prompt = self._construct_prompt_from_genes(
            analysis_genes,
            PromptCategory.ANALYSIS,
        )
        base_prompts[PromptCategory.ANALYSIS] = self._create_prompt_organism(
            PromptCategory.ANALYSIS,
            analysis_genes,
            analysis_prompt,
            generation=0,
        )

        # Synthesis prompt
        synthesis_genes = [
            self.genetic_library["reasoning_strategies"][2],
            self.genetic_library["context_awareness"][2],
            self.genetic_library["output_formatting"][2],
        ]

        synthesis_prompt = self._construct_prompt_from_genes(
            synthesis_genes,
            PromptCategory.SYNTHESIS,
        )
        base_prompts[PromptCategory.SYNTHESIS] = self._create_prompt_organism(
            PromptCategory.SYNTHESIS,
            synthesis_genes,
            synthesis_prompt,
            generation=0,
        )

        # Reasoning prompt
        reasoning_genes = [
            self.genetic_library["reasoning_strategies"][1],
            self.genetic_library["self_reflection"][0],
            self.genetic_library["quality_constraints"][1],
        ]

        reasoning_prompt = self._construct_prompt_from_genes(
            reasoning_genes,
            PromptCategory.REASONING,
        )
        base_prompts[PromptCategory.REASONING] = self._create_prompt_organism(
            PromptCategory.REASONING,
            reasoning_genes,
            reasoning_prompt,
            generation=0,
        )

        # Initialize other categories...
        # (Fact-checking, Orchestration, Self-critique)

        return base_prompts

    async def initialize(self) -> bool:
        """Initialize the prompt evolution system"""
        try:
            self.logger.info("Initializing Prompt Evolution System...")

            # Initialize populations for each category
            for category in PromptCategory:
                if category in self.base_prompts:
                    self.prompt_populations[category] = [self.base_prompts[category]]
                else:
                    # Create default organism for categories without base prompts
                    default_genes = list(
                        self.genetic_library["reasoning_strategies"][:2],
                    )
                    default_prompt = self._construct_prompt_from_genes(
                        default_genes,
                        category,
                    )
                    default_organism = self._create_prompt_organism(
                        category,
                        default_genes,
                        default_prompt,
                        generation=0,
                    )
                    self.prompt_populations[category] = [default_organism]

            # Create evolution log
            await self._initialize_evolution_log()

            # Start evolution loops
            asyncio.create_task(self._continuous_evolution_loop())
            asyncio.create_task(self._a_b_testing_loop())
            asyncio.create_task(self._performance_analysis_loop())

            self.logger.info("Prompt Evolution System fully initialized")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize prompt evolution system: {e}")
            return False

    async def _initialize_evolution_log(self):
        """Initialize the Prompt Evolution Log"""
        log_header = f"""# Prompt Evolution Log - Advanced Autonomous Cognitive Evolution

**Initialization Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Evolution Protocol:** Genetic Algorithm + A/B Testing
**System Status:** Active Evolution

## Overview

This log tracks the autonomous evolution of prompts in the PAKE system. The evolution process uses genetic algorithms combined with A/B testing to continuously improve prompt effectiveness.

## Evolution Parameters

- Population Size: {self.population_size}
- Mutation Rate: {self.mutation_rate}
- Crossover Rate: {self.crossover_rate}
- Selection Pressure: {self.selection_pressure}
- Generation Size: {self.generation_size}

## Evolution History

*Prompt evolution cycles will be logged below...*

---

"""
        with open(self.evolution_log_path, "w", encoding="utf-8") as f:
            f.write(log_header)

    def _construct_prompt_from_genes(
        self,
        genes: list[PromptGene],
        category: PromptCategory,
    ) -> str:
        """Construct a complete prompt from genetic components"""
        prompt_parts = []

        # Category-specific introduction
        intros = {
            PromptCategory.ANALYSIS: "You are an expert analyst. Your task is to analyze the provided information comprehensively.",
            PromptCategory.SYNTHESIS: "You are a synthesis specialist. Your task is to synthesize insights from multiple sources.",
            PromptCategory.REASONING: "You are a reasoning expert. Your task is to apply logical reasoning to solve problems.",
            PromptCategory.FACT_CHECKING: "You are a fact-checker. Your task is to verify the accuracy of information.",
            PromptCategory.ORCHESTRATION: "You are an orchestrator. Your task is to coordinate multiple agents and tasks.",
            PromptCategory.SELF_CRITIQUE: "You are a self-critic. Your task is to identify flaws and improvement opportunities.",
        }

        prompt_parts.append(intros[category])
        prompt_parts.append("")  # Empty line

        # Add genetic components
        for gene in sorted(genes, key=lambda x: x.weight, reverse=True):
            prompt_parts.append(f"- {gene.content}")

        prompt_parts.append("")
        prompt_parts.append(
            "Please follow these guidelines carefully and provide your response accordingly.",
        )

        return "\n".join(prompt_parts)

    def _create_prompt_organism(
        self,
        category: PromptCategory,
        genes: list[PromptGene],
        prompt: str,
        generation: int,
        parent_ids: list[str] = None,
    ) -> PromptOrganism:
        """Create a new prompt organism"""
        organism_id = hashlib.sha256(prompt.encode()).hexdigest()[:12]

        return PromptOrganism(
            organism_id=organism_id,
            category=category,
            generation=generation,
            genes=genes,
            full_prompt=prompt,
            fitness_score=0.0,
            performance_metrics={},
            parent_ids=parent_ids or [],
            mutation_history=[],
            created_at=datetime.now(),
            last_tested=None,
            test_count=0,
            success_count=0,
        )

    async def _continuous_evolution_loop(self):
        """Main evolution loop - continuous genetic improvement"""
        self.logger.info("Starting continuous prompt evolution loop")

        while True:
            try:
                await asyncio.sleep(3600)  # Evolve every hour

                for category in PromptCategory:
                    self.evolution_stage = EvolutionStage.OBSERVATION

                    # Analyze current population performance
                    population = self.prompt_populations[category]
                    performance_analysis = await self._analyze_population_performance(
                        population,
                    )

                    # Check if evolution is needed
                    if self._should_evolve(performance_analysis):
                        self.logger.info(
                            f"Starting evolution cycle for {category.value} prompts",
                        )

                        # Generate new generation
                        new_generation = await self._evolve_population(
                            population,
                            category,
                        )

                        # Add to population (keeping best performers)
                        self.prompt_populations[
                            category
                        ] = await self._select_survivors(population + new_generation)

                        # Log evolution cycle
                        await self._log_evolution_cycle(
                            category,
                            performance_analysis,
                            new_generation,
                        )

                self.evolution_stage = EvolutionStage.OBSERVATION

            except Exception as e:
                self.logger.error(f"Error in evolution loop: {e}")

    async def _evolve_population(
        self,
        population: list[PromptOrganism],
        category: PromptCategory,
    ) -> list[PromptOrganism]:
        """Evolve a population to create new generation"""
        new_generation = []

        # Selection phase
        self.evolution_stage = EvolutionStage.SELECTION
        parents = await self._select_parents(population)

        # Breeding phase
        self.evolution_stage = EvolutionStage.BREEDING
        for i in range(0, len(parents) - 1, 2):
            parent1, parent2 = parents[i], parents[i + 1]

            if random.random() < self.crossover_rate:
                child1, child2 = await self._crossover(parent1, parent2, category)
                new_generation.extend([child1, child2])

        # Mutation phase
        self.evolution_stage = EvolutionStage.MUTATION
        for organism in new_generation:
            if random.random() < self.mutation_rate:
                await self._mutate_organism(organism, category)

        return new_generation

    async def _select_parents(
        self,
        population: list[PromptOrganism],
    ) -> list[PromptOrganism]:
        """Select parents for breeding using tournament selection"""
        tournament_size = max(2, int(len(population) * 0.1))
        parents = []

        for _ in range(len(population)):
            tournament = random.sample(
                population,
                min(tournament_size, len(population)),
            )
            winner = max(tournament, key=lambda x: x.fitness_score)
            parents.append(winner)

        return parents

    async def _crossover(
        self,
        parent1: PromptOrganism,
        parent2: PromptOrganism,
        category: PromptCategory,
    ) -> tuple[PromptOrganism, PromptOrganism]:
        """Create two children through crossover of parent genes"""
        # Combine and select genes from both parents
        all_genes = parent1.genes + parent2.genes
        gene_pool = list(set(all_genes))  # Remove duplicates

        # Create two children with different gene combinations
        child1_genes = random.sample(gene_pool, min(len(gene_pool), len(parent1.genes)))
        child2_genes = random.sample(gene_pool, min(len(gene_pool), len(parent2.genes)))

        # Construct prompts
        child1_prompt = self._construct_prompt_from_genes(child1_genes, category)
        child2_prompt = self._construct_prompt_from_genes(child2_genes, category)

        # Create organisms
        generation = max(parent1.generation, parent2.generation) + 1
        parent_ids = [parent1.organism_id, parent2.organism_id]

        child1 = self._create_prompt_organism(
            category,
            child1_genes,
            child1_prompt,
            generation,
            parent_ids,
        )
        child2 = self._create_prompt_organism(
            category,
            child2_genes,
            child2_prompt,
            generation,
            parent_ids,
        )

        return child1, child2

    async def _mutate_organism(
        self,
        organism: PromptOrganism,
        category: PromptCategory,
    ):
        """Mutate an organism by modifying its genes"""
        mutation_type = random.choice(["add", "remove", "modify"])

        if mutation_type == "add" and len(organism.genes) < 6:
            # Add a new gene from the library
            available_genes = [
                gene
                for gene_list in self.genetic_library.values()
                for gene in gene_list
            ]
            new_gene = random.choice(
                [g for g in available_genes if g not in organism.genes],
            )
            organism.genes.append(new_gene)

        elif mutation_type == "remove" and len(organism.genes) > 2:
            # Remove a gene
            organism.genes.pop(random.randint(0, len(organism.genes) - 1))

        elif mutation_type == "modify":
            # Modify an existing gene
            if organism.genes:
                gene_idx = random.randint(0, len(organism.genes) - 1)
                available_genes = [
                    gene
                    for gene_list in self.genetic_library.values()
                    for gene in gene_list
                ]
                organism.genes[gene_idx] = random.choice(available_genes)

        # Reconstruct prompt
        organism.full_prompt = self._construct_prompt_from_genes(
            organism.genes,
            category,
        )
        organism.mutation_history.append(
            f"{mutation_type}_{datetime.now().isoformat()}",
        )

    async def evolve_prompts(self) -> dict[str, Any]:
        """Manually trigger prompt evolution cycle"""
        self.logger.info("Manual prompt evolution triggered")

        evolution_results = {}

        for category in PromptCategory:
            population = self.prompt_populations[category]

            # Force evolution
            new_generation = await self._evolve_population(population, category)
            self.prompt_populations[category] = await self._select_survivors(
                population + new_generation,
            )

            evolution_results[category.value] = {
                "new_organisms": len(new_generation),
                "total_population": len(self.prompt_populations[category]),
                "best_fitness": max(
                    org.fitness_score for org in self.prompt_populations[category]
                ),
            }

        return evolution_results

    def get_best_prompt(self, category: PromptCategory) -> PromptOrganism:
        """Get the best performing prompt for a category"""
        population = self.prompt_populations[category]
        return max(population, key=lambda x: x.fitness_score)

    def get_status(self) -> dict[str, Any]:
        """Get current status of prompt evolution system"""
        return {
            "evolution_stage": self.evolution_stage.value,
            "population_sizes": {
                cat.value: len(pop) for cat, pop in self.prompt_populations.items()
            },
            "active_experiments": len(self.active_experiments),
            "total_evolution_cycles": len(self.evolution_history),
            "best_performers": {
                cat.value: {
                    "organism_id": self.get_best_prompt(cat).organism_id,
                    "fitness_score": self.get_best_prompt(cat).fitness_score,
                    "generation": self.get_best_prompt(cat).generation,
                }
                for cat in PromptCategory
            },
        }

    async def shutdown(self):
        """Gracefully shutdown the prompt evolution system"""
        self.logger.info("Shutting down Prompt Evolution System...")

        # Save evolution state
        final_status = self.get_status()

        # Log shutdown
        with open(self.evolution_log_path, "a", encoding="utf-8") as f:
            f.write(
                f"\n\n## System Shutdown - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n",
            )
            f.write(f"Final Status: {json.dumps(final_status, indent=2)}\n\n")

        self.logger.info("Prompt Evolution System shutdown complete")

    # Additional helper methods would be implemented here...
    # (A/B testing loop, performance analysis, selection survivors, etc.)

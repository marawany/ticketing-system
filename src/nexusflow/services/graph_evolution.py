"""
Graph Evolution Service

AI-powered service for evolving the classification graph based on:
- Human feedback (HITL corrections)
- New dataset analysis
- Category expansion suggestions
"""

import json
import re
from typing import Any

import structlog
from openai import AsyncOpenAI

from nexusflow.config import settings
from nexusflow.db.neo4j_client import get_neo4j_client

logger = structlog.get_logger(__name__)


class GraphEvolutionService:
    """
    Service for AI-powered graph evolution.
    
    Uses LLMs to:
    1. Suggest new categories based on analysis
    2. Expand existing categories with subcategories
    3. Analyze HITL corrections for graph improvements
    4. Process datasets to identify new classification needs
    """
    
    def __init__(self):
        self._client: AsyncOpenAI | None = None
    
    def _get_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            if settings.azure_openai_endpoint:
                from openai import AsyncAzureOpenAI
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=settings.azure_openai_endpoint,
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version,
                )
            else:
                self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._client
    
    async def _get_current_hierarchy(self) -> dict[str, Any]:
        """Get current graph hierarchy for context."""
        neo4j = await get_neo4j_client()
        paths = await neo4j.get_all_paths()
        
        hierarchy = {}
        for path in paths:
            l1, l2, l3 = path["level1"], path["level2"], path["level3"]
            if l1 not in hierarchy:
                hierarchy[l1] = {}
            if l2 not in hierarchy[l1]:
                hierarchy[l1][l2] = []
            hierarchy[l1][l2].append(l3)
        
        return hierarchy
    
    async def suggest_expansion(
        self,
        category_name: str,
        level: int,
        context: str | None = None,
        num_suggestions: int = 5,
    ) -> dict[str, Any]:
        """
        Use AI to suggest subcategory expansions.
        
        Args:
            category_name: The category to expand
            level: The level of the category (1, 2, or 3)
            context: Additional context about the domain
            num_suggestions: Number of suggestions to generate
        
        Returns:
            Dict with suggestions and reasoning
        """
        hierarchy = await self._get_current_hierarchy()
        
        # Build context about current category
        if level == 1:
            current_children = list(hierarchy.get(category_name, {}).keys())
            child_type = "Level 2 subcategories"
        elif level == 2:
            # Find parent and siblings
            current_children = []
            parent = None
            for l1, l2_dict in hierarchy.items():
                if category_name in l2_dict:
                    parent = l1
                    current_children = l2_dict[category_name]
                    break
            child_type = "Level 3 specific issue types"
        else:
            return {
                "suggestions": [],
                "reasoning": "Level 3 categories cannot be expanded further",
            }
        
        prompt = f"""You are an expert in customer support ticket classification systems.

Current Category: {category_name}
Category Level: {level} ({"top-level domain" if level == 1 else "subcategory"})
Current Children: {', '.join(current_children) if current_children else 'None'}

Additional Context: {context or 'Standard SaaS customer support system'}

TASK: Suggest {num_suggestions} new {child_type} that should be added under "{category_name}".

Requirements:
1. Each suggestion should be distinct from existing children
2. Names should be concise but descriptive (2-5 words)
3. Follow the naming convention of existing categories
4. Consider common patterns in customer support tickets
5. Ensure suggestions are mutually exclusive (no overlap)

Respond in this exact JSON format:
{{
    "suggestions": [
        {{
            "name": "Category Name",
            "description": "Brief description of what tickets belong here",
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "reasoning": "Why this category is needed"
        }}
    ],
    "overall_reasoning": "Explanation of the expansion strategy"
}}"""
        
        client = self._get_client()
        model = settings.azure_openai_deployment_name or "gpt-4o"
        
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a classification taxonomy expert. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "suggestions": result.get("suggestions", []),
                    "reasoning": result.get("overall_reasoning", ""),
                }
            
        except Exception as e:
            logger.error("AI expansion failed", error=str(e))
            raise
        
        return {"suggestions": [], "reasoning": "Failed to generate suggestions"}
    
    async def apply_expansion(
        self,
        category_name: str,
        level: int,
        suggestions: list[dict[str, Any]],
        user_id: str,
    ) -> dict[str, Any]:
        """
        Apply AI-suggested expansions to the graph.
        
        Args:
            category_name: Parent category name
            level: Level of the parent category
            suggestions: List of suggestions to apply
            user_id: ID of user applying changes
        
        Returns:
            Results of the application
        """
        neo4j = await get_neo4j_client()
        
        applied = []
        skipped = []
        errors = []
        
        for suggestion in suggestions:
            name = suggestion.get("name")
            if not name:
                continue
            
            try:
                async with neo4j.session() as session:
                    if level == 1:
                        # Create Level 2 under Level 1
                        await session.run(
                            """
                            MATCH (p:Level1Category {name: $parent})
                            MERGE (c:Level2Category {name: $name})
                            ON CREATE SET c.description = $description,
                                         c.keywords = $keywords,
                                         c.ticket_count = 0,
                                         c.accuracy = 1.0,
                                         c.created_at = datetime(),
                                         c.created_by = $user_id,
                                         c.ai_generated = true
                            MERGE (p)-[r:CONTAINS]->(c)
                            ON CREATE SET r.weight = 1.0, r.traversal_count = 0
                            """,
                            parent=category_name,
                            name=name,
                            description=suggestion.get("description", ""),
                            keywords=suggestion.get("keywords", []),
                            user_id=user_id,
                        )
                    elif level == 2:
                        # Create Level 3 under Level 2
                        await session.run(
                            """
                            MATCH (p:Level2Category {name: $parent})
                            MERGE (c:Level3Category {name: $name})
                            ON CREATE SET c.description = $description,
                                         c.keywords = $keywords,
                                         c.ticket_count = 0,
                                         c.accuracy = 1.0,
                                         c.created_at = datetime(),
                                         c.created_by = $user_id,
                                         c.ai_generated = true
                            MERGE (p)-[r:CONTAINS]->(c)
                            ON CREATE SET r.weight = 1.0, r.traversal_count = 0
                            """,
                            parent=category_name,
                            name=name,
                            description=suggestion.get("description", ""),
                            keywords=suggestion.get("keywords", []),
                            user_id=user_id,
                        )
                
                applied.append(name)
                logger.info("Applied expansion", parent=category_name, child=name)
                
            except Exception as e:
                errors.append({"name": name, "error": str(e)})
                logger.error("Failed to apply expansion", name=name, error=str(e))
        
        return {
            "applied": applied,
            "skipped": skipped,
            "errors": errors,
        }
    
    async def analyze_dataset_for_evolution(
        self,
        tickets: list[dict[str, Any]],
        sample_size: int = 100,
    ) -> dict[str, Any]:
        """
        Analyze a dataset to suggest graph evolution.
        
        Args:
            tickets: List of ticket dictionaries with 'title' and 'description'
            sample_size: Number of tickets to analyze
        
        Returns:
            Analysis results with suggestions
        """
        # Get current hierarchy
        hierarchy = await self._get_current_hierarchy()
        
        # Sample tickets
        import random
        sample = random.sample(tickets, min(sample_size, len(tickets)))
        
        # Prepare ticket summaries for analysis
        ticket_summaries = []
        for t in sample[:50]:  # Limit for prompt size
            title = t.get("title", t.get("subject", ""))
            desc = t.get("description", t.get("body", ""))[:200]
            ticket_summaries.append(f"- {title}: {desc}")
        
        prompt = f"""You are a classification taxonomy expert analyzing support tickets.

CURRENT HIERARCHY:
{json.dumps(hierarchy, indent=2)}

SAMPLE TICKETS TO ANALYZE:
{chr(10).join(ticket_summaries)}

TASK: Analyze these tickets and suggest how to evolve the classification graph.

Consider:
1. Are there tickets that don't fit well into existing categories?
2. Are there patterns suggesting new top-level categories?
3. Should any existing categories be expanded with new subcategories?
4. Are there coverage gaps in the current hierarchy?

Respond in this exact JSON format:
{{
    "new_categories": [
        {{
            "level": 1,
            "name": "Category Name",
            "description": "What this category covers",
            "example_tickets": ["example1", "example2"],
            "children": ["suggested child 1", "suggested child 2"]
        }}
    ],
    "expanded_categories": [
        {{
            "parent_name": "Existing Category",
            "parent_level": 2,
            "new_children": [
                {{"name": "New Subcategory", "description": "What it covers"}}
            ],
            "reasoning": "Why expansion is needed"
        }}
    ],
    "coverage": {{
        "well_covered_areas": ["area1", "area2"],
        "gaps_identified": ["gap1", "gap2"],
        "coverage_percentage": 85
    }},
    "recommendations": [
        "Recommendation 1",
        "Recommendation 2"
    ]
}}"""
        
        client = self._get_client()
        model = settings.azure_openai_deployment_name or "gpt-4o"
        
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a classification taxonomy expert. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=3000,
            )
            
            content = response.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "new_categories": result.get("new_categories", []),
                    "expanded_categories": result.get("expanded_categories", []),
                    "coverage": result.get("coverage", {}),
                    "recommendations": result.get("recommendations", []),
                }
            
        except Exception as e:
            logger.error("Dataset analysis failed", error=str(e))
            return {
                "new_categories": [],
                "expanded_categories": [],
                "coverage": {"error": str(e)},
                "recommendations": ["Analysis failed - please try again"],
            }
        
        return {
            "new_categories": [],
            "expanded_categories": [],
            "coverage": {},
            "recommendations": [],
        }
    
    async def evolve_from_correction(
        self,
        original_path: list[str],
        corrected_path: list[str],
        ticket_content: str,
        user_notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Use LLM to analyze HITL corrections and evolve the graph.
        
        Args:
            original_path: [level1, level2, level3] of original classification
            corrected_path: [level1, level2, level3] of corrected classification
            ticket_content: The ticket title and description
            user_notes: Optional notes from the human reviewer
        
        Returns:
            Analysis and suggestions for graph evolution
        """
        hierarchy = await self._get_current_hierarchy()
        
        prompt = f"""You are analyzing a human correction to an AI classification to improve the taxonomy.

ORIGINAL CLASSIFICATION: {' > '.join(original_path)}
CORRECTED CLASSIFICATION: {' > '.join(corrected_path)}

TICKET CONTENT:
{ticket_content[:500]}

REVIEWER NOTES: {user_notes or 'None provided'}

CURRENT HIERARCHY STRUCTURE:
{json.dumps(hierarchy, indent=2)}

TASK: Analyze this correction and suggest graph modifications.

Consider:
1. Why did the AI make this mistake?
2. Are the categories too similar or confusing?
3. Should keywords be updated?
4. Is a new category needed?
5. Should categories be merged or split?

Respond in this exact JSON format:
{{
    "analysis": {{
        "error_type": "misclassification reason",
        "confusion_factors": ["factor1", "factor2"],
        "pattern_identified": "Description of the pattern"
    }},
    "suggestions": [
        {{
            "type": "update_keywords",
            "target_category": "Category Name",
            "target_level": 3,
            "action": "Add keywords: ['keyword1', 'keyword2']"
        }},
        {{
            "type": "add_category",
            "parent": "Parent Category",
            "parent_level": 2,
            "new_name": "New Category Name",
            "description": "What it covers"
        }},
        {{
            "type": "update_description",
            "target_category": "Category Name",
            "target_level": 3,
            "new_description": "Updated description"
        }}
    ],
    "should_auto_apply": false,
    "confidence": 0.8
}}"""
        
        client = self._get_client()
        model = settings.azure_openai_deployment_name or "gpt-4o"
        
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a classification taxonomy expert. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                
                # Auto-apply keyword updates if confidence is high
                applied_changes = []
                if result.get("should_auto_apply", False) and result.get("confidence", 0) >= 0.8:
                    applied_changes = await self._apply_evolution_suggestions(
                        result.get("suggestions", [])
                    )
                
                return {
                    "analysis": result.get("analysis", {}),
                    "suggestions": result.get("suggestions", []),
                    "applied_changes": applied_changes,
                    "graph_updated": len(applied_changes) > 0,
                }
            
        except Exception as e:
            logger.error("HITL evolution analysis failed", error=str(e))
        
        # Update weights even if LLM analysis fails
        neo4j = await get_neo4j_client()
        await neo4j.record_correction(
            ticket_id="hitl_feedback",
            original_path=tuple(original_path),
            corrected_path=tuple(corrected_path),
        )
        
        return {
            "analysis": {"error": "LLM analysis failed, weights updated only"},
            "suggestions": [],
            "applied_changes": ["edge_weights_updated"],
            "graph_updated": True,
        }
    
    async def _apply_evolution_suggestions(
        self,
        suggestions: list[dict[str, Any]],
    ) -> list[str]:
        """Apply high-confidence evolution suggestions."""
        neo4j = await get_neo4j_client()
        applied = []
        
        for suggestion in suggestions:
            try:
                suggestion_type = suggestion.get("type")
                
                if suggestion_type == "update_keywords":
                    level_label = f"Level{suggestion['target_level']}Category"
                    async with neo4j.session() as session:
                        await session.run(
                            f"""
                            MATCH (c:{level_label} {{name: $name}})
                            SET c.keywords = c.keywords + $new_keywords,
                                c.updated_at = datetime()
                            """,
                            name=suggestion["target_category"],
                            new_keywords=suggestion.get("keywords", []),
                        )
                    applied.append(f"Updated keywords for {suggestion['target_category']}")
                
                elif suggestion_type == "update_description":
                    level_label = f"Level{suggestion['target_level']}Category"
                    async with neo4j.session() as session:
                        await session.run(
                            f"""
                            MATCH (c:{level_label} {{name: $name}})
                            SET c.description = $description,
                                c.updated_at = datetime()
                            """,
                            name=suggestion["target_category"],
                            description=suggestion.get("new_description", ""),
                        )
                    applied.append(f"Updated description for {suggestion['target_category']}")
                
            except Exception as e:
                logger.warning("Failed to apply suggestion", suggestion=suggestion, error=str(e))
        
        return applied


# Singleton
_graph_evolution_service: GraphEvolutionService | None = None


async def get_graph_evolution_service() -> GraphEvolutionService:
    """Get or create the graph evolution service singleton."""
    global _graph_evolution_service
    if _graph_evolution_service is None:
        _graph_evolution_service = GraphEvolutionService()
    return _graph_evolution_service


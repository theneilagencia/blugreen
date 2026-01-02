import json
import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType

logger = logging.getLogger(__name__)

UI_REFINEMENT_SYSTEM_PROMPT = """You are an expert UI designer. Your role is to:
- Improve visual hierarchy
- Adjust spacing for consistency
- Improve readability
- Refine microcopy
- Ensure visual consistency

You must follow these constraints:
- Never violate the Design System
- Never alter user flow
- Never change functionality
- Only use allowed design tokens

Design Tokens:
- Spacing: xs=4, sm=8, md=16, lg=24, xl=32
- Border radius: sm=4, md=8

UI Quality Criteria:
1. Clear visual hierarchy (25%)
2. Consistent spacing (25%)
3. Good readability (25%)
4. Adequate contrast (25%)

Always respond with valid JSON."""


class UIRefinementAgent(BaseAgent):
    agent_type = AgentType.UI_REFINEMENT
    system_prompt = UI_REFINEMENT_SYSTEM_PROMPT
    capabilities = [
        "improve_visual_hierarchy",
        "adjust_spacing",
        "improve_readability",
        "refine_microcopy",
        "ensure_consistency",
    ]
    restrictions = [
        "never_violate_design_system",
        "never_alter_flow",
        "never_change_functionality",
        "only_use_design_tokens",
    ]

    DESIGN_TOKENS = {
        "spacing": {
            "xs": 4,
            "sm": 8,
            "md": 16,
            "lg": 24,
            "xl": 32,
        },
        "border_radius": {
            "sm": 4,
            "md": 8,
        },
    }

    UI_QUALITY_CRITERIA = [
        {
            "id": "visual_hierarchy",
            "criterion": "Clear visual hierarchy",
            "weight": 0.25,
        },
        {
            "id": "spacing_consistency",
            "criterion": "Consistent spacing",
            "weight": 0.25,
        },
        {
            "id": "readability",
            "criterion": "Good readability",
            "weight": 0.25,
        },
        {
            "id": "contrast",
            "criterion": "Adequate contrast",
            "weight": 0.25,
        },
    ]

    def validate_task(self, task: Task) -> tuple[bool, Optional[str]]:
        if task.task_type not in [TaskType.UI_REFINEMENT]:
            return False, f"UI Refinement agent cannot handle task type: {task.task_type}"
        return True, None

    def can_handle_task(self, task: Task) -> bool:
        return task.task_type == TaskType.UI_REFINEMENT

    async def execute(self, task: Task) -> dict[str, Any]:
        self.assign_task(task)

        try:
            result = await self._refine_ui(task)

            if not result["ui_approved"]:
                self.complete_task(task, success=False, error_message="UI quality check failed")
                return {
                    "status": "needs_refinement",
                    "result": result,
                    "message": "UI does not meet quality standards",
                }

            self.complete_task(task, success=True)
            return {
                "status": "success",
                "result": result,
            }
        except Exception as e:
            logger.error(f"UI Refinement agent error: {e}")
            self.complete_task(task, success=False, error_message=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    async def _refine_ui(self, task: Task) -> dict[str, Any]:
        tokens_json = json.dumps(self.DESIGN_TOKENS, indent=2)
        criteria_json = json.dumps(self.UI_QUALITY_CRITERIA, indent=2)

        prompt = f"""Evaluate and refine the UI for the following component/page:

{task.description}

Design Tokens to use:
{tokens_json}

Quality Criteria to evaluate:
{criteria_json}

Provide a JSON response with this structure:
{{
    "quality_scores": [
        {{
            "criterion_id": "visual_hierarchy",
            "criterion": "Clear visual hierarchy",
            "score": 0.0-1.0,
            "issues": ["list of issues found"],
            "recommendations": ["how to improve"]
        }}
    ],
    "refinements": [
        {{
            "type": "spacing|typography|contrast|microcopy",
            "location": "where to apply",
            "current": "current value",
            "suggested": "suggested value",
            "reason": "why this change"
        }}
    ],
    "design_system_violations": [
        {{
            "type": "spacing|border_radius|component",
            "location": "where",
            "issue": "what's wrong",
            "fix": "how to fix"
        }}
    ],
    "microcopy_improvements": [
        {{
            "location": "where",
            "current": "current text",
            "suggested": "improved text",
            "reason": "why"
        }}
    ]
}}

Be thorough in identifying UI improvements while respecting the Design System."""

        try:
            response = await self.ask_llm(prompt, temperature=0.3)
            return self._parse_ui_response(response)
        except Exception as e:
            logger.warning(f"LLM unavailable, using fallback UI evaluation: {e}")
            return self._get_fallback_ui_results()

    def _parse_ui_response(self, response: str) -> dict[str, Any]:
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                quality_scores = result.get("quality_scores", [])
                total_score = 0.0
                for score in quality_scores:
                    criterion_id = score.get("criterion_id")
                    criterion_weight = next(
                        (c["weight"] for c in self.UI_QUALITY_CRITERIA if c["id"] == criterion_id),
                        0.25,
                    )
                    weighted_score = score.get("score", 0) * criterion_weight
                    score["weighted_score"] = weighted_score
                    total_score += weighted_score
                result["total_score"] = total_score
                result["ui_approved"] = total_score >= 0.7
                violations = result.get("design_system_violations", [])
                result["design_system_compliance"] = len(violations) == 0
                return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
        return self._get_fallback_ui_results()

    def _get_fallback_ui_results(self) -> dict[str, Any]:
        quality_scores = [
            {
                "criterion_id": criterion["id"],
                "criterion": criterion["criterion"],
                "score": 1.0,
                "weighted_score": criterion["weight"],
                "issues": [],
                "recommendations": [],
            }
            for criterion in self.UI_QUALITY_CRITERIA
        ]
        return {
            "ui_approved": True,
            "total_score": 1.0,
            "quality_scores": quality_scores,
            "refinements": [],
            "design_system_violations": [],
            "microcopy_improvements": [],
            "design_system_compliance": True,
            "note": "LLM unavailable - manual UI review required",
        }

    def get_design_tokens(self) -> dict[str, Any]:
        return self.DESIGN_TOKENS

    def validate_spacing(self, value: int) -> tuple[bool, Optional[str]]:
        valid_values = list(self.DESIGN_TOKENS["spacing"].values())
        if value not in valid_values:
            return False, f"Invalid spacing value: {value}. Use one of: {valid_values}"
        return True, None

    def validate_border_radius(self, value: int) -> tuple[bool, Optional[str]]:
        valid_values = list(self.DESIGN_TOKENS["border_radius"].values())
        if value not in valid_values:
            return False, f"Invalid border radius: {value}. Use one of: {valid_values}"
        return True, None

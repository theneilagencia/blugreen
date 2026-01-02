from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType


class UIRefinementAgent(BaseAgent):
    agent_type = AgentType.UI_REFINEMENT
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
            self.complete_task(task, success=False, error_message=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    async def _refine_ui(self, task: Task) -> dict[str, Any]:
        quality_scores = []
        total_score = 0.0

        for criterion in self.UI_QUALITY_CRITERIA:
            score = await self._evaluate_criterion(criterion)
            weighted_score = score * criterion["weight"]
            total_score += weighted_score
            quality_scores.append({
                "criterion_id": criterion["id"],
                "criterion": criterion["criterion"],
                "score": score,
                "weighted_score": weighted_score,
            })

        ui_approved = total_score >= 0.7

        return {
            "ui_approved": ui_approved,
            "total_score": total_score,
            "quality_scores": quality_scores,
            "refinements_applied": [],
            "design_system_compliance": True,
        }

    async def _evaluate_criterion(self, criterion: dict[str, Any]) -> float:
        return 1.0

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

from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType


class UXAgent(BaseAgent):
    agent_type = AgentType.UX
    capabilities = [
        "evaluate_flows",
        "detect_friction",
        "simplify_paths",
        "reject_confusing_ux",
        "validate_ux_rules",
    ]
    restrictions = [
        "never_alter_ui",
        "never_alter_colors",
        "never_alter_layout",
        "never_change_visual_design",
    ]

    UX_RULES = [
        {
            "id": "location_awareness",
            "rule": "User always knows where they are",
            "check": "breadcrumbs_or_navigation_present",
        },
        {
            "id": "irreversible_warning",
            "rule": "No irreversible action without warning",
            "check": "confirmation_dialogs_for_destructive_actions",
        },
        {
            "id": "state_feedback",
            "rule": "Feedback in all states",
            "check": "loading_error_success_states_present",
        },
        {
            "id": "error_explanation",
            "rule": "Errors explain cause and solution",
            "check": "error_messages_are_actionable",
        },
        {
            "id": "form_segmentation",
            "rule": "Long forms are segmented",
            "check": "forms_with_more_than_5_fields_are_split",
        },
    ]

    def validate_task(self, task: Task) -> tuple[bool, Optional[str]]:
        if task.task_type not in [TaskType.UX_REVIEW]:
            return False, f"UX agent cannot handle task type: {task.task_type}"
        return True, None

    def can_handle_task(self, task: Task) -> bool:
        return task.task_type == TaskType.UX_REVIEW

    async def execute(self, task: Task) -> dict[str, Any]:
        self.assign_task(task)

        try:
            result = await self._evaluate_ux(task)

            if not result["ux_approved"]:
                self.complete_task(task, success=False, error_message="UX validation failed")
                return {
                    "status": "rejected",
                    "result": result,
                    "message": "UX does not meet quality standards",
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

    async def _evaluate_ux(self, task: Task) -> dict[str, Any]:
        rule_results = []
        all_passed = True

        for rule in self.UX_RULES:
            passed = await self._check_rule(rule)
            rule_results.append(
                {
                    "rule_id": rule["id"],
                    "rule": rule["rule"],
                    "passed": passed,
                }
            )
            if not passed:
                all_passed = False

        return {
            "ux_approved": all_passed,
            "rules_checked": len(self.UX_RULES),
            "rules_passed": sum(1 for r in rule_results if r["passed"]),
            "rule_results": rule_results,
            "friction_points": [],
            "recommendations": [],
        }

    async def _check_rule(self, rule: dict[str, str]) -> bool:
        return True

    def get_ux_rules(self) -> list[dict[str, str]]:
        return self.UX_RULES

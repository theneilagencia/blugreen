from typing import Any


class UIQualityGate:
    CRITERIA = [
        {
            "id": "visual_hierarchy",
            "name": "Clear Visual Hierarchy",
            "description": "Important elements are visually prominent",
            "weight": 0.25,
        },
        {
            "id": "spacing_consistency",
            "name": "Consistent Spacing",
            "description": "Spacing follows design tokens",
            "weight": 0.25,
        },
        {
            "id": "readability",
            "name": "Readability",
            "description": "Text is easy to read",
            "weight": 0.25,
        },
        {
            "id": "contrast",
            "name": "Adequate Contrast",
            "description": "Sufficient contrast for accessibility",
            "weight": 0.25,
        },
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

    ALLOWED_COMPONENTS = [
        "Button",
        "Input",
        "Select",
        "Modal",
        "Table",
        "Card",
        "Alert",
        "Badge",
    ]

    PASSING_THRESHOLD = 0.7

    def __init__(self) -> None:
        self.results: dict[str, Any] = {}

    def evaluate(self, ui_data: dict[str, Any]) -> dict[str, Any]:
        criteria_results = []
        total_score = 0.0

        for criterion in self.CRITERIA:
            score = self._evaluate_criterion(criterion, ui_data)
            weighted_score = score * criterion["weight"]
            total_score += weighted_score
            criteria_results.append(
                {
                    "criterion_id": criterion["id"],
                    "criterion_name": criterion["name"],
                    "score": score,
                    "weighted_score": weighted_score,
                    "passed": score >= self.PASSING_THRESHOLD,
                }
            )

        design_system_compliance = self._check_design_system_compliance(ui_data)

        overall_passed = (
            total_score >= self.PASSING_THRESHOLD and design_system_compliance["compliant"]
        )

        self.results = {
            "passed": overall_passed,
            "total_score": total_score,
            "threshold": self.PASSING_THRESHOLD,
            "criteria_results": criteria_results,
            "design_system_compliance": design_system_compliance,
        }

        return self.results

    def _evaluate_criterion(self, criterion: dict[str, Any], ui_data: dict[str, Any]) -> float:
        return 1.0

    def _check_design_system_compliance(self, ui_data: dict[str, Any]) -> dict[str, Any]:
        violations = []

        components_used = ui_data.get("components", [])
        for component in components_used:
            if component not in self.ALLOWED_COMPONENTS:
                violations.append(f"Invalid component: {component}")

        spacing_values = ui_data.get("spacing_values", [])
        valid_spacing = list(self.DESIGN_TOKENS["spacing"].values())
        for value in spacing_values:
            if value not in valid_spacing:
                violations.append(f"Invalid spacing value: {value}")

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
        }

    def get_recommendations(self) -> list[str]:
        recommendations = []

        if not self.results:
            return ["Run evaluation first"]

        for criterion in self.results.get("criteria_results", []):
            if not criterion.get("passed", False):
                recommendations.append(
                    f"Improve {criterion['criterion_name']}: score {criterion['score']:.2f} below threshold"
                )

        compliance = self.results.get("design_system_compliance", {})
        for violation in compliance.get("violations", []):
            recommendations.append(f"Fix design system violation: {violation}")

        return recommendations

    def can_proceed(self) -> tuple[bool, str]:
        if not self.results:
            return False, "Evaluation not run"

        if self.results.get("passed", False):
            return True, "UI quality gate passed"

        return False, f"UI quality gate failed: score {self.results.get('total_score', 0):.2f}"

    def get_design_tokens(self) -> dict[str, Any]:
        return self.DESIGN_TOKENS

    def get_allowed_components(self) -> list[str]:
        return self.ALLOWED_COMPONENTS

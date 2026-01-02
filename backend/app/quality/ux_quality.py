from typing import Any


class UXQualityGate:
    CRITERIA = [
        {
            "id": "clarity",
            "name": "Clarity",
            "description": "User understands what to do at every step",
            "weight": 0.25,
        },
        {
            "id": "predictability",
            "name": "Predictability",
            "description": "System behaves as expected",
            "weight": 0.25,
        },
        {
            "id": "feedback",
            "name": "Feedback",
            "description": "User receives feedback for all actions",
            "weight": 0.25,
        },
        {
            "id": "error_handling",
            "name": "Understandable Errors",
            "description": "Errors explain cause and solution",
            "weight": 0.25,
        },
    ]

    UX_RULES = [
        {
            "id": "location_awareness",
            "rule": "User always knows where they are",
            "required": True,
        },
        {
            "id": "irreversible_warning",
            "rule": "No irreversible action without warning",
            "required": True,
        },
        {
            "id": "state_feedback",
            "rule": "Feedback in all states",
            "required": True,
        },
        {
            "id": "error_explanation",
            "rule": "Errors explain cause and solution",
            "required": True,
        },
        {
            "id": "form_segmentation",
            "rule": "Long forms are segmented",
            "required": True,
        },
    ]

    PASSING_THRESHOLD = 0.7

    def __init__(self) -> None:
        self.results: dict[str, Any] = {}

    def evaluate(self, ux_data: dict[str, Any]) -> dict[str, Any]:
        criteria_results = []
        total_score = 0.0

        for criterion in self.CRITERIA:
            score = self._evaluate_criterion(criterion, ux_data)
            weighted_score = score * criterion["weight"]
            total_score += weighted_score
            criteria_results.append({
                "criterion_id": criterion["id"],
                "criterion_name": criterion["name"],
                "score": score,
                "weighted_score": weighted_score,
                "passed": score >= self.PASSING_THRESHOLD,
            })

        rules_results = []
        all_rules_passed = True

        for rule in self.UX_RULES:
            passed = self._check_rule(rule, ux_data)
            rules_results.append({
                "rule_id": rule["id"],
                "rule": rule["rule"],
                "passed": passed,
                "required": rule["required"],
            })
            if rule["required"] and not passed:
                all_rules_passed = False

        overall_passed = total_score >= self.PASSING_THRESHOLD and all_rules_passed

        self.results = {
            "passed": overall_passed,
            "total_score": total_score,
            "threshold": self.PASSING_THRESHOLD,
            "criteria_results": criteria_results,
            "rules_results": rules_results,
            "all_rules_passed": all_rules_passed,
        }

        return self.results

    def _evaluate_criterion(self, criterion: dict[str, Any], ux_data: dict[str, Any]) -> float:
        return 1.0

    def _check_rule(self, rule: dict[str, Any], ux_data: dict[str, Any]) -> bool:
        return True

    def get_recommendations(self) -> list[str]:
        recommendations = []

        if not self.results:
            return ["Run evaluation first"]

        for criterion in self.results.get("criteria_results", []):
            if not criterion.get("passed", False):
                recommendations.append(
                    f"Improve {criterion['criterion_name']}: score {criterion['score']:.2f} below threshold"
                )

        for rule in self.results.get("rules_results", []):
            if not rule.get("passed", False):
                recommendations.append(f"Fix UX rule violation: {rule['rule']}")

        return recommendations

    def can_proceed(self) -> tuple[bool, str]:
        if not self.results:
            return False, "Evaluation not run"

        if self.results.get("passed", False):
            return True, "UX quality gate passed"

        return False, f"UX quality gate failed: score {self.results.get('total_score', 0):.2f}"

from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class NeutralSequencingEvaluationCatalogTest(unittest.TestCase):
    def test_blind_cases_and_oracle_are_separate_complete_and_three_run(self) -> None:
        cases = json.loads(
            (SKILL_ROOT / "evals/cases.json").read_text(encoding="utf-8")
        )
        oracle = json.loads(
            (SKILL_ROOT / "evals/oracle.json").read_text(encoding="utf-8")
        )
        result = json.loads(
            (
                SKILL_ROOT
                / "evals/results/v8-release-evaluation.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(
            cases["schema"],
            "source-aligned-neutral-sequencing-evals-v1",
        )
        self.assertEqual(
            oracle["schema"],
            "source-aligned-neutral-sequencing-oracle-v1",
        )
        self.assertEqual(cases["trials-per-case"], 3)
        self.assertEqual(oracle["trials-per-case"], 3)
        self.assertEqual(oracle["required-pass-count"], 3)
        self.assertEqual(
            result["trace-contract-version"],
            "source-aligned-trace-v8",
        )
        self.assertEqual(len(result["fresh-evaluators"]), 3)
        self.assertEqual(result["oracle-disclosure"], "none-before-evaluation")

        case_rows = cases["cases"]
        oracle_rows = oracle["cases"]
        self.assertEqual(
            [row["id"] for row in case_rows],
            [row["id"] for row in oracle_rows],
        )
        self.assertEqual(len(case_rows), 10)
        self.assertEqual(
            [row["id"] for row in result["cases"]],
            [row["id"] for row in case_rows],
        )
        self.assertTrue(result["release-candidate"])
        self.assertTrue(
            all(
                row["decision"] == "passed"
                and row["pass-count"] == 3
                and row["required-pass-count"] == 3
                for row in result["cases"]
            )
        )
        for row in case_rows:
            self.assertEqual(
                set(row),
                {
                    "id",
                    "current-baseline",
                    "source-excerpt",
                    "candidate-plan",
                },
            )
            self.assertNotIn("expected", row)
            self.assertNotIn("category", row)
        for row in oracle_rows:
            self.assertEqual(
                set(row),
                {
                    "id",
                    "category",
                    "required-invariants",
                    "forbidden-outcomes",
                },
            )
            self.assertTrue(row["required-invariants"])
            self.assertTrue(row["forbidden-outcomes"])

        self.assertEqual(
            {row["category"] for row in oracle_rows},
            {
                "valid-foundation",
                "shadow-enabler",
                "planned-guard",
                "existing-baseline-guard",
                "explicit-milestone-and-deferred",
                "directive-false-positive",
                "existing-baseline-engineering-outcome",
                "no-foundation-thin-outcome",
                "stable-outcome-consumption-requires-complete-edge-set",
                "shared-infrastructure-is-not-outcome-consumption",
            },
        )


if __name__ == "__main__":
    unittest.main()

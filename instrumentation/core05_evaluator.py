"""Real-Qwen evaluation for the frozen CORE-05 once-only test."""

from instrumentation.core04_evaluator import Core04Evaluator


class Core05Evaluator(Core04Evaluator):
    """Evaluate the unchanged repair on exactly eight locked test cases."""

    expected_split = "test"
    evaluation_schema = "aether.core05-evaluation.v1"
    result_schema = "aether.core05-arm-result.v1"
    stage_name = "CORE-05"


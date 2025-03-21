from braintrust_core.score import Scorer, Score
from autoevals.ragas import AnswerCorrectness
import subprocess
import jinja2
import structlog

logger = structlog.get_logger(__name__)


class OpsmateScorer(Scorer):
    def _run_eval_sync(self, output, expected=None, **kwargs) -> Score:
        metadata = kwargs.get("metadata", {})
        cmds = {}
        for key, cmd in metadata.get("cmds", {}).items():
            cmds[key] = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

        expected = jinja2.Template(expected).render(**cmds)

        logger.info("rendered expected", expected=expected)
        answer_correctness = AnswerCorrectness()
        score = answer_correctness.eval(
            input=kwargs.get("input"),
            output=output,
            expected=expected,
        )
        score.metadata["cmds"] = cmds
        score.metadata["rendered_expected"] = expected

        return score

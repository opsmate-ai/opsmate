from braintrust_core.score import Scorer, Score
from autoevals.ragas import AnswerCorrectness
from autoevals import ClosedQA
import subprocess
import jinja2
import structlog

logger = structlog.get_logger(__name__)


class OpsmateScorer(Scorer):
    def _run_eval_sync(self, output, expected=None, **kwargs) -> Score:
        metadata = kwargs.get("metadata", {})
        scorer = metadata.get("scorer")
        match scorer:
            case "CorrectnessScorer":
                scorer_cls = CorrectnessScorer
            case "TextEditScorer":
                scorer_cls = TextEditScorer
            case "MitigationScorer":
                scorer_cls = MitigationScorer
            case _:
                raise ValueError(f"Unknown scorer: {scorer}")

        score = scorer_cls().eval(
            output=output,
            expected=expected,
            **kwargs,
        )
        return score


class CorrectnessScorer(Scorer):
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


class TextEditScorer(Scorer):
    def _run_eval_sync(self, output, expected=None, **kwargs) -> Score:
        metadata = kwargs.get("metadata", {})
        file_path = metadata.get("file_path")
        if file_path:
            with open(file_path, "r") as f:
                real_output = f.read()
        else:
            real_output = output

        rendered_expected = jinja2.Template(expected).render(**metadata)
        closed_qa = ClosedQA()
        score = closed_qa.eval(
            input=kwargs.get("input"),
            output=real_output,
            criteria=rendered_expected,
        )

        score.metadata["real_output"] = real_output
        return score


class MitigationScorer(Scorer):
    def _run_eval_sync(self, output, expected=None, **kwargs) -> Score:
        try:
            metadata = kwargs.get("metadata", {})
            criteria = metadata.get("criteria")
            cmds = metadata.get("cmds", {})

            kv = {}
            for key, cmd in cmds.items():
                kv[key] = (
                    subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
                )
            kv["output"] = output

            fact = jinja2.Template(metadata.get("fact")).render(**kv)
            closed_qa = ClosedQA()
            score = closed_qa.eval(
                input=kwargs.get("input"),
                output=fact,
                criteria=criteria,
            )
            score.metadata["fact"] = fact
            return score
        finally:
            for cleanup in metadata.get("cleanups", []):
                subprocess.run(cleanup, shell=True)

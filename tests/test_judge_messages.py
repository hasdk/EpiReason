from inspect_ai.model import ContentText

from harness.judge import JUDGE_SYSTEM, judge_messages, judge_prompt

ARGS = dict(question="Q?", response="An answer.", answer_key="Key.", criterion="Names the bias")


def test_blocks_join_to_the_single_prompt():
    system, user = judge_messages(**ARGS)
    assert system.content == JUDGE_SYSTEM
    blocks = user.content
    assert len(blocks) == 2 and all(isinstance(b, ContentText) for b in blocks)
    assert blocks[0].text + blocks[1].text == judge_prompt(**ARGS)


def test_shared_block_does_not_depend_on_the_criterion():
    a = judge_messages(**ARGS)[1].content[0].text
    b = judge_messages(**{**ARGS, "criterion": "Proposes a fix"})[1].content[0].text
    assert a == b and "[Criterion]" not in a

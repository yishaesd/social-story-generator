"""guard 的单元测试：python -m unittest agent.test_guard 或在该目录下 python test_guard.py"""

import unittest

from guard import check, sanitize, visible_len, sentence_count, has_crisis


def say(text, next_action=None):
    return {"tool": "say", "text": text, "next_action": next_action}


NEXT = {"type": "options", "items": ["去走廊", "戴耳机", "找人"]}


class TestVisibleLen(unittest.TestCase):
    def test_punct_and_space_not_counted(self):
        self.assertEqual(visible_len("去走廊，站一会儿。"), 7)

    def test_sentence_count(self):
        self.assertEqual(sentence_count("好。走。"), 2)


class TestCrisis(unittest.TestCase):
    def test_crisis_detected(self):
        self.assertTrue(has_crisis("我不想活了"))
        self.assertTrue(has_crisis("放学有人要堵我"))

    def test_crisis_must_escalate(self):
        r = check(say("别怕，会好起来的", NEXT), child_text="我不想活了")
        self.assertFalse(r.ok)
        self.assertEqual(r.replacement["tool"], "escalate")

    def test_escalate_passes(self):
        r = check({"tool": "escalate", "reason": "被威胁", "text": "我现在帮你联系姑姑。"},
                  child_text="有人要打我")
        self.assertTrue(r.ok)

    def test_escalate_no_advice(self):
        r = check({"tool": "escalate", "reason": "被威胁", "text": "你别怕，勇敢一点，我陪你。"},
                  child_text="有人要打我")
        self.assertFalse(r.ok)


class TestLength(unittest.TestCase):
    def test_long_and_multi_sentence_fails(self):
        text = "你现在应该先深呼吸，然后在心里数到十，接着慢慢走到走廊尽头那个安静的地方，坐下等一会儿，等感觉好一点再回去上课。"
        r = check(say(text, NEXT))
        self.assertFalse(r.ok)
        self.assertIn("LEN", [i.code for i in r.errors])

    def test_short_ok(self):
        r = check(say("走到走廊尽头，坐着等两分钟。", NEXT))
        self.assertTrue(r.ok)


class TestBanned(unittest.TestCase):
    def test_diagnosis_word(self):
        r = check(say("你可能有点焦虑症状。", NEXT))
        self.assertFalse(r.ok)
        self.assertIn("BANNED", [i.code for i in r.errors])

    def test_progress_praise(self):
        r = check(say("你今天进步很大。", NEXT))
        self.assertFalse(r.ok)

    def test_normalize_sentence(self):
        r = check(say("慢慢就会变正常了。", NEXT))
        self.assertFalse(r.ok)

    def test_imperative(self):
        r = check(say("你应该去跟他谈谈。", NEXT))
        self.assertFalse(r.ok)
        self.assertIn("IMPERATIVE", [i.code for i in r.errors])

    def test_you_yao_allowed_when_not_imperative(self):
        # "要不要" 不是命令，不应误伤
        r = check(say("要不要先去走廊？", NEXT))
        self.assertTrue(r.ok)


class TestAskOnce(unittest.TestCase):
    def test_multi_question_fails(self):
        r = check(say("怎么了？为什么不去？", NEXT))
        self.assertFalse(r.ok)
        self.assertIn("MULTI_Q", [i.code for i in r.errors])

    def test_single_question_ok(self):
        r = check(say("现在最想躲开什么？", NEXT))
        self.assertTrue(r.ok)


class TestNextAction(unittest.TestCase):
    def test_no_next_fails(self):
        r = check(say("我在的。"))
        self.assertFalse(r.ok)
        self.assertIn("NO_NEXT", [i.code for i in r.errors])

    def test_option_too_long_fails(self):
        r = check(say("选一个。", {"type": "options", "items": ["去走廊尽头的那个安静角落待着"]}))
        self.assertFalse(r.ok)

    def test_contact_ok(self):
        r = check(say("要不要现在联系姑姑？", {"type": "contact", "label": "联系姑姑"}))
        self.assertTrue(r.ok)


class TestClarify(unittest.TestCase):
    def test_too_many_options(self):
        r = check({"tool": "clarify", "question": "哪一样？", "options": ["a", "b", "c", "d"]})
        self.assertFalse(r.ok)

    def test_clarify_ok(self):
        r = check({"tool": "clarify", "question": "最烦哪一样？", "options": ["声音", "人多", "灯光"]})
        self.assertTrue(r.ok)


class TestSoften(unittest.TestCase):
    def test_soothe_warns(self):
        r = check(say("没事的，别怕。", NEXT))
        self.assertTrue(r.ok)  # 有 next_action，不阻断
        self.assertIn("SOOTHE", [i.code for i in r.warns])


class TestSanitize(unittest.TestCase):
    def test_bad_becomes_fallback(self):
        out = sanitize(say("你会好起来的。"))
        self.assertEqual(out["tool"], "show_cards")
        self.assertTrue(out["card_ids"])

    def test_good_passes_through(self):
        a = say("走到走廊尽头，坐着等两分钟。", NEXT)
        self.assertEqual(sanitize(a), a)


if __name__ == "__main__":
    unittest.main(verbosity=2)

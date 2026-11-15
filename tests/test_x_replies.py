import unittest
from unittest.mock import patch
import tempfile
import json
from pathlib import Path
from scripts import x_replies
from scripts.x_replies import parse_replies, relevant

class ReplyTests(unittest.TestCase):
    def test_empty_account_is_explicitly_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(x_replies, "OUT", Path(folder) / "signals.json"), \
                 patch.object(x_replies, "STATE", Path(folder) / "state.json"), \
                 patch.dict("os.environ", {"X_BEARER_TOKEN": "test"}), \
                 patch.object(x_replies, "request", side_effect=[
                     {"data": {"id": "100"}}, {"data": []},
                     {"data": {"id": "200"}}, {"data": [{"id": "222", "text": "hello"}]}
                 ]):
                x_replies.main()
                output = json.loads((Path(folder) / "signals.json").read_text())
                self.assertEqual(output["accountStatus"]["blknoiz06"]["status"], "empty_feed")
                self.assertEqual(output["accountStatus"]["MINHxDYNASTY"]["postsReturned"], 1)
                self.assertNotIn("blknoiz06", json.loads((Path(folder) / "state.json").read_text()))

    def test_keyword_filter(self):
        self.assertTrue(relevant('post good things and I will buy!'))
        self.assertTrue(relevant('new token $ROCKSTAR'))
        self.assertFalse(relevant('feel you bro'))

    def test_only_replies(self):
        posts = [
            {"id": "123", "text": "post good things and I will buy!", "referenced_tweets": [{"type": "replied_to", "id": "122"}]},
            {"id": "124", "text": "regular post"},
            {"id": "125", "text": "quote", "referenced_tweets": [{"type": "quoted", "id": "120"}]}
        ]
        signals = parse_replies("blknoiz06", posts)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["replyToId"], "122")
        self.assertFalse(signals[0]["verifiedToken"])
        self.assertEqual(signals[0]["marketReaction"], "not_assessed")

if __name__ == "__main__":
    unittest.main()

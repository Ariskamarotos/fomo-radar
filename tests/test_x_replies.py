import unittest
from scripts.x_replies import parse_replies, relevant

class ReplyTests(unittest.TestCase):
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

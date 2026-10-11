"""Offline regressions. No AWS sessions, model downloads or provider calls."""
import random
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.duplicate_reviewer import DuplicateReviewer
from src.embedding_generator import EmbeddingGenerator


class FakeTable:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.scans = []
        self.updates = []

    def scan(self, **kwargs):
        self.scans.append(kwargs)
        return next(self.pages)

    def update_item(self, **kwargs):
        self.updates.append(kwargs)


class DuplicatePaginationTests(unittest.TestCase):
    def reviewer(self, pages):
        reviewer = DuplicateReviewer.__new__(DuplicateReviewer)
        reviewer.final_table = FakeTable(pages)
        return reviewer

    def test_pending_review_continues_after_empty_filtered_page(self):
        reviewer = self.reviewer([
            {'Items': [], 'LastEvaluatedKey': {'product_id': 'cursor'}},
            {'Items': [{'product_id': 'later-product'}]},
        ])
        self.assertEqual(reviewer.get_pending_duplicates(), [{'product_id': 'later-product'}])
        first, second = reviewer.final_table.scans
        self.assertNotIn('ExclusiveStartKey', first)
        self.assertEqual(second['ExclusiveStartKey'], {'product_id': 'cursor'})
        self.assertEqual(first['FilterExpression'], second['FilterExpression'])
        self.assertEqual(first['ExpressionAttributeValues'], second['ExpressionAttributeValues'])

    def test_duplicate_reference_cleanup_reaches_later_pages(self):
        reviewer = self.reviewer([
            {'Items': [{'product_id': 'first', 'potential_duplicates': ['removed', 'keep']}],
             'LastEvaluatedKey': {'product_id': 'first'}},
            {'Items': [], 'LastEvaluatedKey': {'product_id': 'empty-page'}},
            {'Items': [{'product_id': 'last', 'potential_duplicates': ['removed']}]},
        ])
        reviewer._remove_from_all_duplicate_lists('removed')
        updates = reviewer.final_table.updates
        self.assertEqual([item['Key']['product_id'] for item in updates], ['first', 'last'])
        self.assertEqual(updates[0]['ExpressionAttributeValues'], {':duplicates': ['keep'], ':checked': False})
        self.assertEqual(updates[1]['ExpressionAttributeValues'], {':duplicates': [], ':checked': True})
        self.assertEqual(len(reviewer.final_table.scans), 3)


class EmbeddingSafetyTests(unittest.TestCase):
    def generator(self, method):
        with patch('src.embedding_generator.settings.EMBEDDING_METHOD', method):
            return EmbeddingGenerator()

    def test_missing_clip_does_not_switch_to_dummy(self):
        with patch.dict(sys.modules, {'torch': None, 'clip': None}):
            generator = self.generator('local')
        self.assertEqual(generator.method, 'local')
        with patch.object(generator.image_processor, 'download_image') as download:
            self.assertIsNone(generator.generate_embedding('https://example.invalid/product.jpg'))
        download.assert_not_called()

    def test_local_inference_failure_returns_no_embedding(self):
        generator = EmbeddingGenerator.__new__(EmbeddingGenerator)
        generator.method = 'local'
        generator.model = object()
        generator.image_processor = Mock()
        generator.image_processor.download_image.side_effect = RuntimeError('image unavailable')
        with patch.dict(sys.modules, {'torch': SimpleNamespace()}):
            self.assertIsNone(generator.generate_embedding('https://example.invalid/product.jpg'))
        generator.image_processor.download_image.assert_called_once()

    def test_unimplemented_openai_path_never_downloads_or_synthesizes(self):
        generator = self.generator('openai')
        with patch.object(generator.image_processor, 'download_image') as download:
            self.assertIsNone(generator.generate_embedding('https://example.invalid/product.jpg'))
        download.assert_not_called()

    def test_unknown_method_is_a_configuration_error(self):
        with self.assertRaises(ValueError):
            self.generator('locla')

    def test_explicit_dummy_mode_is_repeatable_and_does_not_reseed_global_rng(self):
        generator = self.generator('dummy')
        state = random.getstate()
        first = generator.generate_embedding('fixture:product')
        second = generator.generate_embedding('fixture:product')
        self.assertEqual(state, random.getstate())
        self.assertEqual(first, second)
        self.assertEqual(len(first), 512)
        self.assertAlmostEqual(sum(value * value for value in first), 1.0)


if __name__ == '__main__':
    unittest.main()

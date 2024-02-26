import unittest
from ftio.cli.ftio_core import main

class TestCalculations(unittest.TestCase):
    
    def test_ftio(self):
        file = '../examples/8.jsonl'
        args = ['ftio', file, '-e', 'no']
        prediction, args = main(args)
        self.assertEqual(prediction['t_start'], 0.05309, 'The sum is wrong.')

    def test_ftio_dbscan(self):
        file = '../examples/8.jsonl'
        args = ['ftio', file, '-e', 'no', '-o', 'dbscan']
        prediction, args = main(args)
        self.assertEqual(prediction['t_start'], 0.05309, 'The sum is wrong.')
    
    def test_ftio_lof(self):
        file = '../examples/8.jsonl'
        args = ['ftio', file, '-e', 'no', '-o', 'lof']
        prediction, args = main(args)
        self.assertEqual(prediction['t_start'], 0.05309, 'The sum is wrong.')
    
 
if __name__ == '__main__':
    unittest.main()
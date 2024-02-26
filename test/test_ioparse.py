import unittest
from ftio.util.ioparse import main

class TestCalculations(unittest.TestCase):
    
    def test_ioplot(self):
        file = '../examples/8.jsonl'
        args = ['ioparse', file]
        main(args)
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
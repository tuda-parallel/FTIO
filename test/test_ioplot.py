import unittest
from ftio.util.ioplot import main

class TestCalculations(unittest.TestCase):
    
    def test_ioplot(self):
        file = '../examples/8.jsonl'
        args = ['ioplot', file, '--no_disp']
        main(args)
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
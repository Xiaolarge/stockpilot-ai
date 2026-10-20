import unittest
from fees import net_result,size_with_fees
class FeeTests(unittest.TestCase):
 def test_breakeven(self):
  a=net_result(200,200.38,2,.38,.38)
  self.assertAlmostEqual(a['net'],0)
  self.assertAlmostEqual(a['break_even'],200.38)
 def test_size_respects_fee(self):
  self.assertEqual(size_with_fees(650,1,200,195,1,.38,.38),1)
 def test_tiny_budget(self):
  self.assertEqual(size_with_fees(100,.1,20,19,1,.38,.38),0)
if __name__=='__main__': unittest.main()

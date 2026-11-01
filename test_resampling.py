import unittest
import numpy as np
import resampling as m
class BootstrapControls(unittest.TestCase):
 def test_wrap_and_truncate(self):np.testing.assert_array_equal(m.from_starts(np.array([[4,1]]),5,3),[[4,0,1,1,2]])
 def test_preserve_order(self):np.testing.assert_array_equal(m.from_starts(np.array([[1,3],[0,4]]),5,3),[[1,2,3,3,4],[0,1,2,4,0]])
 def test_invalid_start(self):
  with self.assertRaises(ValueError):m.from_starts(np.array([[5,1]]),5,3)
 def test_start_count(self):
  with self.assertRaises(ValueError):m.from_starts(np.array([[1]]),5,3)
 def test_constant(self):
  r=m.summarize([100]*3,np.array([[0,1,2],[2,1,0]]));self.assertEqual(r['bootstrap_daily_mean_usd_p05'],1)
 def test_linear_quantile(self):
  r=m.summarize([0,100],np.array([[0,0],[1,1]]));self.assertAlmostEqual(r['bootstrap_daily_mean_usd_p05'],.05);self.assertAlmostEqual(r['bootstrap_daily_mean_usd_p95'],.95)
 def test_zero_days_retained(self):self.assertEqual(m.summarize([0,0,300],np.array([[0,1,2]]))['mean_daily_usd'],1)
 def test_bad_index(self):
  with self.assertRaises(ValueError):m.summarize([100],np.array([[1]]))
 def test_float_changes_rejected(self):
  with self.assertRaises(ValueError):m.summarize([1.5],np.array([[0]]))
 def test_integer_sum_bound(self):
  with self.assertRaises(ValueError):m.summarize(np.array([2**62]*3,dtype=np.int64),np.array([[0,1,2]]))
 def test_fullshape_guard(self):
  with self.assertRaises(ValueError):m.analyze({s:{} for s in m.SCENARIOS},np.array([[0]]))
if __name__=='__main__':unittest.main()

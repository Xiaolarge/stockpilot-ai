import unittest
import numpy as np
import pandas as pd
from engine import analyze, Settings, swing_history

class EngineTests(unittest.TestCase):
    def test_analysis_and_risk(self):
        n = 180
        rng = np.random.default_rng(42)
        close = 100 + np.arange(n)*0.25 + rng.normal(0,.6,n)
        df = pd.DataFrame({'Open':close-.1,'High':close+1,'Low':close-1,'Close':close,'Volume':np.full(n,1_000_000)},index=pd.bdate_range('2025-01-01',periods=n))
        x, result = analyze(df,Settings(650,1,2,2))
        self.assertEqual(len(x),n)
        self.assertGreater(result['stop'],0)
        self.assertLessEqual(result['planned_max_loss'],6.5+1e-8)
        self.assertLessEqual(result['shares']*result['price'],650)
        self.assertIsInstance(swing_history(x),pd.DataFrame)

if __name__ == '__main__':
    unittest.main()

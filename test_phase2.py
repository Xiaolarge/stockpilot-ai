import unittest
import numpy as np
import pandas as pd
from phase2 import scan_one, backtest, summarize_financials

class Phase2Tests(unittest.TestCase):
    def setUp(self):
        n=240
        close=100+np.arange(n)*.35+np.sin(np.arange(n)/8)*3
        self.df=pd.DataFrame({'Open':close-.1,'High':close+1.1,'Low':close-1.1,'Close':close,'Volume':np.full(n,2_000_000)},index=pd.bdate_range('2025-01-01',periods=n))
    def test_scan(self):
        r=scan_one('TEST',self.df)
        self.assertTrue(0<=r['评分/100']<=100)
        self.assertEqual(r['代码'],'TEST')
    def test_backtest_no_leverage(self):
        trades,curve,stats=backtest(self.df,650,1,0,10,2,15)
        self.assertTrue((curve['权益$']>=0).all())
        self.assertTrue(stats['已平仓次数']>=0)
        if not trades.empty:
            self.assertTrue((trades['股数']>=1).all())
    def test_missing_financial(self):
        result=summarize_financials({},pd.DataFrame())
        self.assertTrue(result['数值'].isna().all())

if __name__=='__main__': unittest.main()

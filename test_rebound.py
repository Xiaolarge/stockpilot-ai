import unittest
import numpy as np
import pandas as pd
from rebound import rebound_plan
class TestRebound(unittest.TestCase):
    def test_plan_and_lot(self):
        n=140
        close=np.r_[np.linspace(100,130,100),np.linspace(130,90,20),np.linspace(90,102,20)]
        df=pd.DataFrame({'Open':close,'High':close+1,'Low':close-1,'Close':close,'Volume':np.full(n,1000000)},index=pd.bdate_range('2025-01-01',periods=n))
        p=rebound_plan('TEST',df,10000,1,1,10)
        self.assertTrue(p['参考止损']<p['观察入场上沿']<p['参考止盈'])
        jp=rebound_plan('TEST.T',df,10000,1,100,10)
        self.assertEqual(jp['参考股数']%100,0)
if __name__=='__main__':unittest.main()

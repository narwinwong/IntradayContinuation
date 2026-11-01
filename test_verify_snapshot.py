from pathlib import Path
import copy,json,tempfile,unittest
import verify_snapshot as v
class SnapshotControls(unittest.TestCase):
 def setUp(self):self.r=json.loads((Path(__file__).parent/'results.json').read_text())
 def test_saved_snapshot(self):self.assertEqual(v.verify()['primary_net_pnl_cents'],-14342)
 def test_daily_tamper(self):
  self.r['accounts']['primary']['continuation']['daily'][3]['delta_cents']+=1
  with self.assertRaises(ValueError):v.audit(self.r)
 def test_pending_tamper(self):
  self.r['accounts']['primary']['continuation']['final_pending_cash_cents']+=1
  with self.assertRaises(ValueError):v.audit(self.r)
 def test_decision_tamper(self):
  self.r['statistics']['decision']='PASS'
  with self.assertRaises(ValueError):v.audit(self.r)
 def test_edge_tamper(self):
  self.r['verified_edge']=True
  with self.assertRaises(ValueError):v.audit(self.r)
 def test_private_daily_field(self):
  self.r['accounts']['primary']['continuation']['daily'][0]['shares']=1
  with self.assertRaises(ValueError):v.audit(self.r)
 def test_hash_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'results.json';p.write_text(json.dumps(self.r)+' ')
   with self.assertRaises(ValueError):v.verify(p)
 def test_crlf_copy(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'results.json';p.write_bytes((Path(__file__).parent/'results.json').read_bytes().replace(b'\n',b'\r\n'));self.assertEqual(v.verify(p)['accounts_checked'],20)
if __name__=='__main__':unittest.main()

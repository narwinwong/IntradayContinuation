import unittest
from datetime import date,datetime,time,timedelta,timezone
from unittest.mock import patch
import source_grid as m
class SourceControls(unittest.TestCase):
 def rows(self,day=date(2010,1,5)):
  out=[]
  for h,minute in ((9,30),(15,30)):
   t=datetime.combine(day,time(h,minute),m.NY).astimezone(timezone.utc)
   for i in range(30):out.append([(t+timedelta(minutes=i)).isoformat(),'100','101','99','100','1','1'])
  return out
 def body(self,rows=None):return (','.join(m.COLUMNS)+'\n'+'\n'.join(','.join(r) for r in (self.rows() if rows is None else rows))+'\n').encode()
 def runrows(self,rows=None,day=date(2010,1,5)):return m.inspect(self.body(rows),(day,))
 def test_complete(self):
  rows,q=self.runrows();self.assertEqual(len(rows),60);self.assertFalse(q['returns_computed'])
 def test_calendar(self):self.assertEqual(len(m.default_sessions()),123)
 def test_dst(self):
  rows,q=self.runrows(self.rows(date(2010,3,15)),date(2010,3,15));self.assertIn('13:30',rows[0]['time'])
 def test_missing(self):
  with self.assertRaises(ValueError):self.runrows(self.rows()[:-1])
 def test_duplicate(self):
  r=self.rows();r.insert(1,r[0])
  with self.assertRaises(ValueError):self.runrows(r)
 def test_reversed(self):
  with self.assertRaises(ValueError):self.runrows(list(reversed(self.rows())))
 def test_subminute(self):
  r=self.rows();r[0][0]=r[0][0].replace(':00+00:00',':01+00:00')
  with self.assertRaises(ValueError):self.runrows(r)
 def test_invalid_ohlc(self):
  r=self.rows();r[0][2]='90'
  with self.assertRaises(ValueError):self.runrows(r)
 def test_nonpositive_price(self):
  r=self.rows();r[0][1]='0'
  with self.assertRaises(ValueError):self.runrows(r)
 def test_fractional_count(self):
  r=self.rows();r[0][-1]='1.5'
  with self.assertRaises(ValueError):self.runrows(r)
 def test_zero_counts(self):
  r=self.rows();r[0][-2:]=['0','0'];self.assertEqual(self.runrows(r)[1]['selected_minutes'],60)
 def test_excluded_values_unparsed(self):
  r=self.rows();r.insert(30,['2010-01-05T17:00:00+00:00']+['NOT_A_NUMBER']*6)
  self.assertEqual(self.runrows(r)[1]['rows_excluded_before_financial_conversion'],1)
 def test_wrong_header(self):
  with self.assertRaises(ValueError):m.inspect(b'time,x\n',(date(2010,1,5),))
 def test_byte_cap(self):
  with patch.object(m,'CAP',10):
   with self.assertRaises(ValueError):self.runrows()
 def test_row_cap(self):
  with patch.object(m,'ROW_CAP',1):
   with self.assertRaises(ValueError):self.runrows()
 def test_custom_duplicate_days(self):
  with self.assertRaises(ValueError):m.inspect(self.body(),(date(2010,1,5),date(2010,1,5)))
if __name__=='__main__':unittest.main()

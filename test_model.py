"""Small fabricated arithmetic paths only; no source file or bootstrap access."""
from datetime import date,datetime,time,timedelta,timezone
from decimal import localcontext
import unittest
import model as m

def bars(day=date(2010,1,5),first='99',signal='100',entry='100',exit='101',delay='100'):
    out=[]
    for h,minute,op,cl in ((9,30,first,first),(9,59,signal,signal),(15,31,entry,entry),(15,32,delay,delay),(15,59,exit,exit)):
        t=datetime.combine(day,time(h,minute),m.NY).astimezone(timezone.utc)
        out.append({'date':day.isoformat(),'time':t.isoformat(),'open':op,'close':cl})
    return out

class CashControls(unittest.TestCase):
 def test_no_fees_known_cash_profit(self):
    r=m.run(bars(),'zero_cost','continuation')
    self.assertEqual(r['net_pnl_cents'],2000);self.assertEqual(r['trades'],1)
    self.assertEqual(r['total_shares'],20);self.assertEqual(r['final_equity_cents'],1002000)
 def test_primary_cost_order(self):
    r=m.run(bars(),'primary','continuation')
    self.assertEqual(r['total_entry_notional_cents'],200040)
    self.assertEqual(r['total_exit_notional_cents'],201940)
    self.assertEqual(r['total_fees_cents'],200);self.assertEqual(r['net_pnl_cents'],1700)
 def test_zero_explicit_cost_still_quantizes(self):
    self.assertEqual(m.fill_cents('100.001','buy','zero_cost'),10001)
    self.assertEqual(m.fill_cents('100.009','sell','zero_cost'),10000)
 def test_fee_double_rounded_primary(self):
    self.assertEqual(m.commission_cents(201,'primary'),101)
    self.assertEqual(m.commission_cents(201,'fee_double'),202)
 def test_minimum_fee(self):
    self.assertEqual(m.commission_cents(1,'primary'),100)
    self.assertEqual(m.commission_cents(1,'zero_cost'),0)
 def test_strict_positive_signal(self):
    for first in ('100','101'):
        r=m.run(bars(first=first),'zero_cost','continuation')
        self.assertEqual(r['trades'],0);self.assertEqual(r['signal_flat'],1);self.assertEqual(r['net_pnl_cents'],0)
 def test_always_long_negative_signal(self):
    self.assertEqual(m.run(bars(first='101'),'zero_cost','always_long20')['trades'],1)
 def test_half_allocation_fixed(self):
    self.assertEqual(m.run(bars(),'zero_cost','always_long10')['total_shares'],10)
    self.assertEqual(m.run(bars(),'zero_cost','always_long20')['total_shares'],20)
 def test_cash_control(self):
    r=m.run(bars(),'primary','cash');self.assertEqual(r['trades'],0);self.assertEqual(r['net_pnl_cents'],0)
    self.assertEqual(r['cash_control'],1);self.assertEqual(r['final_pending_cash_cents'],0)
 def test_sizing_uses_signal_not_future_entry(self):
    r=m.run(bars(entry='400'),'zero_cost','continuation')
    self.assertEqual(r['daily'][0]['planned_shares'],20);self.assertEqual(r['total_shares'],20)
 def test_unaffordable_skip_without_resize(self):
    r=m.run(bars(entry='600'),'zero_cost','continuation')
    self.assertEqual(r['insufficient_cash'],1);self.assertEqual(r['daily'][0]['planned_shares'],20)
    self.assertEqual(r['trades'],0);self.assertEqual(r['final_equity_cents'],1000000)
 def test_pending_receipts_unavailable_next_day(self):
    rows=bars(exit='100')+bars(date(2010,1,6),exit='100')
    r=m.run(rows,'zero_cost','continuation')
    self.assertEqual([d['shares'] for d in r['daily']],[20,16])
    self.assertEqual(r['final_settled_cash_cents'],640000);self.assertEqual(r['final_pending_cash_cents'],360000)
 def test_receipt_settles_at_ten_calendar_days(self):
    rows=bars(exit='100')+bars(date(2010,1,15),exit='100')
    r=m.run(rows,'zero_cost','continuation')
    self.assertEqual([d['shares'] for d in r['daily']],[20,20])
    self.assertEqual(m.cash.delayed_credit_date(date(2010,1,5),m.credit_calendar(date(2010,1,5),date(2010,1,15))),date(2010,1,15))
 def test_losing_trade_retained_drawdown(self):
    r=m.run(bars(exit='99'),'zero_cost','continuation')
    self.assertEqual(r['net_pnl_cents'],-2000);self.assertEqual(r['loss_trades'],1)
    self.assertEqual(r['daily_closing_max_drawdown_cents'],2000);self.assertEqual(r['daily'][0]['delta_cents'],-2000)
 def test_delayed_entry_and_holding(self):
    r=m.run(bars(delay='99'),'delay_stress','continuation')
    self.assertEqual(r['total_holding_minutes'],27)
    self.assertEqual(r['total_entry_notional_cents'],198040)
 def test_zero_quantity_skip(self):
    r=m.run(bars(first='9999',signal='10000'),'zero_cost','continuation')
    self.assertEqual(r['zero_quantity'],1);self.assertEqual(r['trades'],0)
 def test_no_missing_exit(self):
    with self.assertRaises(ValueError):m.run(bars()[:-1],'primary','continuation')
 def test_duplicate_or_reverse_rejected(self):
    for rows in (bars()+[bars()[-1]],list(reversed(bars()))):
      with self.assertRaises(ValueError):m.run(rows,'primary','continuation')
 def test_wrong_clock_date(self):
    rows=bars();rows[0]['date']='2010-01-06'
    with self.assertRaises(ValueError):m.run(rows,'primary','continuation')
 def test_unknown_policy_scenario(self):
    with self.assertRaises(ValueError):m.run(bars(),'unregistered','continuation')
    with self.assertRaises(ValueError):m.run(bars(),'primary','short')
 def test_caller_precision_cannot_change_result(self):
    expected=m.run(bars(),'primary','continuation')
    with localcontext() as context:
      context.prec=2
      self.assertEqual(m.run(bars(),'primary','continuation'),expected)
 def test_no_source_price_output_and_conservation(self):
    r=m.run(bars(),'primary','continuation')
    self.assertEqual(r['final_settled_cash_cents']+r['final_pending_cash_cents'],r['final_equity_cents'])
    self.assertEqual(r['net_pnl_cents'],sum(d['delta_cents'] for d in r['daily']))
    self.assertTrue(r['no_overnight_shares']);self.assertFalse(r['prop_payouts_modeled'])
    self.assertFalse(any(k in r['daily'][0] for k in ('open','close','entry_price','exit_price')))

if __name__=='__main__':unittest.main()

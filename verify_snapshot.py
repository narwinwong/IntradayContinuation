"""Saved-summary checks only: no model imports, RNG, source inputs or network."""
from pathlib import Path
from datetime import date,timedelta
import hashlib,json,math
ROOT=Path(__file__).resolve().parent
SCENARIOS=('zero_cost','primary','fee_double','slip_double','delay_stress')
POLICIES=('continuation','always_long20','always_long10','cash')
EXPECTED_HASH='ddf934cb4a92be0addbbad101cb314d6ad10323af6aeed95c2c0b28537a4e42c'

def require(condition,label):
 if not condition:raise ValueError(label)
def integer(x):return type(x) is int

def audit(r):
 require(set(r)=={'classification','accounts','statistics','market_oos','prop_payout_evaluated','verified_edge'},'top-level scope')
 require(r['classification']=='EXPLORATORY_REUSED_VENDOR_BAR_REFERENCE' and all(r[k] is False for k in ('market_oos','prop_payout_evaluated','verified_edge')),'classification limits')
 require(set(r['accounts'])==set(SCENARIOS),'scenarios')
 days=None
 for s in SCENARIOS:
  require(set(r['accounts'][s])==set(POLICIES),'policies')
  for p in POLICIES:
   a=r['accounts'][s][p];daily=a['daily']
   require(a['scenario']==s and a['policy']==p and a['sessions']==123 and len(daily)==123,'account identity')
   require(a['initial_equity_cents']==1000000,'initial cash')
   dates=[d['date'] for d in daily]
   require(dates==sorted(set(dates)) and dates[0]=='2010-01-05' and dates[-1]=='2010-06-30','dates')
   require(all(date.fromisoformat(d).weekday()<5 for d in dates),'weekdays')
   if days is None:days=dates
   require(dates==days,'paired dates')
   prior=peak=1000000;drawdown=0;net=0
   for d in daily:
    require(set(d)=={'date','equity_cents','delta_cents'},'derived-only daily schema')
    require(integer(d['equity_cents']) and integer(d['delta_cents']),'cent integers')
    require(d['equity_cents']==prior+d['delta_cents'],'daily cash identity')
    prior=d['equity_cents'];net+=d['delta_cents'];peak=max(peak,prior);drawdown=max(drawdown,peak-prior)
   require(net==a['net_pnl_cents'] and prior==a['final_equity_cents']==1000000+net,'final cash identity')
   require(a['final_settled_cash_cents']+a['final_pending_cash_cents']==prior,'pending cash identity')
   require(a['final_settled_cash_cents']>=0,'settled cash nonnegative')
   require(drawdown==a['daily_closing_max_drawdown_cents'],'daily drawdown')
   require(sum(a[k] for k in ('trades','signal_flat','zero_quantity','insufficient_cash','cash_control'))==123,'attempt mass')
   require(sum(a[k] for k in ('profit_trades','loss_trades','flat_trades'))==a['trades'],'trade mass')
   require(a['total_holding_minutes']==a['trades']*(27 if s=='delay_stress' else 28),'holding interval')
   require(a['no_overnight_shares'] is True and a['actual_execution_qualified'] is False and a['prop_payouts_modeled'] is False and a['settlement_assumed_calendar_days']==10,'account limits')
   require(not {'total_entry_notional_cents','total_exit_notional_cents'}&set(a),'private notionals excluded')
   if p=='cash':require(net==a['trades']==a['total_fees_cents']==0,'cash control')
   if s=='zero_cost':require(a['total_fees_cents']==0,'zero explicit fees')
   else:require(a['total_fees_cents']>=a['trades']*(400 if s=='fee_double' else 200),'minimum commissions')
   summary=r['statistics']['summaries'][s][p]
   require(summary['sessions']==123 and summary['sum_cents']==net and math.isclose(summary['mean_daily_usd'],net/12300,abs_tol=1e-12),'summary moments')
   lo=summary['bootstrap_daily_mean_usd_p05'];hi=summary['bootstrap_daily_mean_usd_p95']
   require(math.isfinite(lo) and math.isfinite(hi) and lo<=hi,'recorded percentile order')
 stats=r['statistics'];ex=stats['primary_minus_fixed10'];a=r['accounts']['primary']['continuation'];b=r['accounts']['primary']['always_long10']
 require(ex['sum_cents']==a['net_pnl_cents']-b['net_pnl_cents'] and math.isclose(ex['mean_daily_usd'],ex['sum_cents']/12300,abs_tol=1e-12),'paired excess')
 criteria={'at_least30trades':a['trades']>=30,'primary_net_positive':a['net_pnl_cents']>0,'primary_excess_p05_positive':ex['bootstrap_daily_mean_usd_p05']>0,'all_three_stress_nets_positive':all(r['accounts'][s]['continuation']['net_pnl_cents']>0 for s in ('fee_double','slip_double','delay_stress'))}
 require(stats['criteria']==criteria and not all(criteria.values()) and stats['decision']=='FIXED_EXPLORATORY_POLICY_FAILED','failed screen')
 require(stats['verified_edge'] is False and stats['independent_market_oos'] is False and stats['execution_qualified'] is False,'statistical limits')
 bs=stats['bootstrap'];require(bs['reps']==5000 and bs['seed']==2026103104 and bs['block_sessions']==5 and bs['indices_shape']==[5000,123] and bs['quantile_method']=='linear' and bs['paired'] is True and bs['replays_cash_eligibility'] is False,'bootstrap contract')
 return {'accounts_checked':20,'sessions_per_account':123,'primary_net_pnl_cents':a['net_pnl_cents'],'raw_data_replication':False,'bootstrap_regenerated':False,'verified_edge':False}

def verify(path=ROOT/'results.json'):
 body=Path(path).read_bytes().replace(b'\r\n',b'\n')
 require(hashlib.sha256(body).hexdigest()==EXPECTED_HASH,'reviewed snapshot hash')
 return audit(json.loads(body))
if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))

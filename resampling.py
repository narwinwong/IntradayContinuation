"""Paired E19 daily-change uncertainty, never synthetic account paths."""
import hashlib
import numpy as np
REPS=5000
SEED=2026103104
BLOCK=5
DAYS=123
POLICIES=('continuation','always_long20','always_long10','cash')
SCENARIOS=('zero_cost','primary','fee_double','slip_double','delay_stress')

def from_starts(starts,n,block):
 if not isinstance(starts,np.ndarray) or starts.dtype.kind not in 'iu' or starts.ndim!=2 or n<1 or block<1 or starts.shape[1]!=(n+block-1)//block or np.any(starts<0) or np.any(starts>=n):raise ValueError('invalid circular start grid')
 return ((starts[:,:,None]+np.arange(block))%n).reshape(len(starts),-1)[:,:n]

def registered_indices():
 rng=np.random.Generator(np.random.PCG64(SEED))
 starts=rng.integers(0,DAYS,size=(REPS,25))
 return from_starts(starts,DAYS,BLOCK)

def summarize(series,indices):
 x=np.asarray(series)
 if x.ndim!=1 or x.dtype.kind not in 'iu' or not len(x) or indices.ndim!=2 or indices.dtype.kind not in 'iu' or indices.shape[1]!=len(x) or not len(indices) or np.any(indices<0) or np.any(indices>=len(x)):raise ValueError('integer daily cash/index grid required')
 if max(abs(int(x.min())),abs(int(x.max())))>np.iinfo(np.int64).max//len(x):raise ValueError('cash sums exceed exact integer range')
 means=x[indices].mean(axis=1)/100
 return {'sessions':len(x),'sum_cents':int(x.sum()),'mean_daily_usd':float(x.mean()/100),'bootstrap_daily_mean_usd_p05':float(np.quantile(means,.05,method='linear')),'bootstrap_daily_mean_usd_p95':float(np.quantile(means,.95,method='linear'))}

def analyze(accounts,indices):
 if set(accounts)!=set(SCENARIOS):raise ValueError('all five scenarios required')
 if indices.shape!=(REPS,DAYS):raise ValueError('registered paired bootstrap shape')
 out={}
 for scenario in SCENARIOS:
  if set(accounts[scenario])!=set(POLICIES):raise ValueError('all four policies required')
  out[scenario]={}
  for policy in POLICIES:
   daily=accounts[scenario][policy]['daily']
   if len(daily)!=DAYS:raise ValueError('all123days required')
   out[scenario][policy]=summarize([d['delta_cents'] for d in daily],indices)
 a=np.array([d['delta_cents'] for d in accounts['primary']['continuation']['daily']],dtype=np.int64)
 b=np.array([d['delta_cents'] for d in accounts['primary']['always_long10']['daily']],dtype=np.int64)
 excess=summarize(a-b,indices)
 policy=accounts['primary']['continuation']
 trades=sum(bool(d['trade']) for d in policy['daily'])
 tests={'at_least30trades':trades>=30,'primary_net_positive':int(a.sum())>0,'primary_excess_p05_positive':excess['bootstrap_daily_mean_usd_p05']>0,'all_three_stress_nets_positive':all(sum(d['delta_cents'] for d in accounts[s]['continuation']['daily'])>0 for s in ('fee_double','slip_double','delay_stress'))}
 return {'summaries':out,'primary_minus_fixed10':excess,'criteria':tests,'decision':'CONDITIONAL_DEVELOPMENT_PASS_NOT_EDGE' if all(tests.values()) else 'FIXED_EXPLORATORY_POLICY_FAILED','bootstrap':{'reps':REPS,'seed':SEED,'rng':'numpy.PCG64','block_sessions':BLOCK,'indices_shape':list(indices.shape),'indices_sha256':hashlib.sha256(indices.tobytes()).hexdigest(),'quantile_method':'linear','paired':True,'replays_cash_eligibility':False},'independent_market_oos':False,'execution_qualified':False,'verified_edge':False}

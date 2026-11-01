"""Pure E19 cash ledger over provided selected bars; never reads source files."""
from datetime import date,datetime,timedelta
from decimal import Decimal
from fractions import Fraction
from calendar_rules import NY,planned_open
import cash_ledger as cash

SCENARIOS=('zero_cost','primary','fee_double','slip_double','delay_stress')
POLICIES=('continuation','always_long20','always_long10','cash')
INITIAL_CENTS=1000000

def cents(value):
    q=Fraction(value)*100
    if q.denominator!=1:raise ValueError('noncent cash amount')
    return q.numerator

def decimal_cents(value):
    if type(value) is not int:raise ValueError('integer cents required')
    sign='-' if value<0 else '';value=abs(value)
    return Decimal(f'{sign}{value//100}.{value%100:02d}')

def ceil_fraction(value):return -(-value.numerator//value.denominator)

def price(value):
    if type(value) is not str:raise ValueError('source price text required')
    try:x=Decimal(value)
    except Exception as error:raise ValueError('source price syntax') from error
    if not x.is_finite() or not 0<x<=Decimal('1e12'):raise ValueError('positive bounded price')
    return Fraction(x)

def fill_cents(raw,side,scenario):
    if side not in ('buy','sell') or scenario not in SCENARIOS:raise ValueError('fill identity')
    bp=0 if scenario=='zero_cost' else 4 if scenario=='slip_double' else 2
    value=price(raw)*(1+Fraction(bp,10000) if side=='buy' else 1-Fraction(bp,10000))*100
    result=ceil_fraction(value) if side=='buy' else value.numerator//value.denominator
    if result<=0:raise ValueError('nonpositive quantized fill')
    return result

def commission_cents(quantity,scenario):
    if type(quantity) is not int or quantity<=0 or scenario not in SCENARIOS:raise ValueError('commission identity')
    if scenario=='zero_cost':return 0
    primary=ceil_fraction(max(Fraction(100),Fraction(quantity,2)))
    return primary*(2 if scenario=='fee_double' else 1)

def quantity(cash_cents,signal_price,policy):
    if type(cash_cents) is not int or cash_cents<0 or policy not in POLICIES:raise ValueError('quantity input')
    allocation=Fraction(0) if policy=='cash' else Fraction(1,10) if policy=='always_long10' else Fraction(1,5)
    amount=Fraction(cash_cents,100)*allocation/price(signal_price)
    return amount.numerator//amount.denominator

def organize(rows):
    if not isinstance(rows,(list,tuple)) or not rows:raise ValueError('provided rows required')
    byday={};previous=None
    for row in rows:
        if type(row) is not dict:raise ValueError('bar mapping required')
        try:
            t=datetime.fromisoformat(row['time']);day=date.fromisoformat(row['date'])
        except Exception as error:raise ValueError('bar clock/date syntax') from error
        if t.tzinfo is None:raise ValueError('aware timestamp required')
        local=t.astimezone(NY)
        if local.date()!=day or local.second or local.microsecond:raise ValueError('bar clock/date disagreement')
        if previous is not None and t<=previous:raise ValueError('ordered unique bars required')
        previous=t
        if day.year!=2010 or not planned_open(day):raise ValueError('conditional 2010 planned dates required')
        key=(local.hour,local.minute)
        if key in byday.setdefault(day,{}):raise ValueError('duplicate local bar')
        # Source parser owns the full grid; engine revalidates all accessed price texts.
        price(row['open']);price(row['close'])
        byday[day][key]=row
    for bars in byday.values():
        if not {(9,30),(9,59),(15,31),(15,32),(15,59)}<=bars.keys():raise ValueError('required decision/fill bars absent')
    return byday

def credit_calendar(first,last):
    if first.year!=2010 or last>date(2010,6,30):raise ValueError('development date bound')
    result=[];day=first
    while day<=date(2010,7,15):
        if planned_open(day):result.append(day)
        day+=timedelta(days=1)
    return tuple(result)

@cash.exact
def run(rows,scenario,policy):
    if scenario not in SCENARIOS or policy not in POLICIES:raise ValueError('fixed scenario/policy required')
    byday=organize(rows);days=tuple(sorted(byday));calendar=credit_calendar(days[0],days[-1])
    state=cash.State(days[0]-timedelta(days=1),decimal_cents(INITIAL_CENTS))
    prior_equity=peak=INITIAL_CENTS;drawdown=0;daily=[]
    totals={'trades':0,'signal_flat':0,'zero_quantity':0,'insufficient_cash':0,'cash_control':0,
            'profit_trades':0,'loss_trades':0,'flat_trades':0,'total_shares':0,
            'total_entry_notional_cents':0,'total_exit_notional_cents':0,'total_fees_cents':0,'total_holding_minutes':0}
    for day in days:
        state=cash.open_session(state,day);bars=byday[day]
        signal_positive=price(bars[(9,59)]['close'])>price(bars[(9,30)]['open'])
        trade=False;skip=None;shares=0;holding=0;trade_net=None
        if policy=='cash':skip='cash_control'
        elif policy=='continuation' and not signal_positive:skip='signal_flat'
        else:
            shares=quantity(cents(state.cash),bars[(9,59)]['close'],policy)
            if shares==0:skip='zero_quantity'
            else:
                minute=32 if scenario=='delay_stress' else 31
                entry=fill_cents(bars[(15,minute)]['open'],'buy',scenario)
                exit_price=fill_cents(bars[(15,59)]['open'],'sell',scenario)
                fee=commission_cents(shares,scenario)
                if shares*entry+fee>cents(state.cash):skip='insufficient_cash'
                else:
                    due=cash.delayed_credit_date(day,calendar)
                    state=cash.buy(state,shares,decimal_cents(entry),decimal_cents(fee))
                    state=cash.sell_all(state,decimal_cents(exit_price),decimal_cents(fee),due=due)
                    trade=True;holding=59-minute;trade_net=shares*(exit_price-entry)-2*fee
                    totals['trades']+=1;totals['total_shares']+=shares
                    totals['total_entry_notional_cents']+=shares*entry
                    totals['total_exit_notional_cents']+=shares*exit_price
                    totals['total_fees_cents']+=2*fee;totals['total_holding_minutes']+=holding
                    totals['profit_trades' if trade_net>0 else 'loss_trades' if trade_net<0 else 'flat_trades']+=1
        if skip:totals[skip]+=1
        equity=cents(cash.equity(state));delta=equity-prior_equity
        if delta!=(trade_net if trade else 0):raise ValueError('daily cash conservation')
        peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
        daily.append({'date':day.isoformat(),'equity_cents':equity,'delta_cents':delta,'trade':trade,
                      'skip':skip,'shares':shares if trade else 0,'planned_shares':shares,
                      'holding_minutes':holding})
        prior_equity=equity
    if totals['trades']+sum(totals[k] for k in ('signal_flat','zero_quantity','insufficient_cash','cash_control'))!=len(days):raise ValueError('session mass')
    final=cents(cash.equity(state));pending=sum(cents(x.amount) for x in state.pending)
    net=totals['total_exit_notional_cents']-totals['total_entry_notional_cents']-totals['total_fees_cents']
    if final!=INITIAL_CENTS+net or final!=cents(state.cash)+pending or sum(x['delta_cents'] for x in daily)!=net:raise ValueError('account reconciliation')
    return {'scenario':scenario,'policy':policy,'sessions':len(days),'initial_equity_cents':INITIAL_CENTS,
            'daily':daily,**totals,'net_pnl_cents':net,'final_equity_cents':final,
            'final_settled_cash_cents':cents(state.cash),'final_pending_cash_cents':pending,
            'daily_closing_max_drawdown_cents':drawdown,'no_overnight_shares':state.shares==0,
            'settlement_assumed_calendar_days':10,'actual_execution_qualified':False,'prop_payouts_modeled':False}

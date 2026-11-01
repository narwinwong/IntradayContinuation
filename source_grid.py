"""Pure E19 selected-minute parser. No file I/O, downloads or return calculation."""
import csv
from datetime import date,datetime,time,timedelta,timezone
from decimal import Decimal
import hashlib
import io
import re
from calendar_rules import NY,planned_open
from clock import timestamp

CAP=40*1024*1024
ROW_CAP=300000
COLUMNS=['time','open','high','low','close','volume','trades']
GRAMMAR=re.compile(r'[0-9]+(?:\.[0-9]+)?',re.ASCII)

def default_sessions():
 day=date(2010,1,5);result=[]
 while day<=date(2010,6,30):
  if planned_open(day):result.append(day)
  day+=timedelta(days=1)
 return tuple(result)

def number(token,count=False):
 if type(token) is not str or not 0<len(token)<=60 or not GRAMMAR.fullmatch(token):raise ValueError('NUMERIC_GRAMMAR')
 x=Decimal(token)
 if not x.is_finite() or x>Decimal('1e12') or (x<0 if count else x<=0):raise ValueError('NUMERIC_DOMAIN')
 if count and x.as_integer_ratio()[1]!=1:raise ValueError('NONINTEGER_COUNT')
 return x

def inspect(body,sessions=None):
 """Provided bytes only; custom sessions exist for tiny controls, not actual runner."""
 if type(body) is not bytes or not 0<len(body)<=CAP:raise ValueError('BODY_CAP')
 days=default_sessions() if sessions is None else sessions
 if type(days) is not tuple or not days or any(type(d) is not date for d in days) or any(a>=b for a,b in zip(days,days[1:])):raise ValueError('SESSION_GRID')
 expected=set()
 for day in days:
  for h,m in ((9,30),(15,30)):
   first=datetime.combine(day,time(h,m),NY).astimezone(timezone.utc)
   expected.update(first+timedelta(minutes=i) for i in range(30))
 dayset=set(days);reader=csv.reader(io.StringIO(body.decode('utf-8-sig'),newline=''))
 if next(reader,None)!=COLUMNS:raise ValueError('HEADER_SCHEMA')
 seen=set();previous=None;rows=[];scanned=excluded=0
 for fields in reader:
  scanned+=1
  if scanned>ROW_CAP:raise ValueError('ROW_CAP')
  if len(fields)!=7:raise ValueError('ROW_SCHEMA')
  if len(fields[0])>64:raise ValueError('TIME_FORMAT')
  t=timestamp(fields[0]);local=t.astimezone(NY)
  if local.date() not in dayset or not ((9,30)<=(local.hour,local.minute)<(10,0) or (15,30)<=(local.hour,local.minute)<(16,0)):
   excluded+=1;continue
  if t not in expected:raise ValueError('SHIFTED_MINUTE')
  if t in seen or (previous is not None and t<=previous):raise ValueError('DUPLICATE_OR_ORDER')
  values=[number(token,count=i>=4) for i,token in enumerate(fields[1:])]
  o,hi,lo,c=values[:4]
  if not lo<=min(o,c)<=max(o,c)<=hi:raise ValueError('OHLC_COHERENCE')
  rows.append({'time':t.isoformat(),'date':local.date().isoformat(),**dict(zip(COLUMNS[1:],fields[1:]))})
  seen.add(t);previous=t
 if seen!=expected:raise ValueError('INCOMPLETE_SELECTED_GRID')
 return rows,{'classification':'E19_SELECTED_VENDOR_BAR_GRID_ONLY','sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'rows_scanned':scanned,'rows_excluded_before_financial_conversion':excluded,'selected_minutes':len(rows),'selected_sessions':len(days),'returns_computed':False,'source_clock_or_native_units_verified':False}

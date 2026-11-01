"""Immutable conditional stock cash ledger, not a broker or strategy backtest."""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Context, Decimal, Inexact, Rounded, localcontext
from functools import wraps

MAX_MONEY = Decimal('1e12')
MAX_SHARES = 10**9
MAX_PENDING = 10_000


def exact(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        context = Context(prec=50)
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        with localcontext(context):
            return function(*args, **kwargs)
    return wrapped


def money(value, *, positive=False):
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError('finite Decimal required')
    if value.copy_abs() > MAX_MONEY or not -6 <= value.as_tuple().exponent <= 12:
        raise ValueError('money domain: magnitude <=1e12 and at most six decimal places')
    if positive and value <= 0:
        raise ValueError('positive price required')
    return value


def day(value):
    if type(value) is not date:
        raise ValueError('explicit date required')
    return value


@dataclass(frozen=True)
class Pending:
    due: date
    amount: Decimal

    def __post_init__(self):
        day(self.due)
        money(self.amount)  # Signed sale proceeds: a negative amount is payable.


@dataclass(frozen=True)
class State:
    day: date
    cash: Decimal
    shares: int = 0
    pending: tuple = ()

    def __post_init__(self):
        day(self.day)
        if money(self.cash) < 0:
            raise ValueError('negative settled cash')
        if type(self.shares) is not int or not 0 <= self.shares <= MAX_SHARES:
            raise ValueError('nonnegative whole shares required')
        if (type(self.pending) is not tuple or len(self.pending) > MAX_PENDING
                or any(type(p) is not Pending for p in self.pending)):
            raise ValueError('immutable pending items required')
        if any(p.due <= self.day for p in self.pending):
            raise ValueError('overdue items must be settled before this state')


@exact
def open_session(state, session):
    day(session)
    if session <= state.day:
        raise ValueError('session must advance')
    if state.shares:
        raise ValueError('overnight position forbidden by this component')
    # Catching up several dates must not use a later receipt to hide an earlier
    # deficit. Same-date items net together under this date-only assumption.
    grouped = {}
    for pending in state.pending:
        if pending.due <= session:
            grouped[pending.due] = grouped.get(pending.due, Decimal(0)) + pending.amount
    cash = state.cash
    for due in sorted(grouped):
        cash += grouped[due]
        if cash < 0:
            raise ValueError('insufficient cash at an intervening credit date')
    return State(session, cash, 0,
                 tuple(p for p in state.pending if p.due > session))


@exact
def buy(state, quantity, price, fee):
    if type(quantity) is not int or not 0 < quantity <= MAX_SHARES:
        raise ValueError('positive whole-share quantity required')
    money(price, positive=True)
    if money(fee) < 0:
        raise ValueError('negative fee')
    if state.shares:
        raise ValueError('existing position')
    cost = quantity * price + fee
    if cost > state.cash:
        raise ValueError('insufficient settled cash; pending receipts unavailable')
    return State(state.day, state.cash - cost, quantity, state.pending)


@exact
def sell_all(state, price, fee, *, due):
    money(price, positive=True)
    if money(fee) < 0:
        raise ValueError('negative fee')
    day(due)
    if not state.shares or due <= state.day:
        raise ValueError('position and strictly later credit date required')
    net = state.shares * price - fee
    return State(state.day, state.cash, 0, state.pending + (Pending(due, net),))


@exact
def equity(state, *, mark=None):
    if state.shares:
        money(mark, positive=True)
        inventory = state.shares * mark
    else:
        inventory = Decimal(0)
    return state.cash + inventory + sum((p.amount for p in state.pending), Decimal(0))


def delayed_credit_date(sold, planned_sessions):
    """Ten-calendar-day assumption only; supplied dates are not verified clearing days."""
    day(sold)
    sessions = tuple(planned_sessions)
    for session in sessions:
        day(session)
    if any(a >= b for a, b in zip(sessions, sessions[1:])):
        raise ValueError('strictly ordered unique planned sessions required')
    threshold = sold + timedelta(days=10)
    for session in sessions:
        if session >= threshold:
            return session
    raise ValueError('insufficient supplied session coverage; no date invented')

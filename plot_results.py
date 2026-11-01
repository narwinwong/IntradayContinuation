"""Read saved E19 summaries only; never imports model or source readers."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent

def main():
 r=json.loads((ROOT/'results.json').read_text(encoding='utf-8'))
 fig,axes=plt.subplots(1,2,figsize=(12,5))
 for p,label in [('continuation','Continuation'),('always_long20','Always long, 20%'),('always_long10','Always long, 10%'),('cash','Cash')]:
  a=r['accounts']['primary'][p]
  axes[0].plot([0]+[d['equity_cents']/100-10000 for d in a['daily']],label=label)
 axes[0].set_xlabel('Development session');axes[0].set_ylabel('Closing equity change (USD)');axes[0].legend(fontsize=8)
 names=['zero_cost','primary','fee_double','slip_double','delay_stress']
 values=[r['accounts'][s]['continuation']['net_pnl_cents']/100 for s in names]
 axes[1].bar(range(5),values,color=['#777777']+['#377eb8']*4)
 axes[1].set_xticks(range(5),['Zero explicit\ncost','Primary','Double\nfees','Double\nslippage','Delayed\nentry'],fontsize=8)
 axes[1].set_ylabel('Continuation net reference cash PnL (USD)')
 for a in axes:a.axhline(0,color='black',linewidth=.7);a.grid(axis='y',alpha=.2)
 fig.suptitle('SPY intraday continuation: reused January-June 2010 vendor bars')
 fig.text(.5,.015,'Exploratory development only. Assumed fills, costs and settlement; pending cash included in equity. No independent OOS or prop payout.',ha='center',fontsize=9)
 fig.tight_layout(rect=(0,.05,1,.95));out=ROOT/'figures/results.png';fig.savefig(out,dpi=160);plt.close(fig);print(out)
if __name__=='__main__':main()

"""Append-only image ledger summaries and delivered-manifest validation."""
from collections import defaultdict
from datetime import datetime
from image_common import ImageError


def summarize(records,since=None,round_id=None,run_id=None):
    if since:
        try:datetime.fromisoformat(since)
        except ValueError:raise ImageError('E_DATE','Use an ISO date for --since.') from None
    selected=[r for r in records if (not since or r['timestamp'][:10]>=since[:10]) and
              (not round_id or r['round_id']==round_id) and (not run_id or r['run_id']==run_id)]
    def aggregate(rows):
        generated=[r for r in rows if r.get('event')=='generation']
        elapsed=sum(r['elapsed_s'] for r in generated)
        return dict(requests=len(generated),successful_requests=sum(r['status']=='ok' for r in generated),
                    failures=sum(r['status']=='error' for r in generated),cache_hits=sum(r['cache_hit'] for r in generated),
                    cache_saved_images=sum(r['n_returned'] for r in generated if r['cache_hit']),
                    subscription_images=sum(r['subscription_images'] for r in generated),
                    returned_images=sum(r['n_returned'] for r in generated if not r['cache_hit']),
                    reserved_images=sum(r.get('reserved_images',0) for r in rows),
                    api_estimate_usd=round(sum(r['cost_estimate_usd'] for r in generated),8),
                    average_elapsed_s=elapsed/max(1,len(generated)),
                    note='Reserved images include failed/ambiguous dispatches and retries; this conservative total enforces the cap.')
    groups={}
    for field in ('day','round_id','run_id'):
        grouped=defaultdict(list)
        for r in selected:grouped[r['timestamp'][:10] if field=='day' else r[field]].append(r)
        groups[field]={k:aggregate(v) for k,v in grouped.items()}
    total=aggregate(selected)
    return dict(totals=total,groups=groups,summary=f"{total['subscription_images']} subscription AI images; cache saved {total['cache_saved_images']} images; API estimate ${total['api_estimate_usd']:.2f}.")

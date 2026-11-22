from collections import Counter
from fractions import Fraction

from app.codes import blocking

from .budget import propagate


def pack(supply, trace, budgets):
    allocations, returns, packages, pending_packages, jobs={}, {}, {}, {}, {}
    drawn=Counter()
    for work,row in trace['jobs'].items():
        plan=budgets[work]
        reasons=blocking(row['codes'])
        allowed=not reasons
        intake=Fraction(row['admitted_g']) if allowed else Fraction(row['input_g'])
        if allowed:
            for feed in row['lots']:
                if feed['source_kind']=='return':
                    drawn[feed['source']]+=Fraction(feed['g'])
        remaining=intake-Fraction(plan['issued_g']) if allowed else Fraction()
        totals=Counter()
        for output in plan['outputs']:
            amount=Fraction(output['g'])
            record={**output,'status':'certified' if allowed else 'pending',
                    'origin_g':propagate(row['composition_g'],amount,intake) if allowed else {},
                    'hold_codes':reasons}
            allocations[record['id']]=record
            if allowed:
                totals[output['kind']]+=amount
                if output['kind']=='pack':
                    packages[output['id']]=record
            elif output['kind']=='pack':
                pending_packages[output['id']]=record
        jobs[work]=dict(pack_g=str(totals['pack']),loss_g=str(totals['loss']),return_g=str(totals['return']),
                        hold_g=str(remaining),hold_origin_g=propagate(row['composition_g'],remaining,intake) if allowed else {},
                        pending_g='0' if allowed else row['input_g'],
                        hold_codes=reasons,admitted_g=row['admitted_g'],budget=plan)
    for key, pool in supply['return_lots'].items():
        entry=allocations[key]
        used=drawn[key]
        allowed=entry['status']=='certified'
        left=Fraction(entry['g'])-used if allowed else None
        source_pool=supply['pools']['return'][key]
        returns[key]={**entry,'drawn_g':str(used),'available_g':str(left) if left is not None else None,
                      'request_g':source_pool['requested_g'],
                      'received_g':source_pool.get('received_g',source_pool['requested_g']),
                      'remaining_origin_g':propagate(entry['origin_g'],left,Fraction(entry['g'])) if left else {}}
    return dict(jobs=jobs,outputs=allocations,returns=returns,packages=packages,
                pending_packages=pending_packages)

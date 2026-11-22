from collections import defaultdict
from fractions import Fraction
from graphlib import TopologicalSorter

from app.codes import is_blocked

from .cycles import find_cycles
from .mix import blend


def trace(supply, limits):
    jobs, coupons=supply['jobs'],supply['return_lots']
    grouped=defaultdict(list)
    edges={work:set() for work in jobs}
    for row in supply['inputs']:
        work=row['work']
        grouped[work].append(row)
        if row['source_kind']=='return':
            edges[work].add(coupons[row['source']]['work'])
    loops=find_cycles(edges)
    loop_paths={member:loop['path'] for loop in loops for member in loop['members']}
    result={}
    for work in TopologicalSorter({node:() if node in loop_paths else parents for node,parents in edges.items()}).static_order():
        job=jobs[work]
        admitted=sum((Fraction(row['g']) for row in grouped[work]),Fraction())
        receipt_rows=[row for row in grouped[work] if row.get('receipt_id')]
        warnings=[]
        if work in loop_paths:
            warnings.append('CYCLE')
        if work in supply['by_input_issue']:
            warnings.append('INPUT_DISPUTE')
        if limits[work]['code']:
            warnings.append(limits[work]['code'])
        if admitted!=Fraction(job['g']):
            explained=bool(receipt_rows)
            warnings.append('RECEIPT_VARIANCE' if explained else 'INTAKE_MISMATCH')
        unresolved=sorted(parent for parent in edges[work] if parent in result and is_blocked(result[parent]['codes']))
        if unresolved and work not in loop_paths:
            warnings.append('UPSTREAM_PENDING')
        mix, feed_rows=({},[]) if is_blocked(warnings) else blend(grouped[work],coupons,result)
        result[work]=dict(work=work,input_g=job['g'],admitted_g=str(admitted),codes=warnings,
                          lots=feed_rows,composition_g=mix,job_line=job['line'],cycle_path=loop_paths.get(work,[]),
                          upstream_pending=unresolved,reported_inputs=grouped[work],
                          input_issues=supply['by_input_issue'].get(work,[]))
    return dict(jobs=result,cycles=loops,certified=sum(not is_blocked(row['codes']) for row in result.values()))

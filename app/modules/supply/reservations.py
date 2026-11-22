from collections import defaultdict
from fractions import Fraction


def reserve(demands, origins, coupons, receipts):
    grouped=defaultdict(list)
    for row in demands:
        grouped[row['source_kind'],row['source']].append(row)
    request_index={row['id']:row for row in demands}
    accepted, rejected, pools=[],[],{'origin':{},'return':{}}
    # 同一申请秤单只认一张回执：多挂即整组不可裁决
    notes_by_ticket=defaultdict(list)
    for note in receipts.values():
        notes_by_ticket[note['ticket']].append(note)
    ambiguous={ticket for ticket,notes in notes_by_ticket.items() if len(notes)>1}
    for kind,bins in (('origin',origins),('return',coupons)):
        for name, source in bins.items():
            requests=grouped[kind,name]
            requested=sum((Fraction(row['g']) for row in requests),Fraction())
            capacity=Fraction(source['g'])
            status='OVERDRAW_ORIGIN' if kind=='origin' else 'OVERDRAW_RETURN'
            fits=requested<=capacity
            if kind=='origin' or fits:
                pools[kind][name]=dict(capacity_g=str(capacity),requested_g=str(requested),
                                       reserved_g=str(requested if fits else 0),blocked=not fits,
                                       source_line=source['line'],tickets=[row['id'] for row in requests])
                if fits:
                    accepted.extend(requests)
                else:
                    rejected.extend({**row,'code':status,'capacity_g':str(capacity),'requested_g':str(requested)}
                                    for row in requests)
                continue
            # 超领返料：不按提交顺序先到先认，整组凭实领回执裁决
            missing, bad_source, matched, doubles=[],[],{},[]
            for row in requests:
                notes=notes_by_ticket.get(row['id'],[])
                if not notes:
                    missing.append(row)
                elif row['id'] in ambiguous:
                    doubles.append(row)
                elif notes[0]['source']!=name:
                    bad_source.append((row,notes[0]))
                else:
                    matched[row['id']]=notes[0]
            received=sum((Fraction(note['g']) for note in matched.values()),Fraction())
            if doubles:
                hold_code='RECEIPT_AMBIGUOUS'
            elif bad_source and not missing:
                hold_code='RECEIPT_SOURCE'
            else:
                hold_code='RECEIPT_MISSING'
            resolved=not (missing or bad_source or doubles) and 0<received<=capacity
            pool=dict(capacity_g=str(capacity),requested_g=str(requested),
                      received_g=str(received),reserved_g=str(received if resolved else 0),
                      blocked=not resolved,source_line=source['line'],
                      tickets=[row['id'] for row in requests],
                      receipts=sorted(matched),missing=[row['id'] for row in missing],
                      hold_code='' if resolved else hold_code)
            pools[kind][name]=pool
            if not resolved:
                for row in requests:
                    rejected.append({**row,'code':status,'capacity_g':str(capacity),
                                     'requested_g':str(requested),'received_g':str(received),
                                     'hold_code':pool['hold_code']})
                for row,note in bad_source:
                    rejected.append({**note,'code':'RECEIPT_SOURCE','work':row['work']})
                for row in doubles:
                    for note in notes_by_ticket[row['id']]:
                        rejected.append({**note,'code':'RECEIPT_AMBIGUOUS','work':row['work']})
                continue
            for row in requests:
                note=matched[row['id']]
                actual=Fraction(note['g'])
                admitted={**row,'requested_g':row['g'],'receipt_id':note['id'],'receipt_line':note['line'],
                          'received_g':str(actual),'g':str(actual)}
                if actual!=Fraction(row['g']):
                    admitted['variance']='RECEIPT_VARIANCE'
                accepted.append(admitted)
    overdraw_returns={name for name,pool in pools['return'].items() if pool['blocked']}
    for note in receipts.values():
        request=request_index.get(note['ticket'])
        if request is None or request['source_kind']!='return' or request['source'] not in overdraw_returns:
            rejected.append({**note,'code':'RECEIPT_EXTRA'})
    return accepted,rejected,pools

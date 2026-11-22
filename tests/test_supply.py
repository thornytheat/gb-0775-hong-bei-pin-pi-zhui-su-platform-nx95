from app.pipeline import compute


def test_split_reservation(dirty):
    pool=dirty['supply']['pools']['return']['RT-A']
    assert pool==dict(capacity_g='300',requested_g='300',reserved_g='300',blocked=False,source_line=4,
                      tickets=['IN-03','IN-05'])


def test_global_overdraw_no_first_claim(files):  # TRAP-19：缺回执时整组待证，不按先到先认
    files['receipts']='receipt,ticket,source,received,unit\n'
    header,*body=files['inputs'].splitlines()
    files['inputs']='\n'.join([header,*reversed(body)])
    other=compute(files,'supply')['supply']
    denied=[row['id'] for row in other['rejected'] if row['code']=='OVERDRAW_RETURN']
    assert denied==['IN-09','IN-10'] and other['pools']['return']['RT-D']['reserved_g']=='0'
    assert other['pools']['return']['RT-D']['hold_code']=='RECEIPT_MISSING'


def test_overdraw_resolved_by_receipts(dirty):
    pool=dirty['supply']['pools']['return']['RT-D']
    assert pool==dict(capacity_g='100',requested_g='120',received_g='95',reserved_g='95',blocked=False,
                      source_line=12,tickets=['IN-09','IN-10'],receipts=['IN-09','IN-10'],
                      missing=[],hold_code='')
    rows={row['id']:row for row in dirty['supply']['inputs']}
    assert (rows['IN-09']['g'],rows['IN-09']['requested_g'],rows['IN-09']['receipt_id'])==('50','60','RC-01')
    assert (rows['IN-10']['g'],rows['IN-10']['receipt_id'])==('45','RC-02')
    assert not any(row['code']=='OVERDRAW_RETURN' for row in dirty['supply']['rejected'])


def test_late_partial_receipt_still_holds(files):
    files['receipts']='receipt,ticket,source,received,unit\nRC-01,IN-09,RT-D,50,g\n'
    result=compute(files,'supply')['supply']
    pool=result['pools']['return']['RT-D']
    assert pool['blocked'] and pool['reserved_g']=='0' and pool['missing']==['IN-10']
    assert {row['id'] for row in result['rejected'] if row['code']=='OVERDRAW_RETURN'}=={'IN-09','IN-10'}


def test_receipt_total_over_capacity_holds(files):
    files['receipts']=('receipt,ticket,source,received,unit\n'
                       'RC-01,IN-09,RT-D,60,g\nRC-02,IN-10,RT-D,50,g\n')
    result=compute(files,'supply')['supply']
    pool=result['pools']['return']['RT-D']
    assert pool['blocked'] and pool['received_g']=='110' and pool['reserved_g']=='0'


def test_receipts_matching_requests_need_capacity_fit(files):
    # 实领各 50 g，合计 100 g 恰等于卷重：放行，实领少于申请只留信息痕
    files['receipts']=('receipt,ticket,source,received,unit\n'
                       'RC-01,IN-09,RT-D,50,g\nRC-02,IN-10,RT-D,50,g\n')
    result=compute(files)
    pool=result['supply']['pools']['return']['RT-D']
    assert (pool['received_g'],pool['reserved_g'],pool['blocked'])==('100','100',False)
    for work in ('BA-05','BA-06'):
        assert result['lineage']['jobs'][work]['codes']==['RECEIPT_VARIANCE']
    assert result['balance']['balanced']


def test_receipt_over_capacity_even_when_lower_than_request(files):
    # 卷重调到 90 g；实领合计仍 90 看似不超，但申请 60+60=120 超领，
    # 若回执各 50/40 合计 90 恰好卷重则放行；各 50/50 合计 100 超卷重则继续待证
    files['outputs']=files['outputs'].replace('RT-D,BA-04,return,100,0,g','RT-D,BA-04,return,90,0,g')
    files['receipts']=('receipt,ticket,source,received,unit\n'
                       'RC-01,IN-09,RT-D,50,g\nRC-02,IN-10,RT-D,50,g\n')
    blocked=compute(files)['supply']['pools']['return']['RT-D']
    assert blocked['blocked'] and blocked['received_g']=='100' and blocked['reserved_g']=='0'
    files['receipts']=('receipt,ticket,source,received,unit\n'
                       'RC-01,IN-09,RT-D,50,g\nRC-02,IN-10,RT-D,40,g\n')
    settled=compute(files)['supply']['pools']['return']['RT-D']
    assert not settled['blocked'] and settled['reserved_g']=='90'


def test_receipt_source_mismatch_holds(files):
    files['receipts']=('receipt,ticket,source,received,unit\n'
                       'RC-01,IN-09,RT-A,50,g\nRC-02,IN-10,RT-D,45,g\n')
    result=compute(files,'supply')['supply']
    pool=result['pools']['return']['RT-D']
    assert pool['blocked'] and pool['hold_code']=='RECEIPT_SOURCE'
    assert any(row['code']=='RECEIPT_SOURCE' for row in result['rejected'])


def test_receipt_without_ticket_is_extra(files):
    files['receipts']='receipt,ticket,source,received,unit\nRC-99,IN-99,RT-D,10,g\n'
    result=compute(files,'supply')['supply']
    assert result['reasons'].get('RECEIPT_EXTRA')==1


def test_duplicate_receipt_for_one_ticket_holds(files):
    files['receipts']=('receipt,ticket,source,received,unit\n'
                       'RC-01,IN-09,RT-D,50,g\nRC-03,IN-09,RT-D,40,g\n'
                       'RC-02,IN-10,RT-D,45,g\n')
    result=compute(files,'supply')['supply']
    pool=result['pools']['return']['RT-D']
    assert pool['blocked'] and pool['hold_code']=='RECEIPT_AMBIGUOUS'
    assert result['reasons'].get('RECEIPT_AMBIGUOUS')==2


def test_receipt_on_fitting_group_is_extra(files):
    # RT-A 申请恰好 300 g 不超领，挂回执属于多余证据
    files['receipts']='receipt,ticket,source,received,unit\nRC-09,IN-03,RT-A,180,g\n'
    result=compute(files,'supply')['supply']
    assert result['reasons'].get('RECEIPT_EXTRA')==1
    assert result['pools']['return']['RT-A']['reserved_g']=='300'


def test_unregistered_return(dirty):
    row=next(row for row in dirty['supply']['rejected'] if row['code']=='NO_RETURN')
    assert (row['id'],row['source'],row['g'])==('IN-12','RT-404','70')


def test_raw_origin_overdraw(files):
    files['origins']=files['origins'].replace('1000,g','750,g')
    result=compute(files,'supply')['supply']
    assert result['pools']['origin']['ET-01']['reserved_g']=='0'
    assert result['reasons']['OVERDRAW_ORIGIN']==2


def test_unregistered_work(files):
    files['inputs']+='IN-20,BA-77,origin,ET-01,10,g\n'
    result=compute(files,'supply')['supply']
    assert result['reasons']['NO_WORK']==1 and result['pools']['origin']['ET-01']['requested_g']=='800'


def test_master_conflict(client,files):
    files['jobs']+='BA-01,晨配基础批,1.1,kg\n'
    response=client.post('/api/lots/supply',json={'files':files})
    assert (response.status_code,response.json['code'])==(422,'BAD_REGISTER')

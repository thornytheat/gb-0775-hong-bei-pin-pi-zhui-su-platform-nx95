def test_seven_pages(client):
    sections={'balance':'重量勾稽卷联','weighins':'秤单收讫联','supply':'来源额度联','lineage':'拼批血缘卷联',
              'packing':'返料占用与余额','runs':'在柜卷联','proof':'包装批次追溯联'}
    for view,text in sections.items():
        response=client.get('/ledger/'+view)
        assert response.status_code==200 and text in response.get_data(as_text=True)


def test_cycle_evidence_on_web(client):
    page=client.get('/ledger/lineage?work=BA-09').get_data(as_text=True)
    assert 'BA-09 → BA-10 → BA-09' in page


def test_rejected_file_has_no_archive(client,files):
    files['jobs']='work,label,measured,unit\n'
    response=client.post('/api/runs',json={'files':files})
    assert (response.status_code,response.json['code'])==(422,'HEADER_ONLY')
    assert client.get('/api/runs').json['runs']==[]


def test_proof_page_splits_signable_and_pending(client):
    page=client.get('/ledger/proof?work=BA-05').get_data(as_text=True)
    assert '可签包装' in page and '待证包装' in page
    assert 'PK-E' in page and 'PK-G' in page
    assert page.index('可签包装') < page.index('PK-E') < page.index('待证包装')


def test_packing_page_shows_received_grams(client):
    page=client.get('/ledger/packing?work=BA-05').get_data(as_text=True)
    assert '实领 g' in page and 'RC-01' not in page  # 返料表只展实领克重
    assert '已核可签' in page


def test_receipts_optional_in_submission(client,files):
    del files['receipts']
    response=client.post('/api/lots/supply',json={'files':files})
    assert response.status_code==200 and response.json['pools']['return']['RT-D']['blocked']

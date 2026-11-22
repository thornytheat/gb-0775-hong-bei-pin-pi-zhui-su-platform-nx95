from fractions import Fraction

import pytest

from app.errors import RoastError
from app.modules.proof.service import verify_and_export
from app.modules.runs.cabinet import Cabinet
from app.modules.runs.fingerprint import checksum, encode
from app.modules.runs.service import seal_run


@pytest.fixture
def document(tmp_path,files):
    store=Cabinet(tmp_path/'proof')
    return store.read(seal_run(store,files)['id'])


def test_seal(document):
    result=verify_and_export(document)
    seal=result.pop('seal')
    assert result.pop('verified') and seal==checksum(encode(result))


def test_shares(document):
    packages=verify_and_export(document)['packages']
    report=packages['PK-C']
    assert report['origins']['ET-01']['share']=='327/1250' and report['packing_line']==8
    assert sum(Fraction(part['share']) for part in report['origins'].values())==1


def test_corrupt_original(document):
    document['files']['inputs']+='\n'
    with pytest.raises(RoastError) as error:
        verify_and_export(document)
    assert error.value.code=='BAD_SEAL'


def test_unbalanced_export_rejected(document):
    document['reports']['balance']['balanced']=False
    document['manifest']['result_sha256']=checksum(encode(document['reports']))
    with pytest.raises(RoastError) as error:
        verify_and_export(document)
    assert error.value.code=='UNBALANCED'


def test_packaging_identity_in_attachment(client):
    key=client.post('/api/runs',json={'sample':'dirty'}).json['id']
    response=client.get(f'/api/export/{key}')
    assert response.headers['Content-Disposition'].startswith('attachment;')
    assert set(response.json['packages'])=={'PK-A','PK-B','PK-C','PK-D','PK-E','PK-F'}
    assert set(response.json['pending_packages'])=={'PK-G'}
    assert response.json['pending_packages']['PK-G']['hold_codes']==['NEGATIVE_REMAINDER']


def test_packaging_pending_never_signed(document):
    result=verify_and_export(document)
    assert 'PK-G' not in result['packages'] and result['reports']['balance']['jobs']['BA-07']['pending_g']=='100'
    # 回执裁决放行的包装带完整产地克重，可随当天签发
    pkg=result['packages']['PK-E']
    assert pkg['net_g']=='40' and pkg['origins']=={'ET-01':dict(grams='40',share='1',
        label=result['reports']['supply']['origins']['ET-01']['label'],
        line=result['reports']['supply']['origins']['ET-01']['line'])}

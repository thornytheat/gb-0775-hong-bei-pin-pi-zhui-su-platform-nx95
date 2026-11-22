from fractions import Fraction

from app.modules.balance.service import verify_mass


def test_per_job(dirty):
    row=dirty['balance']['jobs']['BA-01']
    assert (row['input_g'],row['pack_g'],row['loss_g'],row['remainder_g'],row['pending_g'],row['delta_g'])==('1000','600','50','350','0','0')


def test_disputed_jobs_keep_input(dirty):
    assert dirty['balance']['jobs']['BA-07']['pending_g']=='100'
    assert dirty['balance']['jobs']['BA-07']['delta_g']=='0'
    assert dirty['balance']['warehouse']['pending_g']=='270'


def test_warehouse_equation(dirty):
    row=dirty['balance']['warehouse']
    assert int(row['origin_used_g'])==1670==sum(int(row[key]) for key in ('pack_g','loss_g','hold_g','return_stock_g'))
    assert row['delta_g']=='0'


def test_origin_follows_every_exit(dirty):
    row=dirty['balance']['warehouse']['origins']['ET-01']
    assert row=={'used_g':'800','distributed_g':'800','delta_g':'0'}


def test_number_of_csv_lines_kept(dirty):
    assert dirty['balance']['line_delta']==dict.fromkeys(('jobs','origins','inputs','outputs','receipts'),0)


def test_detect_missing_origin_mass(dirty):
    pack=dirty['packing']
    pack['packages']['PK-C']['origin_g']['ET-01']='0'
    result=verify_mass(dirty['weighins'],dirty['lineage'],pack)
    assert result['package_delta_g']['PK-C']=='3597/50' and not result['balanced']


def test_receipt_batches_conserve_on_admitted_mass(dirty):
    # 实领 95 g = 灌装 80 g + 余量 15 g，卷内剩余 5 g
    rows=dirty['balance']['jobs']
    assert (rows['BA-05']['admitted_g'],rows['BA-05']['pack_g'],rows['BA-05']['remainder_g'])==('50','40','10')
    assert (rows['BA-06']['admitted_g'],rows['BA-06']['pack_g'],rows['BA-06']['remainder_g'])==('45','40','5')
    assert dirty['balance']['warehouse']['return_stock_g']=='5'
    assert dirty['balance']['warehouse']['pack_g']=='1485'
    assert dirty['balance']['warehouse']['hold_g']=='105'
    assert dirty['balance']['warehouse']['origin_used_g']=='1670'
    # 包装产地克重逐克对得上
    for key in ('PK-E','PK-F'):
        pkg=dirty['packing']['packages'][key]
        assert sum(Fraction(g) for g in pkg['origin_g'].values())==Fraction(pkg['g'])

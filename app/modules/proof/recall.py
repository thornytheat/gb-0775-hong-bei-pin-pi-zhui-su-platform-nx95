from fractions import Fraction


def _describe(labels, report, row, reasons=()):
    net=Fraction(row['g'])
    shares={origin:dict(grams=mass,share=str(Fraction(mass)/net),label=labels[origin]['label'],
                        line=labels[origin]['line']) for origin,mass in row['origin_g'].items()} if net else {}
    return dict(work=row['work'],net_g=row['g'],packing_line=row['line'],origins=shares,
                inputs=report['lineage']['jobs'][row['work']]['lots'],hold_codes=list(reasons))


def recall(report):
    labels=report['supply']['origins']
    packages={key:_describe(labels,report,row) for key,row in report['packing']['packages'].items()}
    pending={key:_describe(labels,report,row,row.get('hold_codes',()))
             for key,row in report['packing']['pending_packages'].items()}
    return packages,pending

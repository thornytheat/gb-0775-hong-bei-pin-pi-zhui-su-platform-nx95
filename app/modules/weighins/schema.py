SCHEMA = {
    'origins':('origin','label','available','unit'),
    'jobs':('work','label','measured','unit'),
    'inputs':('ticket','work','source_kind','source','quantity','unit'),
    'outputs':('ticket','work','kind','gross','tare','unit'),
    'receipts':('receipt','ticket','source','received','unit'),
}
KEY_FIELD = {'origins':'origin','jobs':'work','inputs':'ticket','outputs':'ticket','receipts':'receipt'}
MISSING = frozenset({'','-','N/A','NULL','未知'})

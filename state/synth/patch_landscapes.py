import csv,json,re
from collections import defaultdict
cnt=defaultdict(lambda: defaultdict(int))
designs=set()
for r in csv.DictReader(open('data/trends/monthly_counts.csv')):
    cnt[(r['domain'],r['design'])][r['month'][:4]]+=int(r['count']); designs.add(r['design'])
order=[d for d in ['all','rct','ma','guideline','observational'] if d in designs]
print(designs)
for i in range(1,10):
    d=f'D{i}'; p=f'outputs/landscape/{d}.md'; t=open(p).read()
    yrs=[str(y) for y in range(2016,2027)]
    tab='| Year | '+' | '.join(order)+' |\n|---|'+'---|'*len(order)+'\n'
    for y in yrs:
        tab+=f'| {y}{" (to October)" if y=="2026" else ""} | '+' | '.join(str(cnt[(d,k)][y]) for k in order)+' |\n'
    sec=f'## Evidence trend\n\nPubMed counts by entrez year for the domain query, from data/trends/monthly_counts.csv (counted 24 October 2026). Categories overlap, so columns do not sum.\n\n{tab}\n'
    t=re.sub(r'\nPrimary outcomes of the trials above.*?(?=\n## )','',t,flags=re.S)
    t=re.sub(r'## Evidence trend\n.*?(?=\n## )',sec,t,flags=re.S)
    trs={}
    for l in open(f'state/synth/{d}_trials.jsonl'):
        x=json.loads(l); trs[x['nct']]=x
    ids=[n for n in dict.fromkeys(re.findall(r'NCT\d{8}',t)) if n in trs]
    rows=''
    for n in ids:
        po=trs[n].get('primary_outcomes') or []
        m='; '.join(o.get('measure','') for o in po[:2]) or 'not stated'
        rows+=f'- {n}: primary outcome as registered: {m[:300]}\n'
    if ids:
        t=t.replace('\n## Evidence trend',f'\nPrimary outcomes of the trials above, as registered:\n\n{rows}\n## Evidence trend',1)
    t=t.replace('primary outcomes are not given in the file.','').replace('primary outcomes are not given in the file','')
    open(p,'w').write(t)

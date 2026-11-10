"""Idea 39 (IDEAS row 39), offline: is a free check's pass worth less after a feedback-guided repair than a fresh first-attempt pass on the SAME problem?
Usage: python poc/repair_precision.py. No model call. Per problem: precision (share right) of passes reached after >=1 repair minus precision of first-attempt
passes of the same problem in other seeds; bootstrap over problems (95%). Domains: GridPuzzle / Mitra-Baral (gtr, gtrl, gtrt, 8B / 32B), ZebraLogic
translation (zl_*_{tr,trf,trt}), BIRD SQL (N -> R repair from the execution check), word-problem optimization programs (x3 opt_ -> repair_)."""
import json,random,os,glob,re,collections
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
def boot(per,n=10000,seed=0):
    ids=sorted(per); rng=random.Random(seed); f=lambda v: sum(v)/len(v)
    pt=f([per[i] for i in ids]); xs=sorted(f([per[rng.choice(ids)] for _ in ids]) for _ in range(n))
    return pt,xs[int(.025*n)],xs[int(.975*n)-1]
def rows(f): return [json.loads(l) for l in open(f) if l.strip()]
def report(dom, first, rep):
    """first/rep: {(unit, pid): [bool,...]} ; paired on keys in both"""
    ids=[k for k in rep if k in first]
    per={k: sum(rep[k])/len(rep[k]) - sum(first[k])/len(first[k]) for k in ids}
    nf=sum(len(v) for v in first.values()); cf=sum(sum(v) for v in first.values())
    nr=sum(len(v) for v in rep.values()); cr=sum(sum(v) for v in rep.values())
    nrp=sum(len(rep[k]) for k in ids)
    b=boot(per) if per else (float('nan'),)*3
    print(f"{dom}: unpaired first {cf}/{nf}={cf/max(nf,1):.3f} repaired {cr}/{nr}={cr/max(nr,1):.3f} | paired {b[0]:+.3f} [{b[1]:+.3f}, {b[2]:+.3f}] over {len(ids)} problems ({nrp} repaired passes)")
    return per
ALL={}
# ZebraLogic translation: hist rounds, check count==1
for tag in ['q8b','q8bh','q8bf','q4bh','oss20','oss20f']:
  for arm in ['tr','trf','trt']:
    fs=sorted(glob.glob(f'{R}/zl_{tag}_{arm}_s*.jsonl'))
    if not fs: continue
    first,rep=collections.defaultdict(list),collections.defaultdict(list)
    for f in fs:
      for r in rows(f):
        h=r.get('hist')
        if not h: continue
        k=(tag+arm,r['id'])
        if h[0]['count']==1: first[k].append(h[0]['exact'])
        else:
          for x in h[1:]:
            if x['count']==1: rep[k].append(x['exact']); break
    ALL.setdefault('zebralogic',{}).update(report(f'zl {tag} {arm} ({len(fs)} seeds)',first,rep))
# SQL: grades json, N first, R repair; check chk=='pass'
for tag in ['q8b','q14a','q35','n3n']:
    fs=sorted(glob.glob(f'{R}/sql/grades_{tag}_s*.json'))
    first,rep=collections.defaultdict(list),collections.defaultdict(list)
    for f in fs:
        G=json.load(open(f))
        for q,g in G.items():
            if not isinstance(g,dict): continue
            k=('sql'+tag,q)
            n=g.get('N'); r=g.get('R')
            if n and n.get('chk')=='pass': first[k].append(bool(n['ok']))
            elif n and r and r.get('chk')=='pass': rep[k].append(bool(r['ok']))
    ALL.setdefault('sql',{}).update(report(f'sql {tag} ({len(fs)} seeds)',first,rep))
# word-problem optimization programs: opt_ first, repair_ (HO7 arms: visible failures only)
ok_=lambda r: r.get("status")=="ok" and r.get("pred") not in (None,"NBS")
for m in ['q8b','q14a','q35','n3n','oss20']:
  for arm in ['formx','free','mips']:
    first,rep=collections.defaultdict(list),collections.defaultdict(list); nseed=0
    for st in ['bwor','logior','optibench','optmath']:
        for f in glob.glob(f'{R}/x3/opt_{m}_{st}_{arm}_s*.jsonl'):
            for r in rows(f):
                if ok_(r): first[(m+arm+st,r['id'])].append(bool(r['correct']))
        for f in glob.glob(f'{R}/x3/repair_{m}_{st}_{arm}_s*.jsonl'):
            nseed+=1
            for r in rows(f):
                if ok_(r): rep[(m+arm+st,r['id'])].append(bool(r['correct']))
    if rep: ALL.setdefault('programs',{}).update(report(f'opt {m} {arm} ({nseed} repair files)',first,rep))
print('=== pooled per domain (problem-level paired differences, bootstrap over problems)')
for d,per in ALL.items():
    if per:
        b=boot(per); print(f"{d}: {b[0]:+.3f} [{b[1]:+.3f}, {b[2]:+.3f}] over {len(per)} problems")
# GridPuzzle / Mitra-Baral translation
for s in ['gp','lgp']:
  for tag,arm in [('q8b','gtr'),('q8bl','gtrl'),('q8b','gtrt'),('q32a','gtr'),('q32a','gtrt')]:
    first,rep=collections.defaultdict(list),collections.defaultdict(list)
    for f in [x for x in sorted(glob.glob(f'{R}/{s}_{tag}_{arm}_s*.jsonl')) if 'crashed' not in x]:
      for r in rows(f):
        h=r['hist']; k=(s+tag+arm,r['id'])
        if h[0]['count']==1: first[k].append(h[0]['exact'])
        else:
          for x in h[1:]:
            if x['count']==1: rep[k].append(x['exact']); break
    report(f'{s} {tag} {arm}',first,rep)

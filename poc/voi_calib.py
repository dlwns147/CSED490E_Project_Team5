"""PREREG_VOI diagnostic (2026-11-22): along the policy's own path on the fit half, each source's predicted one-step gain in
E[100 * P(argmax right)] vs the realized change under the model (label-free martingale check) and with labels. usage: python3 poc/voi_calib.py <set>"""
import sys,zlib,math,collections
which=sys.argv[1]; sys.argv=['voi.py',which]; sys.path.insert(0,'poc')
import voi
P,srcs={"math":voi.load_math,"oeis":voi.load_oeis,"words":voi.load_words}.get(which,lambda: voi.load_euler(which))()
ids=sorted(i for i in P if all(len(P[i].get(s,[])) for s in srcs))
fit=[i for i in ids if zlib.crc32(i.encode())%2==1]
probs=[[(s,k,ck,t) for s in srcs for k,t,ok,ck in P[i][s]] for i in fit]
best=None
for D in range(1,7):
    m=voi.Model(srcs,D); ll=m.fit(probs); bic=-2*ll+(len(srcs)*D*4+D)*math.log(len(probs))
    if best is None or bic<best[0]: best=(bic,m)
m=best[1]
# along the policy's own path on fit problems: predicted one-step gain in E[100*P(argmax)] vs realized change, label-free; also realized with labels
pred=collections.defaultdict(float); real=collections.defaultdict(float); lab=collections.defaultdict(float); n=collections.Counter()
for i in fit:
    obs,used=[],collections.defaultdict(int); avail={s:len(P[i][s]) for s in srcs}
    while True:
        v,s=voi.lookahead(m,obs,avail,None,2) if False else voi.lookahead(m,obs,avail,{x:0 for x in srcs},2)
        v0,y0,post=voi.stop_value(m,obs)
        # evaluate every source's one-step predicted gain vs realized for the actually stored next sample
        for s2 in srcs:
            if avail[s2]<=0: continue
            ev=sum(pr*voi.stop_value(m,obs+[(s2,(f"__new{len(obs)}" if k=="__NEW__" else k),None,None)])[0] for pr,k in voi.outcomes(m,obs,s2,post))
            k,t,ok,ck=P[i][s2][used[s2]]
            v1,y1,_=voi.stop_value(m,obs+[(s2,k,ck,t)])
            pred[s2]+=ev-v0; real[s2]+=v1-v0; lab[s2]+=100*((y1=="GOLD")-(y0=="GOLD")); n[s2]+=1
        # follow the policy (with real costs) to generate states
        v,s=voi.lookahead(m,obs,avail,{x:sum(t for j in fit for _,t,_,_ in P[j][x])/sum(len(P[j][x]) for j in fit) for x in srcs},2)
        if s is None: break
        k,t,ok,ck=P[i][s][used[s]]; used[s]+=1; avail[s]-=1; obs.append((s,k,ck,t))
print(which, "per source: predicted gain / realized (model) / realized (labels), mean over policy states")
for s in srcs:
    if n[s]: print(f"  {s:14s} n={n[s]:4d}  {pred[s]/n[s]:6.2f}  {real[s]/n[s]:6.2f}  {lab[s]/n[s]:6.2f}")

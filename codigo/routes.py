import pickle, sqlite3, json, math, sys
import networkx as nx
from shapely.geometry import LineString
from scipy.spatial import cKDTree
GP=sys.argv[1]; D=sys.argv[2]
G,edges,nxy=pickle.load(open(D+'/graph.pkl','rb'))
c=sqlite3.connect(f'file:{GP}?mode=ro',uri=True)
st={r[0]:dict(codigo=r[0],uf=r[1],municipio=r[2],bairro=r[3],logradouro=r[4],numero=r[5],hierarquia=r[6],caracteristicas=r[7],lon=r[8],lat=r[9]) for r in c.execute('select codigo,uf,municipio,bairro,logradouro,numero,hierarquia,caracteristicas,lon,lat from lojas_autoglass_poc')}
# only nodes touching FRC<=4 roads for snapping
good=set()
for u,v,dd in G.edges(data=True):
    if edges[dd['oid']][2]<=4: good.add(u); good.add(v)
ids=list(good); tree=cKDTree([nxy[n] for n in ids])
def snap(s):
    d,i=tree.query((s['lon'],s['lat'])); return ids[i], d*111
TRIPS=[('CL','PG01'),('CL','PG05'),('CL','PG04'),('CL','PG06'),('CL','MG38'),('CL','MG05'),
       ('MG38','MG53'),('MG38','MG74'),('MG38','MG41'),('MG38','MG84'),('MG38','MG02'),
       ('MG05','MG18'),('MG05','MG14'),('MG05','MG42'),('PG07','PG02'),('MG84','MG74')]
def hav(a,b):
    R=6371; la1,lo1,la2,lo2=map(math.radians,(a[1],a[0],b[1],b[0]))
    h=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(h))
out=[]
for o,dst in TRIPS:
    a,da=snap(st[o]); b,db=snap(st[dst])
    path=nx.shortest_path(G,a,b,weight='w')
    coords=[]; prof=[]  # per edge: km, truck minutes, road name
    for u,v in zip(path[:-1],path[1:]):
        dd=G[u][v]; cs,me,frc,kph,name,shield=edges[dd['oid']]
        cs=cs if dd['fw'] else cs[::-1]
        if coords and coords[-1]==cs[0]: cs=cs[1:]
        coords+=cs
        tk=min(kph or 40,80)*0.85
        prof.append((me/1000, me/1000/max(tk,8)*60, shield or name or ''))
    # cumulative arrays at vertex level: approximate by distributing edge time along its vertices
    line=LineString(coords).simplify(0.0008)
    sc=list(line.coords)
    km=sum(p[0] for p in prof); mins=sum(p[1] for p in prof)
    # nominal pace per cumulative km (edge breakpoints)
    cum=[[0,0]]; k=t=0
    for p in prof:
        k+=p[0]; t+=p[1]
        if t-cum[-1][1]>3 or p is prof[-1]: cum.append([round(k,2),round(t,2)])
    # main roads used
    from collections import Counter
    rc=Counter()
    for p in prof:
        if p[2].startswith(('BR','ES','MG','RJ','SP')) : rc[p[2]]+=p[0]
    vias=[r for r,_ in rc.most_common(3)]
    out.append(dict(o=o,d=dst,km=round(km,1),min=round(mins),coords=[[round(x,5),round(y,5)] for x,y in sc],pace=cum,vias=vias,snap=[round(da,2),round(db,2)]))
    print(o,dst,round(km),'km',round(mins/60,1),'h',len(sc),'pts',vias,'snap',round(da,2),round(db,2))
json.dump(dict(stores=st,routes=out),open(D+'/routes.json','w'),ensure_ascii=False)

import sqlite3, struct, pickle, time, sys
from shapely import wkb
import networkx as nx
GP=sys.argv[1]; OUT=sys.argv[2]
def geom(b):
    flags=b[3]; env=(flags>>1)&7; off=8+{0:0,1:32,2:48,3:48,4:64}[env]
    return wkb.loads(bytes(b[off:]))
c=sqlite3.connect(f'file:{GP}?mode=ro',uri=True)
t=time.time()
edges={}; G=nx.DiGraph(); nodexy={}
for oid,g,f,tj,ow,mi,me,frc,kph,name,shield in c.execute('select OBJECTID,Shape,F_JNCTID,T_JNCTID,ONEWAY,MINUTES,METERS,FRC,KPH,NAME,SHIELDNUM from vias_principais'):
    if ow=='N' or g is None: continue
    gm=geom(g); 
    coords=[pt for line in gm.geoms for pt in line.coords] if gm.geom_type=='MultiLineString' else list(gm.coords)
    f=int(f); tj=int(tj)
    nodexy.setdefault(f,coords[0]); nodexy.setdefault(tj,coords[-1])
    mins=mi if mi and mi>0 else (me/1000)/max(kph or 30,5)*60
    edges[oid]=(coords,me,frc,kph,name,shield)
    if ow in (' ','FT',None,''): 
        if not G.has_edge(f,tj) or G[f][tj]['w']>mins: G.add_edge(f,tj,w=mins,oid=oid,fw=True)
    if ow in (' ','TF',None,''):
        if not G.has_edge(tj,f) or G[tj][f]['w']>mins: G.add_edge(tj,f,w=mins,oid=oid,fw=False)
print('loaded',len(edges),G.number_of_nodes(),G.number_of_edges(),round(time.time()-t))
comp=max(nx.strongly_connected_components(G),key=len)
print('largest scc',len(comp))
G=G.subgraph(comp).copy()
pickle.dump((G,edges,{n:nodexy[n] for n in G.nodes}),open(OUT,'wb'))

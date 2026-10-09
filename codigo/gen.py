import json, math, sqlite3, struct, sys, random
from shapely import wkb
from shapely.geometry import Point, LineString, Polygon, mapping
from shapely.ops import unary_union
D=sys.argv[1]; GP=sys.argv[2]
R=json.load(open(D+'/routes.json')); st=R['stores']; routes=R['routes']
random.seed(7)
def hav(a,b):
    la1,lo1,la2,lo2=map(math.radians,(a[1],a[0],b[1],b[0]))
    h=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 12742*math.asin(math.sqrt(h))
# cumulative km per simplified coord, rescaled to network km
for r in routes:
    ck=[0]
    for a,b in zip(r['coords'][:-1],r['coords'][1:]): ck.append(ck[-1]+hav(a,b))
    s=r['km']/ck[-1]; r['ck']=[round(x*s,2) for x in ck]
TRUCK=1.15  # caminhão mais lento que o tempo da malha
import bisect
for r in routes:
    p=[]
    for k,t in r['pace']:
        if not p or (t>p[-1][1]+1e-6 and k>p[-1][0]+1e-6): p.append([k,t])
    if p[-1][0]<r['km']: p.append([r['km'],p[-1][1]+0.01])
    r['pace']=p; r['_k']=[x[0] for x in p]; r['_t']=[x[1]*TRUCK for x in p]
def _interp(xs,ys,x):
    i=bisect.bisect_left(xs,x)
    if i<=0: return ys[0]
    if i>=len(xs): return ys[-1]
    x0,x1=xs[i-1],xs[i]; return ys[i-1]+(ys[i]-ys[i-1])*(x-x0)/(x1-x0)
def nominal(r,km): return _interp(r['_k'],r['_t'],km)
def km_at_nominal(r,tn): return _interp(r['_t'],r['_k'],tn)
def pt_at(r,km):
    ck=r['ck'];c=r['coords']
    for i in range(1,len(ck)):
        if km<=ck[i]:
            f=(km-ck[i-1])/(ck[i]-ck[i-1]) if ck[i]>ck[i-1] else 0
            return [c[i-1][0]+(c[i][0]-c[i-1][0])*f, c[i-1][1]+(c[i][1]-c[i-1][1])*f]
    return c[-1]
def H(s): h,m=s.split(':'); return int(h)*60+int(m)
key={(r['o'],r['d']):r for r in routes}
def ellipse(c,rx_km,ry_km,rot,n=48):
    pts=[]
    for i in range(n):
        a=2*math.pi*i/n; x=rx_km*math.cos(a); y=ry_km*math.sin(a)
        xr=x*math.cos(rot)-y*math.sin(rot); yr=x*math.sin(rot)+y*math.cos(rot)
        # leve irregularidade
        k=1+0.12*math.sin(3*a+rot)+0.06*math.cos(5*a)
        pts.append((c[0]+xr*k/(111*math.cos(math.radians(c[1]))), c[1]+yr*k/111))
    return Polygon(pts)
# alertas (simulados) posicionados sobre trechos das rotas
ALERTS=[
 dict(id='A1',tipo='Chuvas intensas',sev='laranja',nivel='Perigo',on=('CL','MG38'),frac=0.47,rx=38,ry=24,rot=0.5,ini='10:00',fim='20:00',fator=0.55,
      desc='Chuva entre 30 e 60 mm/h ou 50 a 100 mm/dia, ventos de 60 a 100 km/h'),
 dict(id='A2',tipo='Tempestade com granizo',sev='vermelho',nivel='Grande perigo',on=('CL','MG05'),frac=0.66,rx=34,ry=22,rot=-0.4,ini='14:00',fim='21:00',fator=0.45,
      desc='Chuva superior a 60 mm/h, ventos acima de 100 km/h e granizo'),
 dict(id='A3',tipo='Ventos costeiros / vendaval',sev='amarelo',nivel='Potencial perigo',on=('MG38','MG53'),frac=0.72,rx=30,ry=20,rot=0.2,ini='16:00',fim='22:00',fator=0.85,
      desc='Ventos de 40 a 60 km/h, baixo risco de queda de árvores'),
 dict(id='A4',tipo='Acumulado de chuva',sev='amarelo',nivel='Potencial perigo',on=('CL','PG04'),frac=0.62,rx=26,ry=18,rot=1.1,ini='12:00',fim='18:00',fator=0.8,
      desc='Chuva entre 20 e 30 mm/h ou até 50 mm/dia'),
 dict(id='A5',tipo='Tempestade',sev='laranja',nivel='Perigo',on=('MG05','MG14'),frac=0.85,rx=16,ry=11,rot=0.0,ini='15:20',fim='20:30',fator=0.6,
      desc='Chuva entre 30 e 60 mm/h, ventos de 60 a 100 km/h, risco de alagamentos'),
]
for a in ALERTS:
    r=key[a['on']]; c=pt_at(r,r['km']*a['frac'])
    a['geom']=ellipse(c,a['rx'],a['ry'],a['rot']); a['t0']=H(a['ini']); a['t1']=H(a['fim'])
def zones_on(r):
    out=[]
    for a in ALERTS:
        inter=[]; inside=False; k0=None
        step=max(0.5,r['km']/600)
        k=0
        while k<=r['km']:
            p=Point(pt_at(r,k)); i=a['geom'].contains(p)
            if i and not inside: k0=k
            if not i and inside: inter.append([round(k0,1),round(k,1)])
            inside=i; k+=step
        if inside: inter.append([round(k0,1),round(r['km'],1)])
        for iv in inter: out.append(dict(alerta=a['id'],km0=iv[0],km1=iv[1]))
    return out
# cenários
TR=[ # o,d, saída prevista, atraso saída, fator trânsito, paradas não previstas [(frac,min,motivo)]
 ('CL','PG01','13:30',5,1.0,[]),
 ('CL','PG05','13:00',0,1.0,[(0.72,75,'Parada não prevista em acostamento da BR-101')]),
 ('CL','PG04','12:30',20,0.9,[]),
 ('CL','PG06','14:40',0,1.0,[]),
 ('CL','MG38','07:00',35,0.95,[]),
 ('CL','MG05','08:00',10,1.0,[]),
 ('MG38','MG53','06:30',0,1.0,[]),
 ('MG38','MG74','09:00',0,1.0,[(0.62,80,'Caminhão parado fora de ponto de apoio')]),
 ('MG38','MG41','15:30',0,1.0,[]),
 ('MG38','MG84','14:30',45,1.0,[]),
 ('MG38','MG02','13:30',0,0.9,[]),
 ('MG05','MG18','14:00',15,0.6,[]),
 ('MG05','MG14','14:20',0,0.95,[]),
 ('MG05','MG42','16:00',0,1.0,[]),
 ('PG07','PG02','14:45',0,1.0,[]),
 ('MG84','MG74','11:00',0,1.0,[]),
]
TRANSP=['TransVix Cargas','Rodo Minas Log','Expresso Serrano','Carioca Transportes','Capixaba Express']
CARGA=['Para-brisas e vidros laterais','Vidros traseiros e borrachas','Faróis e lanternas','Retrovisores e palhetas','Película e insumos de instalação','Para-brisas (lote de reposição)']
def plate():
    L='ABCDEFGHJKLMNPRSTUVWXYZ'
    return f"{random.choice('RQPO')}{random.choice(L)}{random.choice(L)}{random.randint(0,9)}{random.choice(L)}{random.randint(10,99)}"
REST_EVERY=270; REST=30
trips=[]
for i,(o,d,sp,dly,traf,stops) in enumerate(TR,1):
    r=key[(o,d)]; dur_drive=nominal(r,r['km'])
    nrest=int(dur_drive//REST_EVERY) if dur_drive>REST_EVERY+20 else 0
    rest_at=[REST_EVERY*(j+1) for j in range(nrest)]  # minutos de direção nominal
    dep_p=H(sp); arr_p=round(dep_p+dur_drive+nrest*REST+10)  # 10 min de folga contratual
    dep=dep_p+dly
    zs=zones_on(r)
    # simulação: passos de ~1 min
    segs=[]; t=dep; km=0; drv=0  # drv = direção nominal acumulada
    stops_k=sorted([(f*r['km'],m,mot) for f,m,mot in stops])
    ri=0; si=0
    cur=None
    def push(kind,t0,t1,k0,k1,info=None):
        if segs and segs[-1][4]==kind and kind in('m','w') and abs(segs[-1][1]-t0)<1e-6 and len(segs)>0 and (t1-segs[-1][0])<4:
            segs[-1][1]=t1; segs[-1][3]=k1; return
        segs.append([t0,t1,k0,k1,kind]+([info] if info else []))
    while km<r['km']-1e-6:
        # paradas
        if ri<len(rest_at) and drv>=rest_at[ri]:
            push('r',t,t+REST,km,km,'Descanso obrigatório (Lei 13.103)'); t+=REST; ri+=1; continue
        if si<len(stops_k) and km>=stops_k[si][0]:
            push('s',t,t+stops_k[si][1],km,km,stops_k[si][2]); t+=stops_k[si][1]; si+=1; continue
        dt=1.0
        tn0=nominal(r,km); kn=km_at_nominal(r,tn0+dt*traf)
        f=1.0; inzone=None
        for z in zs:
            a=next(x for x in ALERTS if x['id']==z['alerta'])
            if z['km0']<=km<=z['km1'] and a['t0']<=t<=a['t1']: f=min(f,a['fator']); inzone=a['id']
        kn=km_at_nominal(r,tn0+dt*traf*f)
        kn=min(max(kn,km+0.01),r['km'])
        push('w' if inzone else 'm',t,t+dt,km,kn)
        drv+= (nominal(r,kn)-tn0); km=kn; t+=dt
    arr=t
    for s in segs: s[0]=round(s[0],1); s[1]=round(s[1],1); s[2]=round(s[2],2); s[3]=round(s[3],2)
    # thin moving segs to every ~5 min
    thin=[]
    for s in segs:
        if thin and s[4] in('m','w') and thin[-1][4]==s[4] and s[0]-thin[-1][0]<6 and abs(thin[-1][1]-s[0])<0.01:
            thin[-1][1]=s[1]; thin[-1][3]=s[3]
        else: thin.append(s)
    so,sd=st[o],st[d]
    trips.append(dict(id=f'VG-{1040+i}',placa=plate(),transportadora=TRANSP[i%len(TRANSP)],carga=CARGA[i%len(CARGA)],
        volumes=random.randint(18,140),
        origem=dict(cod=o,nome=f"{'Centro Logístico' if o=='CL' else ('CD' if so['caracteristicas']=='CD' else 'Loja')} {so['municipio']}",tipo=so['caracteristicas'],uf=so['uf']),
        destino=dict(cod=d,nome=f"{'CD' if sd['caracteristicas']=='CD' else 'Loja'} {sd['municipio']}",tipo=sd['caracteristicas'],uf=sd['uf'],bairro=sd['bairro']),
        km=r['km'],vias=r['vias'],saida_prevista=dep_p,saida_real=dep,chegada_prevista=arr_p,chegada_real=round(arr,1),
        rest_at=rest_at,rest_min=REST,pace=[[round(k,2),round(t,2)] for k,t in zip(r['_k'],r['_t'])],
        coords=r['coords'],ck=r['ck'],segs=thin,zonas=zs))
    print(flush=True) or print(trips[-1]['id'],o,d,'km',r['km'],'prev',dep_p//60,dep_p%60,'->',arr_p//60,arr_p%60,'real arr',int(arr)//60,int(arr)%60,'delay',round(arr-arr_p),'zones',[z['alerta'] for z in zs])
alerts=[dict(id=a['id'],fator=a['fator'],tipo=a['tipo'],sev=a['sev'],nivel=a['nivel'],ini=a['t0'],fim=a['t1'],desc=a['desc'],
             coords=[[round(x,4),round(y,4)] for x,y in a['geom'].exterior.coords]) for a in ALERTS]
stores=[dict(cod=k,**{x:v[x] for x in('uf','municipio','bairro','logradouro','numero','hierarquia','caracteristicas','lon','lat')}) for k,v in st.items()]
# base viária de contexto
def geom(b):
    flags=b[3]; env=(flags>>1)&7; off=8+{0:0,1:32,2:48,3:48,4:64}[env]
    return wkb.loads(bytes(b[off:]))
c=sqlite3.connect(f'file:{GP}?mode=ro',uri=True)
lines={1:[],2:[]}
for g,frc in c.execute('select Shape,FRC from vias_principais where FRC<=2'):
    gm=geom(g)
    b=gm.bounds
    if b[0]<-50.5 or b[2]>-38.5 or b[1]<-24 or b[3]>-16.5: continue
    for ln in (gm.geoms if gm.geom_type=='MultiLineString' else [gm]): lines[frc].append(ln)
from shapely.ops import linemerge
base={}
for frc,ls in lines.items():
    m=linemerge(ls).simplify(0.006 if frc==1 else 0.01)
    gl=m.geoms if m.geom_type=='MultiLineString' else [m]
    base[frc]=[[[round(x,3),round(y,3)] for x,y in g.coords] for g in gl if g.length>(0.02 if frc==1 else 0.05)]
    print('base frc',frc,len(base[frc]),sum(len(x) for x in base[frc]))
json.dump(dict(trips=trips,alerts=alerts,stores=stores,base=base),open(D+'/sim.json','w'),ensure_ascii=False,separators=(',',':'))
import os; print('size',os.path.getsize(D+'/sim.json')/1e6,'MB')

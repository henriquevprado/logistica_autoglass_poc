import sys, json
from playwright.sync_api import sync_playwright
html, outdir = sys.argv[1], sys.argv[2]
JS = """(T)=>DATA.trips.map(t=>{const s=stateAt(t,T);const r=x=>Math.round(x);
const hm=m=>{m=r(m);return '2026-10-08 '+String(Math.floor(m/60)%24).padStart(2,'0')+':'+String(m%60).padStart(2,'0')};
return {type:'Feature',geometry:{type:'Point',coordinates:[+s.pos.lon.toFixed(5),+s.pos.lat.toFixed(5)]},properties:{
 data_hora:hm(T),id_viagem:t.id,id_caminhao:t.placa,transportadora:t.transportadora,carga:t.carga,volumes:t.volumes,
 cod_origem:t.origem.cod,tipo_origem:t.origem.tipo,nome_origem:t.origem.nome,cod_destino:t.destino.cod,nome_destino:t.destino.nome,uf_destino:t.destino.uf,
 dt_saida_prevista:hm(t.saida_prevista),dt_saida_real:T>=t.saida_real?hm(t.saida_real):null,dt_chegada_prevista:hm(t.chegada_prevista),
 dt_chegada_estimada:hm(s.eta),atraso_min:r(s.atraso),situacao_prazo:s.fase==='aguardando'?'aguardando':s.sit,status_viagem:s.fase,
 dist_total_km:+t.km.toFixed(1),dist_percorrida_km:+s.km.toFixed(1),dist_restante_km:+(t.km-s.km).toFixed(1),pct_percurso:r(100*s.km/t.km),
 rumo:r((s.pos.hdg+360)%360),alerta_meteo:s.wx?(s.wx.rel==='dentro'?'sob aviso':'aviso a frente'):'nao',
 alerta_tipo:s.wx?s.wx.a.tipo:null,alerta_severidade:s.wx?s.wx.a.sev:null,alerta_nivel:s.wx?s.wx.a.nivel:null,
 decisao:null,decisao_por:null,decisao_em:null}}})"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto('file://'+html); pg.wait_for_timeout(800)
    snap=pg.evaluate(JS,900)
    json.dump(dict(type='FeatureCollection',features=snap),open(outdir+'/caminhoes_15h00.geojson','w'),ensure_ascii=False)
    serie=[]
    for T in range(360,1440,10):
        serie+= [f for f in pg.evaluate(JS,T)]
    json.dump(dict(type='FeatureCollection',features=serie),open(outdir+'/caminhoes_serie_10min.geojson','w'),ensure_ascii=False)
    b.close()
from collections import Counter
print(len(snap), Counter(f['properties']['situacao_prazo'] for f in snap), Counter(f['properties']['alerta_meteo'] for f in snap), len(serie))

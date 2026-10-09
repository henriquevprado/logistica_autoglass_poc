"""Monta o painel: injeta CSS/JS do Leaflet e os dados (sim.json) no template.
Uso: python build.py dados/sim.json controle_entregas.html"""
import json, sys, os
here=os.path.dirname(os.path.abspath(__file__))
sim, out = sys.argv[1], sys.argv[2]
d=json.load(open(sim, encoding='utf-8'))
s=open(os.path.join(here,'template.html'), encoding='utf-8').read()
s=s.replace("extra+=tz*(1/({amarelo:.85,laranja:.57,vermelho:.45}[a.sev])-1)","extra+=tz*(1/a.fator-1)")
s=s.replace('/*__LEAFLET_CSS__*/', open(os.path.join(here,'leaflet.css'), encoding='utf-8').read())
# Leaflet embutido: o HTML funciona sem internet (só as fontes do Google caem para fontes do sistema)
s=s.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>',
            '<script>'+open(os.path.join(here,'leaflet.js'), encoding='utf-8').read()+'</script>')
s=s.replace('/*__DATA__*/null', json.dumps(d, ensure_ascii=False, separators=(',',':')))
page='<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+s.replace('<div class="wrap">','</head><body><div class="wrap">',1)+'</body></html>'
open(out,'w',encoding='utf-8').write(page); print('ok', out)

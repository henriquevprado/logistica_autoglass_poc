# POC – Controle de entregas CD → loja (Autoglass)

Painel web com caminhões simulados saindo de CDs/lojas para lojas: situação de prazo,
avisos meteorológicos na rota, próximas chegadas e registro de decisão (seguir, aguardar, desviar, retornar).
**Todos os dados de viagem e de alerta são simulados.**

## Abrir
Abra o `index.html` (ou o endereço publicado no Vercel). Abre em qualquer navegador, sem servidor e sem internet
(sem internet as fontes caem para as do sistema). O relógio abre às 15:00 de 08/10; use Reproduzir ou o controle deslizante.

## Pastas
- `index.html` – painel pronto (dados e biblioteca de mapa embutidos).
- `dados/`
  - `unidades.geojson` – 17 lojas/CDs (geocodificadas com geocodebr/CNEFE).
  - `viagens_simuladas.geojson` – rotas (linhas) com saída/chegada prevista e real.
  - `alertas_simulados.geojson` – polígonos de aviso (níveis INMET, áreas e horários fictícios).
  - `caminhoes_15h00.geojson` – posição dos 16 caminhões às 15:00 (mesmo recorte que o painel abre), com os campos da camada de frota: horários, atraso, situação, km percorridos, rumo, alerta meteorológico e campos de decisão vazios.
  - `caminhoes_serie_10min.geojson` – a mesma camada a cada 10 min, das 06:00 às 23:50 (campo `data_hora`), para usar com o controle de tempo do ArcGIS Pro.
  - `sim.json` – tudo que o painel usa (viagens, trechos de movimento, alertas, malha de fundo).
- `codigo/` – pipeline em Python que gera os dados e o painel.

## Regenerar (Python 3.10+ com `shapely`, `networkx`, `scipy`)
A malha viária não vai no pacote (≈130 MB): é o `shp_poc_log.gpkg` (camadas `vias_principais`, TomTom, e `lojas_autoglass_poc`).

```
python codigo/graph.py shp_poc_log.gpkg trabalho/graph.pkl        # grafo pela conectividade F_JNCTID/T_JNCTID, ONEWAY e MINUTES
python codigo/routes.py shp_poc_log.gpkg trabalho                  # menor caminho de cada viagem (lista TRIPS)
python codigo/gen.py trabalho shp_poc_log.gpkg                     # cenários, alertas e malha de fundo -> trabalho/sim.json
python codigo/build.py trabalho/sim.json index.html    # monta o HTML
python codigo/export_pts.py $PWD/index.html dados     # exporta os pontos dos caminhões (precisa de playwright)
```

## Onde mexer
- Viagens: `TRIPS` em `routes.py` (origem/destino) e `TR` em `gen.py` (saída prevista, atraso de saída, fator de trânsito, paradas não previstas).
- Alertas: `ALERTS` em `gen.py` (rota de referência, posição, raio, horário, nível).
- Regras: caminhão = tempo da via × 1,15; descanso de 30 min a cada 4h30 de direção; folga de 10 min;
  no prazo até 15 min de atraso, atenção 15–60 min, atrasado > 60 min.
- Visual e lógica do painel: `template.html` (cores no bloco `:root`, cálculo da chegada estimada em `stateAt`).

## Limitações da POC
- Decisões ficam salvas só no navegador de quem clicou (localStorage); não são compartilhadas.
- Em produção, posição e horários viriam do rastreador/TMS e os avisos do feed CAP do INMET.

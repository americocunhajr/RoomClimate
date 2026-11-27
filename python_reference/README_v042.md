# RoomClimate v0.4.2 — Laje explícita

Extensão do modelo v0.4.1. Os módulos e resultados anteriores foram preservados; `results_mc*` e `results_sobol` correspondem à topologia anterior, não à nova. Consulte README_v041.md para dados meteorológicos e Sobol, README_v04.md para Monte Carlo e README_v03.md para umidade.

## Modelo

Estado `[Ta,Tm,Tl,w]`: temperatura do ar, massa interna não pertencente à laje, temperatura efetiva da laje, razão de umidade. Unidades SI, temperatura em °C, diferenças em K.

- `Ca dTa/dt = (Gglass+Ginf)(Te-Ta) + Gma(Tm-Ta) + Gla(Tl-Ta) + Qa - Qsens`.
- `Cm dTm/dt = sum_i Gei(Ti-Tm) + Gma(Ta-Tm) + Qm`, com i = divisórias, fachada opaca e piso.
- `Cl dTl/dt = Gel(Tsol-Tl) + Gla(Ta-Tl) + Ql`.
- `m_da dw/dt = m_inf(w_out-w) + m_gen - Qlat/h_fg`.

`Qa+Qm+Ql` é igual à soma dos ganhos sensíveis internos e solares. O modelo de serpentina idealizada da versão anterior foi mantido. Não se modelam condensação nas superfícies, temperatura radiante média, gradientes espaciais ou desempenho real do compressor.

`Cl = A*d*rho*cp`. Espessura 0,15 m, densidade 2300 kg/m³, calor específico 880 J/(kg K), condutividade 1,7 W/(m K), resistência de filme interno 0,10 m² K/W. Todos são hipóteses, não medições. Para 12 m², Cl=3,6432 MJ/K. Cm=1,2 MJ/K, agora explicitamente interpretado como massa sem a laje (hipótese nova). A resistência interna por área é `r_in=0.10+d/(2*k)`; a externa é `r_out=1/U-r_in`. A condutância é A/r. A combinação conserva UA em regime estacionário. U=0 elimina a troca externa; combinações incompatíveis são rejeitadas. Atribuem-se à laje 5% da parcela não convectiva do ganho solar pela janela e 20% da parcela não convectiva dos ganhos internos; são hipóteses sem calibração. A resistência externa efetiva incorpora as camadas e filmes externos. Não se trata de uma solução da condução distribuída na espessura.

## Execução

```
pip install -r requirements.txt
python -m unittest test_roof test_v041 test_mc
python roof.py --out results_roof
```

`roof.py` compara três modelos em três dias sintéticos e seis capacidades (54 simulações de avaliação): original, agregado com capacidade total igual à do novo, e laje explícita. Cada modelo é inicializado em regime periódico sem ar-condicionado. Operação 10–18 h; avaliação 13–18 h; referência 21 °C, tolerância 0,5 °C, UR máxima 65%. Séries e métricas em CSV. Picos estimados na malha de 5 minutos mais nós de mudança de forçante e horários.

`HistoricalRoofSystem` permite utilizar `WeatherArchive` da versão anterior; exemplo:

```python
from datetime import date
from pathlib import Path
from roof import HistoricalRoofSystem, WeatherArchive
from roomclimate import Room, SCENARIOS
arc = WeatherArchive(Path('weather.csv'))
sys = HistoricalRoofSystem(arc, Room(), SCENARIOS[1])
d = date(2024, 1, 15) # requer presença deste dia e dos sete dias anteriores
initial = sys.warm_block(d, 7)
h, y = sys.day(initial, 18000)
print(sys.metrics(h, y, 18000))
```

Verifique convergência do aquecimento inicial para os dados reais (por exemplo, 3, 7 e 14 dias). A interface histórica foi testada com dados sintéticos, não com ERA5 real. Não foi repetido Monte Carlo ou Sobol para a nova topologia. Os parâmetros incertos previamente discutidos continuam válidos como hipóteses, mas a distribuição de Cm agora deverá ser reinterpretada ou revisada; propriedades da laje ainda fixas. Os resultados continuam superestimando temperaturas livres em relação às estimativas do usuário. Não há validação experimental nem garantia de capacidade do aparelho. O próximo passo é atualizar a propagação de incertezas e avaliar a resposta com clima real, além de preparar a interface web.

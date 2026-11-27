# RoomClimate v0.4 — Monte Carlo condicional

Extensão de v0.3. O modelo termo-higrométrico permanece inalterado; os parâmetros são amostrados independentemente no ensaio inicial. A hipótese de independência é provisória, especialmente para U da laje e capacidade térmica efetiva. O clima não é aleatorizado: `--climate 0`, `1`, `2` escolhe um dos três dias sintéticos anteriores. Em cada dia, as temperaturas sol-ar são as forçantes prescritas do v0.2, não calculadas de dados meteorológicos. Não há probabilidades atribuídas aos dias. A futura versão deverá usar séries conjuntas observadas e calcular as forçantes de superfície fisicamente.

| Parâmetro | Distribuição | Unidade |
|---|---|---|
| U da laje | uniforme(0.8,3.5) | W/(m² K) |
| fator solar da janela | triangular(0.35,0.45,0.55) | adimensional |
| infiltração | log-uniforme(0.2,2) | h⁻¹ |
| capacidade térmica efetiva | log-uniforme(0.6,2.4) | MJ/K |
| ganhos internos sensíveis totais | triangular(445,545,695) | W |
| temperatura efetiva da serpentina | uniforme(8,14) | °C |

Triangular(a,m,b) indica mínimo, moda e máximo. Log-uniforme(a,b) significa log(X) uniforme(log(a),log(b)). As faixas são hipóteses de engenharia, não dados. Geometria, ganho latente interno (55 W), propriedades restantes e horários são fixos. As mesmas realizações são aplicadas a todas as capacidades, inclusive à condição sem AC. Cada amostra usa uma inicialização periódica sem refrigeração, como v0.3. LSODA, rtol 1e-6, passo máximo de 240 s, avaliação a cada 5 minutos; o teste de refinamento compara com rtol 1e-9 e passo máximo 30 s em uma realização. Máximos estimados na malha, não garantidos em tempo contínuo. Critério de sucesso conjunto: temperatura <=21.5 °C e UR <=65% entre 13–18 h e ausência de supersaturação simulada no dia. Não há limite inferior de UR. Não há modelo de condensação nas superfícies. Capacidade nominal é limite idealizado, não curva do fabricante.

## Execução

```sh
pip install -r requirements.txt
python test_mc.py
python roomclimate_mc.py --n 128 --seed 20261126 --climate 1 --workers 4 --out results_mc_128
```

`results_mc` contém o piloto de 32 amostras; `results_mc_128` contém o ensaio de 128 amostras. Cada CSV de amostras contém as seis capacidades por realização; summary.csv contém as frequências, intervalos de Wilson marginais de 95% e quantis empíricos de temperatura e UR máximas. Os intervalos de Wilson representam apenas erro amostral de Monte Carlo condicional ao modelo, não incerteza de modelagem, validação física ou probabilidade anual de conforto. Não usar para certificar dimensionamento. O modelo anterior superestimava a temperatura livre relatada; esse problema continua em aberto. Os ensaios de 32 e 128 usam a mesma semente, mas não são amostras aninhadas, devido à ordem de geração dos vetores.

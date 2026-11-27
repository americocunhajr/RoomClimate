# RoomClimate

**Pré-dimensionamento de ar-condicionado por simulação física e análise de incertezas.**

Versão 1.0 beta · Aplicação web em português brasileiro · Execução no navegador

[Manual de uso](MANUAL.md) · [Manual para o navegador](manual.html) · [Documentação científica](python_reference/README.md) · [Publicação](#publicação-no-github-pages)

**[Abrir o RoomClimate no GitHub Pages (após ativação)](https://americocunhajr.github.io/RoomClimate/)**

## Por que o RoomClimate?

A capacidade necessária de um ar-condicionado depende não apenas da área da sala, mas também do sol que incide nas janelas e na cobertura, das propriedades térmicas da construção, da infiltração de ar, da ocupação, dos equipamentos e da temperatura desejada. O calor acumulado nas superfícies também influencia a evolução da temperatura ao longo do dia.

O RoomClimate combina um editor de planta, um modelo térmico transiente e uma análise opcional de incertezas para apoiar a comparação de capacidades comerciais. Destina-se a estudantes, engenheiros, profissionais de climatização e usuários que desejam fazer uma avaliação preliminar antes de adquirir um equipamento.

> **Aviso:** esta versão beta tem verificação numérica, mas não validação experimental. É uma ferramenta de pré-dimensionamento, não um projeto executivo, uma certificação de conformidade normativa ou uma garantia de conforto.

## Início rápido

1. Abra `index.html` em um navegador moderno ou acesse a página publicada quando estiver disponível.
2. Informe comprimento, largura e pé-direito; configure fachadas, janelas e proteção solar.
3. Informe a temperatura desejada, as fontes de calor, a cobertura e o cenário climático.
4. Clique em **Comparar aparelhos**. Observe a menor capacidade testada que satisfaz simultaneamente os critérios de temperatura e umidade.
5. Compare os gráficos com e sem refrigeração. Se houver incertezas relevantes, use **Testar incertezas**.
6. Exporte a configuração JSON e os resultados CSV para registrar e reproduzir a análise.

O exemplo inicial é um escritório de 12 m² no Rio de Janeiro, com janela voltada para oeste, meta de 21 °C e parâmetros estimados. Ele serve para demonstrar o uso, não como configuração universal. O [manual](MANUAL.md) detalha as etapas e a interpretação dos resultados.

## Recursos

| Recurso | Descrição |
| --- | --- |
| Editor geométrico | Sala retangular, múltiplas fachadas externas, janelas com dimensões e fatores solares próprios, representação de móveis, porta e aparelho. |
| Simulação dinâmica | Temperaturas do ar, massa térmica interna e cobertura, além da umidade do ar ao longo de 24 horas. |
| Comparação | Sem refrigeração e capacidades nominais de 7.500, 9.000, 12.000, 18.000 e 24.000 BTU/h. |
| Radiação solar | Posição do Sol, orientação das fachadas, componentes direta, difusa e refletida da irradiância e sombreamento parametrizado. |
| Climatologia | Dia sintético simplificado, céu sintético com geometria solar ou importação horária de série histórica ERA5. |
| Incertezas | Monte Carlo com 10 parâmetros, intervalos ajustáveis, semente configurável e estimativas de frequência de atendimento. |
| Resultados | Tabela de atendimento, gráficos temporais, limite de conforto e período de avaliação destacados. |
| Reprodutibilidade | Exportação JSON e CSV, código Python de referência, testes e resultados de versões anteriores. |

## Como o modelo funciona

O motor considera uma única zona com ar perfeitamente misturado. A construção é representada por uma rede de resistências e capacitâncias térmicas, com três temperaturas independentes (ar, massa interna e laje) e uma variável de umidade. As trocas térmicas com o exterior, piso e recintos adjacentes, os ganhos solares e internos e a entrada de ar compõem as excitações do sistema.

A cobertura tem capacidade térmica própria, permitindo representar atraso e armazenamento de calor. A radiação é projetada sobre cada superfície a partir da geometria solar; a radiação difusa segue uma aproximação isotrópica. O equipamento é modelado por um controlador com capacidade limitada e uma serpentina efetiva que determina a repartição sensível e latente. O navegador resolve as equações com Runge–Kutta de quarta ordem e passo limitado pelas escalas temporais do sistema. Nos cenários sintéticos, a inicialização é periódica sem refrigeração; no modo histórico, os dias antecedentes aquecem o modelo antes do dia avaliado.

O critério determinístico exige que a temperatura máxima no período selecionado não ultrapasse a meta mais a tolerância e que a umidade relativa máxima respeite o limite informado. Supersaturação simulada invalida a classificação. A indicação é a menor **capacidade testada**, não o ótimo contínuo nem a capacidade efetiva de um modelo comercial específico.

### Meteorologia

- **Dia quente simplificado:** perfis sintéticos, sem cálculo de orientação solar.
- **Sol conforme localização:** posição solar dependente de latitude, longitude, data e fuso horário, com condições atmosféricas sintéticas.
- **Dados meteorológicos históricos:** séries horárias de temperatura, ponto de orvalho e radiação da reanálise ERA5, obtidas via Open-Meteo ou importadas em JSON. Não representam uma previsão nem necessariamente uma medição local. A chamada real à API ainda não foi verificada no ambiente de desenvolvimento; a importação foi testada com dados sintéticos explicitamente identificados.

### Quantificação de incertezas

O Monte Carlo no navegador mantém o dia climático fixo e sorteia propriedades físicas independentes. Os intervalos são hipóteses exploratórias, não distribuições calibradas para todas as construções.

| Parâmetro | Distribuição inicial |
| --- | --- |
| Transmitância da cobertura | Uniforme |
| Multiplicador da proteção solar | Triangular |
| Infiltração de ar | Log-uniforme |
| Multiplicador da capacidade térmica interna | Log-uniforme |
| Multiplicador dos ganhos internos | Triangular |
| Temperatura efetiva da serpentina | Uniforme |
| Espessura da laje | Uniforme |
| Densidade, calor específico e condutividade do concreto | Triangular (cada parâmetro) |

Os suportes respeitam a positividade e os limites físicos; os intervalos da laje também são verificados quanto à compatibilidade entre resistências térmicas. As mesmas realizações são empregadas para todas as capacidades. A frequência de atendimento conjunto é acompanhada por um intervalo de Wilson marginal de 95%; a recomendação probabilística compara seu limite inferior com a meta definida. Esses intervalos quantificam apenas a incerteza amostral, não erros de modelagem. Não se trata de uma probabilidade anual de conforto. Os índices de Sobol estão disponíveis no código Python de referência, não na interface web.

## Arquivos e desenvolvimento

```text
.
├── index.html                 # Aplicação autocontida, entrada do GitHub Pages
├── RoomClimate.html           # Cópia para execução local
├── manual.html                # Manual de uso para o navegador
├── MANUAL.md                  # Manual de uso em Markdown
├── README.md                  # Este documento
├── web/
│   ├── index.html             # Estrutura da interface
│   ├── style.css              # Tema e layout responsivo
│   ├── solar.js               # Geometria solar e meteorologia
│   ├── core.js                # Núcleo termo-higrométrico
│   ├── app.js                 # Editor, interface e exportações
│   └── uncertainty.js         # Monte Carlo e análise estatística
├── build.py                   # Geração do HTML autocontido
├── fixtures/                  # Dados sintéticos para testes
├── python_reference/          # Modelos, testes e resultados científicos anteriores
├── test_core.js
├── test_solar.js
├── test_uncertainty.js
├── test_release.py
└── .nojekyll                  # Hospedagem estática sem processamento Jekyll
```

A aplicação não requer instalação de frameworks, banco de dados ou servidor de cálculo. Para desenvolver localmente, instale Python 3 e Node.js. Edite os arquivos em `web/` (não apenas os arquivos gerados) e execute:

```sh
python build.py
python -m http.server 8000
```

Abra `http://localhost:8000`. Também é possível abrir `index.html` diretamente nos modos sintéticos. Para consultar dados meteorológicos externos, é necessário acesso à internet.

## Verificação e testes

```sh
node test_core.js
node test_solar.js
node test_uncertainty.js
python test_release.py
```

Os três primeiros testes não requerem bibliotecas externas. O último requer Playwright para Python e Chromium, atualmente configurado em `/usr/bin/chromium`. Ajuste o caminho se necessário. O teste da interface verifica a configuração inicial, mudanças de parâmetros, Monte Carlo, importação meteorológica controlada, exportação JSON e comportamento em telas pequenas.

Para os modelos de referência em Python, consulte `python_reference/README.md` e instale as dependências com `python -m pip install -r python_reference/requirements.txt`. Os arquivos `verification_*.txt` e os diretórios de resultados preservam a evidência dos ensaios anteriores. A concordância com o modelo Python e o refinamento temporal verificam a implementação, mas não validam a representação física de um ambiente real.

## Publicação no GitHub Pages

1. O repositório público `americocunhajr/RoomClimate` utiliza a licença MIT.
2. Envie o conteúdo deste pacote para a raiz da branch `main`, incluindo `index.html`, `manual.html`, o README e `.nojekyll`.
3. Em **Settings → Pages → Build and deployment**, selecione **Deploy from a branch** e escolha `main` e `/ (root)`. Salve.
4. Após a publicação, abra o endereço apresentado pelo GitHub e teste a simulação, os links do manual e as exportações.

Veja a [documentação oficial do GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site). O site é estático; não é necessário configurar um backend.

## Privacidade e dados

O processamento térmico e a amostragem são realizados no dispositivo do usuário. Não há cadastro, serviço de armazenamento de configurações ou telemetria implementada. Ao solicitar uma série meteorológica, a localização e as datas são enviadas ao Open-Meteo, sujeito aos termos e à política de privacidade desse provedor. A importação de arquivo local é uma alternativa. Os arquivos exportados podem conter dados da sala e coordenadas; revise-os antes de compartilhá-los.

## Escopo, limitações e próximos passos

- Modelo de zona única, com cobertura termicamente exposta e pelo menos uma fachada externa. Móveis e posição do aparelho têm função geométrica, sem simulação de escoamento ou conforto local.
- Propriedades térmicas, infiltração, ocupação e temperaturas adjacentes são estimadas. A configuração de exemplo pode superestimar a temperatura sem refrigeração em relação ao ambiente real que a motivou.
- A potência nominal é idealizada; não há curvas de desempenho de equipamentos, avaliação de consumo elétrico, ventilação normativa, condensação superficial ou certificação de conformidade com a ABNT NBR 16401.
- O modelo ainda necessita de validação experimental, comparação sistemática com ferramentas como EnergyPlus e ensaios com climatologia histórica real. A seleção final do equipamento deve considerar dados do fabricante e avaliação profissional.

## Contribuições

Relatos de erros e sugestões são bem-vindos. Ao documentar um problema, informe a versão, navegador, cenário e passos para reproduzi-lo; anexe o JSON da configuração apenas se não contiver informações que deseja manter privadas. Para alterações no motor, inclua hipóteses, testes e casos de referência. Alterações na interface devem preservar a acessibilidade, a apresentação em português e a distinção entre simulação e validação.

## Referências e recursos

- [EnergyPlus](https://energyplus.net/) — referência para simulação energética de edificações.
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) — acesso à reanálise meteorológica, com atribuição e condições de uso do provedor.
- [NOAA Solar Calculation Details](https://gml.noaa.gov/grad/solcalc/calcdetails.html) — aproximações de geometria solar.
- [CBE Thermal Comfort Tool](https://comfort.cbe.berkeley.edu/) — referência complementar de conforto térmico.
- [Modelica Buildings Library](https://simulationresearch.lbl.gov/modelica/) — modelagem física de edificações e sistemas HVAC.

## Licença

Distribuído sob a [licença MIT](LICENSE), selecionada na criação deste repositório. Os dados meteorológicos de terceiros têm termos próprios.

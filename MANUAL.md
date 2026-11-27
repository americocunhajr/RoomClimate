# RoomClimate — Manual de uso

**Versão 1.0 beta · Guia rápido de pré-dimensionamento**

O RoomClimate estima como uma sala aquece durante o dia e compara aparelhos de ar-condicionado. O objetivo é ajudar na escolha inicial de capacidade, não substituir um projeto de climatização.

## 1. Descreva sua sala

- Em **Seu ambiente**, informe largura, comprimento e pé-direito em metros.
- Selecione a fachada externa e marque as demais paredes que dão para a rua, se houver. Cadastre as janelas: largura, altura, altura do peitoril e posição ao longo da parede. Revise a planta para conferir as medidas.
- Em **Mobiliário e instalação**, represente os móveis, a porta e o aparelho. Essas posições não alteram a circulação de ar no modelo atual.

## 2. Informe as condições de uso

Em **Condições de uso**, escolha o isolamento da cobertura e a proteção solar das janelas. Se não souber, compare mais de uma opção. Informe a temperatura desejada, tolerância, limite de umidade e entrada de ar.

Use **Calcular ganhos internos a partir de pessoas e aparelhos** para informar quantidades e potências. Clique em **Aplicar estimativa**. Considere apenas equipamentos efetivamente ligados no horário de ocupação; use potências realistas, não necessariamente as máximas de placa.

Ajuste os horários de funcionamento, ocupação e avaliação. O horário é decimal: 13,5 significa 13h30. Ligue o aparelho antes do período que deseja avaliar se precisar de tempo para resfriar a sala.

## 3. Escolha o clima e o sol

Em **Clima, localização e sol**, selecione uma das três opções:

| Opção | Quando usar |
| --- | --- |
| Dia quente simplificado | Estimativa rápida, sem orientação solar. |
| Sol conforme localização | Compare o efeito da orientação das janelas em determinada data. O clima é sintético. |
| Dados meteorológicos históricos | Use uma série horária importada ou solicite dados ERA5. Requer dias antecedentes para representar a memória térmica da construção. |

Nos modos com geometria solar, informe latitude, longitude, data, fuso horário e orientação da parede superior da planta: norte = 0°, leste = 90°, sul = 180° e oeste = 270°. Confira a indicação de norte na planta. No modo histórico, clique em **Obter série ERA5** ou **Importar JSON ERA5**. A consulta depende de internet e do serviço externo; em caso de falha, use um arquivo compatível ou um cenário sintético.

## 4. Compare as capacidades

Clique em **Comparar aparelhos**. A tabela apresenta temperatura e umidade máximas no intervalo avaliado, para cada capacidade, incluindo a sala sem refrigeração.

- **Atende:** satisfaz simultaneamente os limites informados, sem supersaturação simulada.
- **Não atende:** pelo menos um dos critérios não foi atingido.
- **Supersaturação:** resultado fora do domínio de validade do modelo de umidade. Revise o cenário; não use essa classificação para decidir a compra.

A menor capacidade que atende é uma **candidata**, não uma garantia. Nos gráficos, compare a temperatura com e sem aparelho, a umidade, a temperatura da laje e a incidência solar. A região sombreada indica o intervalo avaliado. Se o aparelho não atende, compare também a melhoria de proteção solar, isolamento e vedação antes de aumentar a potência.

## 5. Teste as incertezas (opcional)

Em **E se minhas estimativas estiverem erradas?**, revise os intervalos das propriedades. Os valores iniciais pertencem ao exemplo de escritório; não os aplique automaticamente a outra construção.

Escolha o número de combinações, a meta de atendimento e a semente. Comece com 16 ou 32 combinações para explorar; use mais para reduzir a incerteza amostral. Clique em **Testar incertezas**. A análise pode levar alguns minutos, dependendo do dispositivo.

Uma frequência de 90% indica que o aparelho atendeu em 90% das combinações simuladas naquele dia. Não significa 90% dos dias do ano. O simulador também mostra um intervalo estatístico: a indicação usa seu limite inferior. Mesmo sem falhas, uma amostra pequena pode não demonstrar uma meta elevada.

## 6. Salve e revise

Em **Salvar e compartilhar**, use **Exportar JSON** para salvar a configuração e **Importar JSON** para retomá-la. **Exportar CSV** salva as séries de temperatura e umidade, após a simulação. Na análise de incertezas, **Exportar amostras CSV** salva as realizações e um JSON com as hipóteses. Sempre execute novamente após alterar os parâmetros.

Antes da compra, confira as dimensões, a orientação solar, as condições de verão, a vedação e as propriedades da cobertura. Repita a análise para diferentes dias e condições plausíveis. Consulte a capacidade efetiva e os requisitos de instalação do fabricante e um profissional habilitado.

**Limitações:** o RoomClimate é uma versão beta sem validação experimental. Não calcula a distribuição espacial do ar, a ventilação normativa, o consumo elétrico nem a condensação em superfícies. A posição dos móveis e do aparelho é apenas ilustrativa. A análise histórica online ainda não foi verificada com acesso real ao serviço. Os resultados são estimativas condicionadas às informações fornecidas.

[Voltar ao simulador](index.html) · [Documentação do projeto](README.md)

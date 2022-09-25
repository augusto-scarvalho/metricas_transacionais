from datetime import date, datetime, timedelta
import pytz

import json
import glob
import re

from dash import Dash, dcc, html
from dash.dependencies import Input, Output

import plotly.graph_objects as go
import plotly.express as px

import pandas as pd

app = Dash(__name__)

pattern_filename = re.compile(r"data\/(.*)\.json")

dados_dict = {}

paths = [path for path in glob.glob('data/*', recursive=True)]
transacoes = [pattern_filename.match(path)[1] for path in paths]


for index, path in enumerate(paths):
    with open(path, "rb") as f:
        dados_dict[transacoes[index]] = json.loads(f.read())

transacao = transacoes[0]
dados = dados_dict[transacao]


# retorna uma lista de objetos para o seletor dropdown
def retorna_labels_dropdown():
    return [{"label": trn, "value": trn} for trn in dados_dict.keys()]


labels_dropdown = retorna_labels_dropdown()

# convertendo de str para date todas as chaves do dict
datas = sorted([date.fromisoformat(data) for data in dados])

timezone = pytz.timezone("Brazil/East")

hoje = datetime.now(timezone).date()
dia_mes_anterior = date(hoje.year, hoje.month-1, hoje.day)

# se D e D-30 estão contidos no range de datas disponíveis
# se não estiverem
# o início e final do intervalo serão os extremos da lista datas
start_date = dia_mes_anterior if dia_mes_anterior in datas else datas[0]
end_date = hoje if hoje in datas else datas[-1]


# retorna a soma de acessos de uma etapa em um intervalo de datas
def retorna_acessos_range(etapa, datas_intervalo):
    return sum([dados[data_index.strftime('%Y-%m-%d')][etapa]["acessos"] for data_index in datas_intervalo])


# dada uma cor, retorna a cor com opacidade e tonalidade mais pastel
def pasteurizar_cor(cor, opacidade):
    rgb = [round(x,) for x in px.colors.unlabel_rgb(cor)]
    offset = 0
    # offset = 255 - max(rgb) # descomentar caso queira deixar as cores mais pastel
    rgb = px.colors.label_rgb(tuple(
        [(componente + offset) for componente in rgb]))[:-1]+', '+str(opacidade)+')'
    return rgb.replace('rgb', 'rgba')


# montando layout da dashboard
app.layout = html.Div(
    className="container scalable",
    children=[
        html.Div(
            id="banner",
            className="banner",
            children=[
                html.H6("Dashboard transações"),
                html.Img(src=app.get_asset_url("logo.png")),
            ],
        ),
        html.Div(
            className="app_main_content",
            children=[
                html.Div(
                    id="dropdown-select-outer",
                    children=[
                        html.Div(
                            [
                                html.P("Selecione uma jornada"),
                                dcc.Dropdown(
                                    id="dropdown-select",
                                    options=labels_dropdown,
                                    value=labels_dropdown[0]["value"]
                                ),
                            ],
                            className="selector",
                        ),
                        html.Div(
                            [
                                html.P("Selecione um intervalo de datas"),
                                dcc.DatePickerRange(
                                    id="my-date-picker-range",
                                    min_date_allowed=datas[0],
                                    max_date_allowed=end_date,
                                    initial_visible_month=start_date,
                                    end_date=end_date,
                                    start_date=start_date,
                                    display_format="DD/MM/YYYY",
                                    start_date_placeholder_text="dia/mês/ano",
                                    minimum_nights=0
                                )
                            ],
                            # style={'textAlign': 'center'},
                            id="date-picker-outer",
                            className="selector",
                        ),
                    ]
                ),
                html.Div(
                    id="top-row",
                    className="row",
                    children=[
                        html.Div(
                            id="sankey-outer",
                            className="twelve columns",
                            children=[dcc.Graph(id='sankey-transacao')],
                            style={"textAlign": "center"}
                        )
                    ],
                ),
                html.Div(
                    id="middle-row",
                    className="row",
                    children=[
                        html.Div(
                            id="time-series-outer",
                            className="twelve columns",
                            children=[dcc.Graph(id='serie-temporal-transacao')],
                            style={"textAlign": "center"}
                        )
                    ],
                ),
                html.Div(
                    id="bottom-row",
                    className="row",
                    children=[
                        html.Div(
                            id="funnel-outer",
                            className="twelve columns",
                            children=[dcc.Graph(id='funil-transacao')],
                            style={"textAlign": "center"}
                        )
                    ],
                ),
            ]
        )
    ]
)


@app.callback(
    Output('sankey-transacao', 'figure'),
    Output('serie-temporal-transacao', 'figure'),
    Output('funil-transacao', 'figure'),
    Input('my-date-picker-range', 'start_date'),
    Input('my-date-picker-range', 'end_date'),
    Input('dropdown-select', 'value'))
def update_sankey(start_date, end_date, value):

    if start_date is not None:
        start_date_object = date.fromisoformat(start_date)
        start_date_string = start_date_object.strftime('%d/%m/%Y')

    if end_date is not None:
        end_date_object = date.fromisoformat(end_date)
        end_date_string = end_date_object.strftime('%d/%m/%Y')

    if (start_date is not None) and (end_date is not None) and (value is not None):
        # cria uma lista com todas as datas entre start_date e end_date
        datas_intervalo = sorted([
            start_date_object+timedelta(days=x) for x in range(
                (end_date_object-start_date_object).days + 1)])

        transacao = value
        dados = dados_dict[transacao]

        # criando uma amostra de dados para gerar a estrutura do grafo
        amostra = dados[datas_intervalo[0].strftime('%Y-%m-%d')]

        etapas = [etapa for etapa in amostra]

        # buscando a quantidade de acessos da etapa inicial
        acessos_inicial_ref = [etapa for etapa in amostra if amostra[etapa].get(
            "flags") and "inicial" in amostra[etapa].get("flags")]
        acessos_inicial = retorna_acessos_range(
            acessos_inicial_ref[0], datas_intervalo) if len(acessos_inicial_ref) > 0 else 0

        origens = []
        alvos = []
        valores = []
        porcent_ant = []
        porcent_ini = []
        percentuais = []

        # criando uma cor para cada nó do grafo dentro do gradiente escolhido
        cores = px.colors.sample_colorscale(
            "plasma", [n / (len(etapas) + 1) for n in range(len(etapas))])

        # para cada um dos pares de nodos do grafo
        for pares in [[(x[0], y) for y in x[1]] for x in [(etapa, amostra[etapa]["prox_passo"]) for etapa in amostra] if len(x[1]) > 0]:
            # cada par em pares é representado por uma tupla (origem,alvo)
            for par in pares:
                origens += [etapas.index(par[0])]
                alvos += [etapas.index(par[1])]
                # busca todos os acessos do nodo alvo dentro do intervalo de datas
                valores += [retorna_acessos_range(par[1], datas_intervalo)]
                # busca todos os acessos do nodo origem dentro do intervalo de datas
                acessos_origem = retorna_acessos_range(
                    par[0], datas_intervalo)
                # calculando percentual de conversão entre as etapas origem → alvo
                porcent_ant += [(valores[-1] / acessos_origem) *
                                100] if acessos_origem > 0 and valores[-1] > 0 else [0.00]
                # calculando percentual de conversão entre as etapas inicial → atual
                porcent_ini += [(valores[-1] / acessos_inicial) *
                                100] if acessos_inicial > 0 and valores[-1] > 0 else [0.00]
                # preparando template de exibição de métricas para o grafo
                percentuais += [
                    f'{round(porcent_ant[-1], 2)}% em relação a etapa anterior {par[0]}<br />{round(porcent_ini[-1], 2)}% em da etapa inicial {acessos_inicial_ref[0] if len(acessos_inicial_ref) > 0 else ""}']

        ## gerando o sankey
        sankey = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=etapas,
                color=cores,
                hovertemplate='Etapa %{label} teve um total de %{value:,.0f} acessos<extra></extra>'
            ),
            link=dict(
                source=origens,
                target=alvos,
                value=valores,
                customdata=percentuais,
                color=[pasteurizar_cor(cor, 0.3) for cor in cores],
                # hovertemplate='%{value:,.0f} acessos da etapa %{source.label} para a etapa %{target.label}<br />'+'representando %{customdata:,.2f}% dos %{source.value} acessos da etapa %{source.label}'
                # hovertemplate='Acessos: %{value:,.0f}<br />' + '%{customdata:,.2f}% dos %{source.value} acessos da etapa %{source.label}'
                hovertemplate='Acessos: %{value:,.0f}<br />%{customdata}'
            ))])

        sankey.update_layout(
            title={
                "text": f"Fluxo da transação <b>{transacao}</b> {'em '+start_date_string if start_date_string == end_date_string else 'de '+start_date_string + ' até ' + end_date_string}",
                "x": 0.5,
                "xanchor": "center"
            },
            font_size=12,
            paper_bgcolor='rgba(244,244,244,0.7)',
            plot_bgcolor='rgba(244,244,244,0.7)'
        )

        # gerando o gráfico da série temporal
        # transformando em registros cada um dos dados serializados no json
        dados_normalizados = [(dia, etapa, dados[dia][etapa]["acessos"], True if dados[dia][etapa].get("flags") and "funil" in dados[dia][etapa].get("flags") else False) for dia in dados for etapa in dados[dia]]

        # criando um df para ser utilizado no gráfico de linhas
        df_linhas = pd.DataFrame(dados_normalizados, columns=["dia", "etapa", "acessos", "funil"])

        # criando uma máscara para filtrar os dados de acordo as datas de início e fim escolhidas no datepicker
        mask = (df_linhas['dia'] >= datas_intervalo[0].strftime('%Y-%m-%d')) & (df_linhas['dia'] <= datas_intervalo[-1].strftime('%Y-%m-%d'))
        df_linhas = df_linhas.loc[mask]

        linhas = px.line(df_linhas, x="dia", y="acessos", color='etapa')

        # gerando o gráfico de funil
        # filtrando o df apenas com as etapas que representam o funil de conversão
        df_funil = df_linhas.loc[df_linhas["funil"]].groupby("etapa").sum()
        funil = go.Figure(go.Funnel(y=df_funil.axes[0], x=df_funil["acessos"]))

        return sankey, linhas, funil


if __name__ == '__main__':
    app.run_server(
        debug=False,
    )
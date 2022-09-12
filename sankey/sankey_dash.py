from datetime import date, datetime, timedelta
import pytz

import json

from dash import Dash, dcc, html
from dash.dependencies import Input, Output

import plotly.graph_objects as go
import plotly.express as px

app = Dash(__name__)

transacao = "Mock transaction"

with open("./data/dados.json", "rb") as file:
    dados = json.loads(file.read())

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
app.layout = html.Div([

    html.Div(html.H1("Dashboard transações"),
             style={'textAlign': 'center'}),

    html.Div(
        dcc.DatePickerRange(
            id='my-date-picker-range',
            min_date_allowed=datas[0],
            max_date_allowed=end_date,
            initial_visible_month=start_date,
            end_date=end_date,
            start_date=start_date,
            display_format='DD/MM/YYYY',
            start_date_placeholder_text='dia/mês/ano'
        ), style={'textAlign': 'center'}),

    dcc.Graph(id='sankey-transacao', style={'textAlign': 'center'}),

])


@app.callback(
    Output('sankey-transacao', 'figure'),
    Input('my-date-picker-range', 'start_date'),
    Input('my-date-picker-range', 'end_date'))
def update_graph(start_date, end_date):

    if start_date is not None:
        start_date_object = date.fromisoformat(start_date)
        start_date_string = start_date_object.strftime('%d/%m/%Y')

    if end_date is not None:
        end_date_object = date.fromisoformat(end_date)
        end_date_string = end_date_object.strftime('%d/%m/%Y')

    if (start_date is not None) and (end_date is not None):
        # cria uma lista com todas as datas entre start_date e end_date
        datas_intervalo = [
            start_date_object+timedelta(days=x) for x in range((end_date_object-start_date_object).days + 1)]

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

        # gerando o grafo
        fig = go.Figure(data=[go.Sankey(
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

        fig.update_layout(
            title={
                "text": f"Fluxo da transação {transacao} {'em '+start_date_string if start_date_string == end_date_string else 'de '+start_date_string + ' até ' + end_date_string}",
                "x": 0.5,
                "xanchor": "center"
            },
            font_size=12,
            paper_bgcolor='rgba(244,244,244,0.7)',
            plot_bgcolor='rgba(244,244,244,0.7)'
        )

        return fig


if __name__ == '__main__':
    app.run_server(debug=True)
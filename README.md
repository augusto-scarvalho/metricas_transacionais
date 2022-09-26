# Chatbot transactions dashboard

Um protótipo de dashboard para acompanhamento de jornadas transacionais.

Usando plotly e dash para plotar os gráficos.

Os dados precisam seguir o seguinte template:

```JSON
{
    /*Data no formato YYYY-MM-DD*/
    "2022-09-11": {
        /*Nome do nodo/etapa da transação*/
        "etapa1": {
            /*Lista com os próximos nodos/etapas*/
            "prox_passo": ["etapa1-1", "etapa1-2", "etapa-2"],
            /*Metadados úteis, p.ex: indicar se a etapa faz parte do funil*/
            "flags": ["funil", "inicial"],
            /*Quantidade de acessos*/
            "acessos": 50
        },
        "etapa1-1": {
            "prox_passo": [],
            "acessos": 2
        },
        "etapa1-2": {
            "prox_passo": [],
            "acessos": 4
        },
        "etapa2": {
            "prox_passo": [],
            "flags": ["funil"],
            "acessos": 44
        },
    },
    /*
    .
    .
    .
    */
}
```
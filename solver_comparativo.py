# analise_resultados.py
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def analisar_desempenho(resultados_totais):
    """Analisa estatisticamente os resultados"""
    
    dados = []
    for nome_cenario, resultados in resultados_totais:
        for resultado in resultados:
            dados.append({
                'Cenario': nome_cenario,
                'Algoritmo': resultado.algoritmo,
                'Custo': resultado.custo if resultado.viável else np.nan,
                'Tempo': resultado.tempo,
                'Viavel': resultado.viável
            })
    
    df = pd.DataFrame(dados)
    
    return df

# Para executar a análise, adicione ao main:
if __name__ == "__main__":
    from cenarios_comparacao import testar_cenarios
    import random
    random.seed(42)
    
    resultados = testar_cenarios()
    df = analisar_desempenho(resultados)
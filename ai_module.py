# ai_module.py (Versão Global)

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import joblib
import database

# O nome do nosso modelo global
NOME_ARQUIVO_MODELO = "modelo_categorizacao_global.joblib"

def treinar_modelo_global():
    """
    Busca dados de TODOS os usuários, treina um modelo de IA global e o salva.
    Esta função deve ser chamada periodicamente pelo administrador do sistema.
    """
    print("Iniciando treinamento do modelo global...")
    
    # 1. Busca os dados de treinamento
    despesas_raw = database.get_all_despesas_for_training()

    if len(despesas_raw) < 100: # Definimos um mínimo maior para o modelo global
        print("Dados insuficientes para treinamento. Necessário pelo menos 100 despesas no total.")
        return

    df = pd.DataFrame(despesas_raw, columns=["Descrição", "Categoria"])
    df.dropna(subset=['Descrição', 'Categoria'], inplace=True)
    print(f"Treinando com {len(df)} exemplos de despesas.")

    # 2. Define o pipeline do modelo
    model_pipeline = Pipeline([
        ('vectorizer', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ('classifier', MultinomialNB(alpha=0.1))
    ])

    # 3. Treina o modelo
    X = df['Descrição']
    y = df['Categoria']
    model_pipeline.fit(X, y)

    # 4. Salva o modelo global
    joblib.dump(model_pipeline, NOME_ARQUIVO_MODELO)
    print(f"Modelo global salvo com sucesso em '{NOME_ARQUIVO_MODELO}'!")

def prever_categoria(descricao):
    """
    Carrega o modelo de IA GLOBAL e prevê a categoria para uma nova descrição.
    """
    try:
        modelo = joblib.load(NOME_ARQUIVO_MODELO)
        previsao = modelo.predict([descricao])
        return previsao[0]
    except FileNotFoundError:
        # Modelo global ainda não foi treinado.
        return None
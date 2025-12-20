# 1. Buscar TODAS as subcategorias do usuário
# Esperado: (subcategoria_id, categoria_id, nome)
subcats = database.get_subcategorias(user_id)

if not subcats:
    st.warning("Você precisa cadastrar subcategorias de despesa antes de poder definir um orçamento.")
else:
    # 2. Buscar orçamentos já definidos (chave = nome da subcategoria)
    orcamentos_definidos = database.get_orcamentos(user_id)
    orcamentos_dict = {orc[0]: orc[1] for orc in orcamentos_definidos}

    # 3. Montar lista de subcategorias ÚNICAS pelo nome
    nomes_unicos = sorted({sub_nome for _, _, sub_nome in subcats})

    dados_editor = []
    for sub_nome in nomes_unicos:
        chave = sub_nome  # orçamento só por subcategoria
        limite_atual = orcamentos_dict.get(chave, 0.0)
        dados_editor.append(
            {
                "Subcategoria": sub_nome,
                "Limite Mensal": limite_atual,
            }
        )

    df_orcamento = pd.DataFrame(dados_editor)

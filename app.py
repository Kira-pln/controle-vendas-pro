import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

# -------------------------------------------------
# CONFIGURAÇÃO (MOBILE-FIRST)
# -------------------------------------------------
st.set_page_config(
    page_title="Inova Eletro Móveis",
    layout="centered"
)

# -------------------------------------------------
# ESTILO E TÍTULO FIXO
# -------------------------------------------------
st.markdown("""
<style>
header {visibility: hidden;}
.main-title {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background-color: #111827;
    color: white;
    text-align: center;
    padding: 12px;
    font-size: 22px;
    font-weight: 600;
    z-index: 1000;
}
.block-container {
    padding-top: 80px;
}
</style>

<div class="main-title">Inova Eletro Móveis</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# CONEXÃO COM BANCO
# -------------------------------------------------
conn = sqlite3.connect("vendas.db", check_same_thread=False)
cur = conn.cursor()

# -------------------------------------------------
# TABELAS
# -------------------------------------------------
cur.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    descricao TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto TEXT,
    quantidade INTEGER,
    preco REAL,
    percentual REAL,
    valor_receber REAL,
    metodo_pagamento TEXT,
    parcelas INTEGER,
    data TEXT
)
""")

conn.commit()

# -------------------------------------------------
# MENU
# -------------------------------------------------
st.sidebar.title("Menu")
pagina = st.sidebar.radio(
    "Navegação",
    ["Cadastro de produtos", "Registrar venda", "Relatórios"]
)

# =================================================
# CADASTRO DE PRODUTOS
# =================================================
if pagina == "Cadastro de produtos":

    st.title("Cadastro de produtos")

    nome = st.text_input("Nome do produto")
    descricao = st.text_input("Descrição do produto")

    if st.button("Cadastrar produto"):
        if nome.strip() == "":
            st.warning("Informe o nome do produto.")
        else:
            cur.execute(
                "INSERT INTO produtos (nome, descricao) VALUES (?, ?)",
                (nome, descricao)
            )
            conn.commit()
            st.success("Produto cadastrado com sucesso.")

    produtos = pd.read_sql("SELECT * FROM produtos", conn)

    st.subheader("Produtos cadastrados")
    st.dataframe(produtos, use_container_width=True)

    if not produtos.empty:
        st.subheader("Excluir produto")
        pid = st.selectbox(
            "Selecione o produto",
            produtos["id"],
            format_func=lambda x: produtos.loc[produtos["id"] == x, "nome"].values[0]
        )

        if st.button("Excluir produto"):
            cur.execute("DELETE FROM produtos WHERE id=?", (pid,))
            conn.commit()
            st.success("Produto excluído.")
            st.rerun()

# =================================================
# REGISTRAR VENDA
# =================================================
elif pagina == "Registrar venda":

    st.title("Registrar venda")

    produtos = pd.read_sql("SELECT nome FROM produtos", conn)

    if produtos.empty:
        st.warning("Cadastre produtos antes de registrar vendas.")
    else:
        produto = st.selectbox("Produto", produtos["nome"])
        quantidade = st.number_input("Quantidade vendida", min_value=1, step=1)
        preco = st.number_input("Preço de venda (R$)", min_value=0.0, step=0.01)
        percentual = st.number_input("Percentual a receber (%)", min_value=0.0, step=0.1)

        metodo_pagamento = st.radio(
            "Método de pagamento",
            ["Pix", "Cartão"]
        )

        if metodo_pagamento == "Cartão":
            parcelas = st.number_input("Número de parcelas", min_value=1, step=1)
        else:
            parcelas = 1
            st.info("Pagamento via Pix (1 parcela)")

        data_venda = st.date_input("Data da venda", value=date.today())

        valor_receber = quantidade * preco * (percentual / 100)

        st.info(f"Valor a receber: R$ {valor_receber:.2f}")

        if st.button("Registrar venda"):
            cur.execute("""
                INSERT INTO vendas
                (produto, quantidade, preco, percentual, valor_receber,
                 metodo_pagamento, parcelas, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                produto,
                quantidade,
                preco,
                percentual,
                valor_receber,
                metodo_pagamento,
                parcelas,
                data_venda.isoformat()
            ))
            conn.commit()
            st.success("Venda registrada com sucesso.")

# =================================================
# RELATÓRIOS
# =================================================
elif pagina == "Relatórios":

    st.title("Relatório de vendas")

    vendas = pd.read_sql("SELECT * FROM vendas", conn)

    if vendas.empty:
        st.warning("Nenhuma venda registrada.")
    else:
        vendas["data"] = pd.to_datetime(vendas["data"])

        produto_filtro = st.multiselect(
            "Filtrar por produto",
            vendas["produto"].unique()
        )

        metodo_filtro = st.multiselect(
            "Filtrar por método de pagamento",
            vendas["metodo_pagamento"].unique()
        )

        data_ini, data_fim = st.date_input(
            "Filtrar por período",
            [vendas["data"].min(), vendas["data"].max()]
        )

        if produto_filtro:
            vendas = vendas[vendas["produto"].isin(produto_filtro)]

        if metodo_filtro:
            vendas = vendas[vendas["metodo_pagamento"].isin(metodo_filtro)]

        vendas = vendas[
            (vendas["data"] >= pd.to_datetime(data_ini)) &
            (vendas["data"] <= pd.to_datetime(data_fim))
        ]

        total_qtd = vendas["quantidade"].sum()
        total_vendido = (vendas["quantidade"] * vendas["preco"]).sum()
        total_receber = vendas["valor_receber"].sum()

        st.markdown(f"""
        **Total de produtos vendidos:** {total_qtd}  
        **Valor total vendido:** R$ {total_vendido:.2f}  
        **Valor total a receber:** R$ {total_receber:.2f}
        """)

        st.subheader("Lista de vendas")
        st.dataframe(
            vendas[[
                "produto",
                "quantidade",
                "preco",
                "metodo_pagamento",
                "parcelas",
                "valor_receber",
                "data"
            ]],
            use_container_width=True
        )

        st.subheader("Excluir venda")
        vid = st.selectbox("Selecione a venda", vendas["id"])

        if st.button("Excluir venda"):
            cur.execute("DELETE FROM vendas WHERE id=?", (vid,))
            conn.commit()
            st.success("Venda excluída.")
            st.rerun()

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            vendas.to_excel(writer, index=False)

        st.download_button(
            "Exportar relatório para Excel",
            buffer,
            "relatorio_vendas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
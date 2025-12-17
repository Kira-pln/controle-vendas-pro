import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import plotly.express as px
import io

# -------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -------------------------------------------------
st.set_page_config(
    page_title="Controle de Vendas Pro",
    page_icon="📊",
    layout="wide"
)

# -------------------------------------------------
# ESTILO CUSTOMIZADO
# -------------------------------------------------
st.markdown("""
<style>
.metric-card {
    background-color: #0f172a;
    padding: 20px;
    border-radius: 12px;
    color: white;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# CONEXÃO COM BANCO DE DADOS
# -------------------------------------------------
conn = sqlite3.connect("vendas.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    descricao TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto TEXT,
    quantidade INTEGER,
    preco REAL,
    percentual REAL,
    valor_receber REAL,
    data TEXT
)
""")

conn.commit()

# -------------------------------------------------
# MENU LATERAL
# -------------------------------------------------
st.sidebar.title("📋 Menu")
pagina = st.sidebar.radio(
    "Navegação",
    ["Cadastro de produtos", "Registrar venda", "Relatórios"]
)

# =================================================
# PÁGINA — CADASTRO DE PRODUTOS
# =================================================
if pagina == "Cadastro de produtos":

    st.title("📦 Cadastro de produtos")

    col1, col2 = st.columns(2)

    with col1:
        nome = st.text_input("Nome do produto")
    with col2:
        descricao = st.text_input("Descrição")

    if st.button("Cadastrar produto"):
        if nome.strip() == "":
            st.warning("Informe o nome do produto.")
        else:
            cursor.execute(
                "INSERT INTO produtos (nome, descricao) VALUES (?, ?)",
                (nome, descricao)
            )
            conn.commit()
            st.success("Produto cadastrado com sucesso.")

    produtos = pd.read_sql("SELECT * FROM produtos", conn)
    st.subheader("Produtos cadastrados")
    st.dataframe(produtos[["nome", "descricao"]], use_container_width=True)

# =================================================
# PÁGINA — REGISTRAR VENDA
# =================================================
elif pagina == "Registrar venda":

    st.title("🛒 Registrar venda")

    produtos = pd.read_sql("SELECT nome FROM produtos", conn)

    if produtos.empty:
        st.warning("Cadastre produtos antes de registrar vendas.")
    else:
        produto = st.selectbox("Produto", produtos["nome"])

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            quantidade = st.number_input("Quantidade", min_value=1, step=1)

        with col2:
            preco = st.number_input("Preço de venda (R$)", min_value=0.0, step=0.01)

        with col3:
            percentual = st.number_input("Percentual a receber (%)", min_value=0.0, step=0.1)

        with col4:
            data_venda = st.date_input("Data", value=date.today())

        valor_receber = quantidade * preco * (percentual / 100)

        st.info(f"Valor a receber: R$ {valor_receber:.2f}")

        if st.button("Registrar venda"):
            cursor.execute("""
                INSERT INTO vendas
                (produto, quantidade, preco, percentual, valor_receber, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                produto,
                quantidade,
                preco,
                percentual,
                valor_receber,
                data_venda.isoformat()
            ))
            conn.commit()
            st.success("Venda registrada com sucesso.")

# =================================================
# PÁGINA — RELATÓRIOS
# =================================================
elif pagina == "Relatórios":

    st.title("📊 Relatórios e análises")

    vendas = pd.read_sql("SELECT * FROM vendas", conn)

    if vendas.empty:
        st.warning("Nenhuma venda registrada.")
    else:
        vendas["data"] = pd.to_datetime(vendas["data"])

        # ---------------- FILTROS ----------------
        col1, col2 = st.columns(2)

        with col1:
            produto_filtro = st.multiselect(
                "Filtrar por produto",
                vendas["produto"].unique()
            )

        with col2:
            data_ini, data_fim = st.date_input(
                "Filtrar por período",
                [vendas["data"].min(), vendas["data"].max()]
            )

        if produto_filtro:
            vendas = vendas[vendas["produto"].isin(produto_filtro)]

        vendas = vendas[
            (vendas["data"] >= pd.to_datetime(data_ini)) &
            (vendas["data"] <= pd.to_datetime(data_fim))
        ]

        # ---------------- MÉTRICAS ----------------
        total_qtd = vendas["quantidade"].sum()
        total_vendido = (vendas["quantidade"] * vendas["preco"]).sum()
        total_receber = vendas["valor_receber"].sum()

        col1, col2, col3 = st.columns(3)

        col1.metric("Total de produtos", total_qtd)
        col2.metric("Total vendido (R$)", f"{total_vendido:.2f}")
        col3.metric("Total a receber (R$)", f"{total_receber:.2f}")

        # ---------------- GRÁFICO ----------------
        grafico = px.bar(
            vendas,
            x="produto",
            y="quantidade",
            title="Quantidade vendida por produto"
        )

        st.plotly_chart(grafico, use_container_width=True)

        # ---------------- TABELA ----------------
        st.subheader("Detalhamento das vendas")
        st.dataframe(
            vendas[[
                "produto", "quantidade", "preco",
                "percentual", "valor_receber", "data"
            ]],
            use_container_width=True
        )

        # ---------------- EXPORTAÇÃO ----------------
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            vendas.to_excel(writer, index=False)

        st.download_button(
            "Exportar relatório para Excel",
            buffer,
            "relatorio_vendas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

# -------------------------------------------------
# CONFIGURAÇÃO
# -------------------------------------------------
st.set_page_config(
    page_title="Inova Eletro Móveis",
    layout="centered"
)

# -------------------------------------------------
# ESTILO + TÍTULO FIXO
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
    padding-top: 90px;
}
</style>

<div class="main-title">Inova Eletro Móveis</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# BANCO DE DADOS
# -------------------------------------------------
conn = sqlite3.connect("vendas.db", check_same_thread=False)
cur = conn.cursor()

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
# GARANTIR COLUNAS (EVITA KeyError)
# -------------------------------------------------
cur.execute("PRAGMA table_info(vendas)")
colunas_existentes = [col[1] for col in cur.fetchall()]

colunas_necessarias = {
    "produto": "TEXT",
    "quantidade": "INTEGER",
    "preco": "REAL",
    "percentual": "REAL",
    "valor_receber": "REAL",
    "metodo_pagamento": "TEXT",
    "parcelas": "INTEGER",
    "data": "TEXT"
}

for coluna, tipo in colunas_necessarias.items():
    if coluna not in colunas_existentes:
        cur.execute(f"ALTER TABLE vendas ADD COLUMN {coluna} {tipo}")

conn.commit()

# -------------------------------------------------
# MENU
# -------------------------------------------------
pagina = st.radio(
    "Menu",
    ["Cadastro de produtos", "Registrar venda", "Relatórios"]
)

st.divider()

# =================================================
# CADASTRO DE PRODUTOS
# =================================================
if pagina == "Cadastro de produtos":

    st.subheader("Cadastro de produtos")

    nome = st.text_input("Nome do produto")
    descricao = st.text_input("Descrição do produto")

    if st.button("Cadastrar produto"):
        if nome.strip():
            cur.execute(
                "INSERT INTO produtos (nome, descricao) VALUES (?, ?)",
                (nome, descricao)
            )
            conn.commit()
            st.success("Produto cadastrado com sucesso.")
        else:
            st.warning("Informe o nome do produto.")

    produtos = pd.read_sql("SELECT * FROM produtos", conn)
    st.dataframe(produtos, use_container_width=True)

    if not produtos.empty:
        pid = st.selectbox(
            "Excluir produto",
            produtos["id"],
            format_func=lambda x: produtos.loc[produtos["id"] == x, "nome"].values[0]
        )

        if st.button("Excluir produto"):
            cur.execute("DELETE FROM produtos WHERE id=?", (pid,))
            conn.commit()
            st.rerun()

# =================================================
# REGISTRAR VENDA
# =================================================
elif pagina == "Registrar venda":

    st.subheader("Registrar venda")

    produtos = pd.read_sql("SELECT nome FROM produtos", conn)

    if produtos.empty:
        st.warning("Cadastre produtos antes de registrar vendas.")
    else:
        produto = st.selectbox("Produto", produtos["nome"])
        quantidade = st.number_input("Quantidade", min_value=1, step=1)
        preco = st.number_input("Preço (R$)", min_value=0.0, step=0.01)
        percentual = st.number_input("Percentual a receber (%)", min_value=0.0, step=0.1)

        metodo_pagamento = st.radio("Método de pagamento", ["Pix", "Cartão"])

        parcelas = 1
        if metodo_pagamento == "Cartão":
            parcelas = st.number_input("Parcelas", min_value=1, step=1)

        data_venda = st.date_input("Data", value=date.today())

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

    st.subheader("Relatório de vendas")

    vendas = pd.read_sql("SELECT * FROM vendas", conn)

    if vendas.empty:
        st.warning("Nenhuma venda registrada.")
    else:
        vendas["data"] = pd.to_datetime(vendas["data"], errors="coerce")

        total_vendido = (vendas["quantidade"] * vendas["preco"]).sum()
        total_receber = vendas["valor_receber"].sum()

        st.markdown(f"""
        **Total vendido:** R$ {total_vendido:.2f}  
        **Valor a receber:** R$ {total_receber:.2f}
        """)

        colunas_exibir = [
            "produto",
            "quantidade",
            "preco",
            "metodo_pagamento",
            "parcelas",
            "valor_receber",
            "data"
        ]

        st.dataframe(vendas[colunas_exibir], use_container_width=True)

        vid = st.selectbox("Excluir venda", vendas["id"])
        if st.button("Excluir venda"):
            cur.execute("DELETE FROM vendas WHERE id=?", (vid,))
            conn.commit()
            st.rerun()

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            vendas.to_excel(writer, index=False)

        st.download_button(
            "Exportar para Excel",
            buffer,
            "relatorio_vendas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
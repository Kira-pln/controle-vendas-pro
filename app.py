import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import plotly.express as px
import io
import hashlib

# -------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (MOBILE-FIRST)
# -------------------------------------------------
st.set_page_config(
    page_title="Controle de Vendas",
    layout="centered"
)

# -------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def conectar_db():
    return sqlite3.connect("vendas.db", check_same_thread=False)

conn = conectar_db()
cursor = conn.cursor()

# -------------------------------------------------
# CRIAÇÃO DAS TABELAS
# -------------------------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    senha TEXT
)
""")

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
# USUÁRIO PADRÃO (ADMIN)
# -------------------------------------------------
cursor.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
if cursor.fetchone() is None:
    cursor.execute(
        "INSERT INTO usuarios (usuario, senha) VALUES (?, ?)",
        ("admin", hash_senha("admin"))
    )
    conn.commit()

# -------------------------------------------------
# LOGIN
# -------------------------------------------------
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND senha = ?",
            (usuario, hash_senha(senha))
        )
        if cursor.fetchone():
            st.session_state.logado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")

    st.stop()

# -------------------------------------------------
# MENU
# -------------------------------------------------
st.sidebar.title("Menu")
pagina = st.sidebar.radio(
    "Navegação",
    ["Cadastro de produtos", "Registrar venda", "Relatórios", "Sair"]
)

# -------------------------------------------------
# SAIR
# -------------------------------------------------
if pagina == "Sair":
    st.session_state.logado = False
    st.rerun()

# =================================================
# CADASTRO DE PRODUTOS
# =================================================
if pagina == "Cadastro de produtos":

    st.title("Cadastro de produtos")

    nome = st.text_input("Nome do produto")
    descricao = st.text_input("Descrição")

    if st.button("Cadastrar"):
        if nome.strip() == "":
            st.warning("Informe o nome do produto.")
        else:
            cursor.execute(
                "INSERT INTO produtos (nome, descricao) VALUES (?, ?)",
                (nome, descricao)
            )
            conn.commit()
            st.success("Produto cadastrado.")

    produtos = pd.read_sql("SELECT * FROM produtos", conn)

    st.subheader("Produtos cadastrados")
    st.dataframe(produtos[["id", "nome", "descricao"]], use_container_width=True)

    st.subheader("Excluir produto")
    if not produtos.empty:
        produto_excluir = st.selectbox(
            "Selecione o produto",
            produtos["id"],
            format_func=lambda x: produtos.loc[produtos["id"] == x, "nome"].values[0]
        )

        if st.button("Excluir produto"):
            cursor.execute("DELETE FROM produtos WHERE id = ?", (produto_excluir,))
            cursor.execute("DELETE FROM vendas WHERE produto = (SELECT nome FROM produtos WHERE id = ?)", (produto_excluir,))
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
        st.warning("Cadastre produtos antes.")
    else:
        produto = st.selectbox("Produto", produtos["nome"])

        quantidade = st.number_input("Quantidade", min_value=1, step=1)
        preco = st.number_input("Preço de venda (R$)", min_value=0.0, step=0.01)
        percentual = st.number_input("Percentual a receber (%)", min_value=0.0, step=0.1)
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
            st.success("Venda registrada.")

# =================================================
# RELATÓRIOS
# =================================================
elif pagina == "Relatórios":

    st.title("Relatórios")

    vendas = pd.read_sql("SELECT * FROM vendas", conn)

    if vendas.empty:
        st.warning("Nenhuma venda registrada.")
    else:
        vendas["data"] = pd.to_datetime(vendas["data"])

        produto_filtro = st.multiselect(
            "Filtrar por produto",
            vendas["produto"].unique()
        )

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

        total_qtd = vendas["quantidade"].sum()
        total_vendido = (vendas["quantidade"] * vendas["preco"]).sum()
        total_receber = vendas["valor_receber"].sum()

        st.markdown(f"""
        **Total de produtos vendidos:** {total_qtd}  
        **Valor total vendido:** R$ {total_vendido:.2f}  
        **Valor total a receber:** R$ {total_receber:.2f}
        """)

        grafico = px.bar(
            vendas,
            x="produto",
            y="quantidade"
        )

        st.plotly_chart(grafico, use_container_width=True)

        st.subheader("Vendas registradas")
        st.dataframe(vendas, use_container_width=True)

        st.subheader("Excluir venda")
        venda_excluir = st.selectbox(
            "Selecione a venda",
            vendas["id"]
        )

        if st.button("Excluir venda"):
            cursor.execute("DELETE FROM vendas WHERE id = ?", (venda_excluir,))
            conn.commit()
            st.success("Venda excluída.")
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


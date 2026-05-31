import streamlit as st
import sqlite3
import bcrypt
import pandas as pd

# --- CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="ItaGesso Gestão", layout="wide")

def init_db():
    conn = sqlite3.connect('itagesso.db')
    cursor = conn.cursor()
    # Tabela de Estoque
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       produto TEXT, categoria TEXT, quantidade REAL, 
                       preco_compra REAL, preco_venda REAL)''')
    # Tabela de Movimentações
    cursor.execute('''CREATE TABLE IF NOT EXISTS movimentacoes
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       produto TEXT, tipo TEXT, quantidade REAL, 
                       valor_total REAL, data DATE)''')
    conn.commit()
    conn.close()

init_db()

# --- SEGURANÇA ---
def check_password(password):
    # Pega o hash salvo no secrets.toml (precisa estar na pasta .streamlit)
    if "ADMIN_PASSWORD_HASH" in st.secrets:
        stored_hash = st.secrets["ADMIN_PASSWORD_HASH"].encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
    return False

# --- LÓGICA DO SISTEMA ---
def get_connection():
    return sqlite3.connect('itagesso.db')

# --- INTERFACE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🔐 ItaGesso - Acesso")
    pwd = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if check_password(pwd):
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Senha inválida!")
else:
    st.sidebar.title("Navegação ItaGesso")
    page = st.sidebar.radio("Ir para:", ["Dashboard", "Estoque", "Vendas/Compras"])
    
    if st.sidebar.button("Sair"):
        st.session_state["logged_in"] = False
        st.rerun()

    # --- PÁGINAS ---
    if page == "Dashboard":
        st.title("📊 Resumo ItaGesso")
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM estoque", conn)
        st.dataframe(df)
        conn.close()

    elif page == "Estoque":
        st.title("📦 Controle de Estoque")
        # Formulário para novo produto
        with st.form("novo_produto"):
            nome = st.text_input("Nome do Material")
            cat = st.selectbox("Categoria", ["Gesso", "Drywall", "Estrutura", "Parafusos", "Acabamento"])
            qtd = st.number_input("Quantidade Inicial", min_value=0.0)
            p_compra = st.number_input("Preço de Compra", min_value=0.0)
            p_venda = st.number_input("Preço de Venda", min_value=0.0)
            if st.form_submit_button("Cadastrar"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (?,?,?,?,?)", 
                               (nome, cat, qtd, p_compra, p_venda))
                conn.commit()
                conn.close()
                st.success("Material cadastrado!")

    elif page == "Vendas/Compras":
        st.title("💸 Vendas e Compras")
        # Simples registro de movimentação
        tipo = st.selectbox("Tipo", ["Venda", "Compra"])
        produto = st.text_input("Nome do Produto")
        qtd = st.number_input("Quantidade")
        valor = st.number_input("Valor Total")
        
        if st.button("Registrar Movimentação"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO movimentacoes (produto, tipo, quantidade, valor_total, data) VALUES (?,?,?,?, date('now'))", 
                           (produto, tipo, qtd, valor))
            conn.commit()
            conn.close()
            st.success("Registrado com sucesso!")

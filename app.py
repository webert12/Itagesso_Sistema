import streamlit as st
import sqlite3
import pandas as pd

# --- CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="ItaGesso Gestão", layout="wide")

def init_db():
    conn = sqlite3.connect('itagesso.db', check_same_thread=False)
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
    return conn

conn = init_db()

# --- NAVEGAÇÃO ---
st.sidebar.title("ItaGesso - Menu")
page = st.sidebar.radio("Navegação", ["Dashboard", "Estoque", "Vendas/Compras"])

# --- LÓGICA DO SISTEMA ---
if page == "Dashboard":
    st.title("📊 Painel Geral")
    df = pd.read_sql("SELECT * FROM estoque", conn)
    st.dataframe(df)

elif page == "Estoque":
    st.title("📦 Cadastro de Materiais")
    with st.form("form_estoque"):
        nome = st.text_input("Nome do Material")
        cat = st.selectbox("Categoria", ["Gesso", "Drywall", "Estrutura", "Parafusos", "Acabamento"])
        qtd = st.number_input("Quantidade Inicial", min_value=0.0)
        p_compra = st.number_input("Preço de Compra", min_value=0.0)
        p_venda = st.number_input("Preço de Venda", min_value=0.0)
        
        if st.form_submit_button("Cadastrar"):
            cursor = conn.cursor()
            cursor.execute("INSERT INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (?,?,?,?,?)", 
                           (nome, cat, qtd, p_compra, p_venda))
            conn.commit()
            st.success(f"{nome} cadastrado com sucesso!")

elif page == "Vendas/Compras":
    st.title("💸 Vendas e Compras")
    tipo = st.selectbox("Tipo de Movimentação", ["Venda", "Compra"])
    produto = st.text_input("Nome do Produto")
    qtd = st.number_input("Quantidade", min_value=0.0)
    valor = st.number_input("Valor Total", min_value=0.0)
    
    if st.button("Registrar"):
        cursor = conn.cursor()
        cursor.execute("INSERT INTO movimentacoes (produto, tipo, quantidade, valor_total, data) VALUES (?,?,?,?, date('now'))", 
                       (produto, tipo, qtd, valor))
        # Atualiza o estoque automaticamente (simplificado)
        if tipo == "Venda":
            cursor.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE produto = ?", (qtd, produto))
        else:
            cursor.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE produto = ?", (qtd, produto))
        
        conn.commit()
        st.success("Movimentação registrada e estoque atualizado!")

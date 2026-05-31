import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="ItaGesso Gestão", layout="wide")

def get_connection():
    return sqlite3.connect('itagesso.db', check_same_thread=False)

# --- INICIALIZAÇÃO DO BANCO ---
conn = get_connection()
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS estoque 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   produto TEXT UNIQUE, categoria TEXT, quantidade REAL, 
                   preco_compra REAL, preco_venda REAL)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS movimentacoes
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   produto TEXT, tipo TEXT, quantidade REAL, 
                   valor_total REAL, data DATE)''')
conn.commit()
conn.close()

# --- LÓGICA DO DASHBOARD ---
def show_dashboard():
    st.title("📊 Painel ItaGesso")
    conn = get_connection()
    df_mov = pd.read_sql("SELECT * FROM movimentacoes", conn)
    df_estoque = pd.read_sql("SELECT * FROM estoque", conn)
    conn.close()
    
    # Métricas
    total_vendas = df_mov[df_mov['tipo'] == 'Venda']['valor_total'].sum()
    total_compras = df_mov[df_mov['tipo'] == 'Compra']['valor_total'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Receita Total", f"R$ {total_vendas:,.2f}")
    c2.metric("Despesas Totais", f"R$ {total_compras:,.2f}")
    c3.metric("Saldo Estimado", f"R$ {total_vendas - total_compras:,.2f}")
    
    if not df_estoque.empty:
        fig = px.pie(df_estoque, values='quantidade', names='categoria', title="Composição do Estoque")
        st.plotly_chart(fig, use_container_width=True)

# --- PÁGINA ESTOQUE (COM ABAS) ---
def page_estoque():
    st.title("📦 Controle de Materiais")
    tab1, tab2 = st.tabs(["📋 Estoque Atual", "➕ Cadastrar Novo Produto"])
    
    with tab1:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM estoque", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum material cadastrado.")

    with tab2:
        with st.form("form_novo"):
            nome = st.text_input("Nome do Material (Ex: Gesso Cola)")
            cat = st.selectbox("Categoria", ["Gesso", "Drywall", "Estrutura", "Parafusos", "Acabamento"])
            qtd = st.number_input("Quantidade Inicial", min_value=0.0)
            p_compra = st.number_input("Preço de Compra", min_value=0.0)
            p_venda = st.number_input("Preço de Venda", min_value=0.0)
            if st.form_submit_button("Salvar no Estoque"):
                conn = get_connection()
                try:
                    conn.execute("INSERT INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (?,?,?,?,?)", 
                                 (nome, cat, qtd, p_compra, p_venda))
                    conn.commit()
                    st.success("Produto cadastrado!")
                    st.rerun()
                except:
                    st.error("Erro: Este produto já existe no estoque.")
                conn.close()

# --- PÁGINA VENDAS/COMPRAS ---
def page_transacoes():
    st.title("💸 Vendas e Compras")
    conn = get_connection()
    produtos = pd.read_sql("SELECT produto FROM estoque", conn)['produto'].tolist()
    
    if not produtos:
        st.warning("Cadastre algum produto no Estoque primeiro!")
    else:
        tipo = st.selectbox("Tipo", ["Venda", "Compra"])
        prod_selecionado = st.selectbox("Selecione o Produto", produtos)
        qtd = st.number_input("Quantidade", min_value=0.1)
        valor = st.number_input("Valor Total da Operação (R$)", min_value=0.0)
        
        if st.button("Confirmar Movimentação"):
            cursor = conn.cursor()
            # Registra movimento
            cursor.execute("INSERT INTO movimentacoes (produto, tipo, quantidade, valor_total, data) VALUES (?,?,?,?, date('now'))", 
                           (prod_selecionado, tipo, qtd, valor))
            # Atualiza estoque
            if tipo == "Venda":
                cursor.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE produto = ?", (qtd, prod_selecionado))
            else:
                cursor.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE produto = ?", (qtd, prod_selecionado))
            
            conn.commit()
            st.success(f"Estoque atualizado para {prod_selecionado}!")
            st.rerun()
    conn.close()

# --- MENU LATERAL ---
menu = st.sidebar.radio("Navegação", ["Dashboard", "Estoque", "Vendas/Compras"])
if menu == "Dashboard": show_dashboard()
elif menu == "Estoque": page_estoque()
elif menu == "Vendas/Compras": page_transacoes()

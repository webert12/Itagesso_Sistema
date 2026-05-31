import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="ItaGesso Dashboard", layout="wide")

def get_connection():
    return sqlite3.connect('itagesso.db', check_same_thread=False)

# --- DASHBOARD E CÁLCULOS ---
def show_dashboard():
    st.title("📊 Painel ItaGesso")
    conn = get_connection()
    
    # Busca dados
    df_mov = pd.read_sql("SELECT * FROM movimentacoes", conn)
    df_estoque = pd.read_sql("SELECT * FROM estoque", conn)
    
    # Cálculos Financeiros
    total_vendas = df_mov[df_mov['tipo'] == 'Venda']['valor_total'].sum() if not df_mov.empty else 0
    total_compras = df_mov[df_mov['tipo'] == 'Compra']['valor_total'].sum() if not df_mov.empty else 0
    saldo = total_vendas - total_compras
    
    # Layout de Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Vendas (Receita)", f"R$ {total_vendas:,.2f}")
    c2.metric("Total Compras (Despesas)", f"R$ {total_compras:,.2f}")
    c3.metric("Saldo (Lucro Estimado)", f"R$ {saldo:,.2f}", delta_color="normal")
    
    st.markdown("---")
    
    # Gráfico de Pizza
    if not df_estoque.empty:
        st.subheader("Distribuição do Estoque por Categoria")
        fig = px.pie(df_estoque, values='quantidade', names='categoria', 
                     title="Proporção de Materiais em Estoque")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Cadastre materiais para ver o gráfico de estoque.")
    
    conn.close()

# --- NAVEGAÇÃO ---
st.sidebar.title("ItaGesso Menu")
page = st.sidebar.radio("Navegação", ["Dashboard", "Estoque", "Vendas/Compras"])

if page == "Dashboard":
    show_dashboard()
elif page == "Estoque":
    st.title("📦 Cadastro de Materiais")
    with st.form("novo_produto"):
        nome = st.text_input("Nome do Material")
        cat = st.selectbox("Categoria", ["Gesso", "Drywall", "Estrutura", "Parafusos", "Acabamento"])
        qtd = st.number_input("Quantidade", min_value=0.0)
        p_compra = st.number_input("Preço de Compra", min_value=0.0)
        p_venda = st.number_input("Preço de Venda", min_value=0.0)
        if st.form_submit_button("Cadastrar"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (?,?,?,?,?)", 
                           (nome, cat, qtd, p_compra, p_venda))
            conn.commit()
            conn.close()
            st.success("Cadastrado!")
            st.rerun()

elif page == "Vendas/Compras":
    st.title("💸 Vendas e Compras")
    tipo = st.selectbox("Tipo", ["Venda", "Compra"])
    produto = st.text_input("Nome do Produto")
    qtd = st.number_input("Quantidade", min_value=0.0)
    valor = st.number_input("Valor Total (R$)", min_value=0.0)
    
    if st.button("Registrar"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO movimentacoes (produto, tipo, quantidade, valor_total, data) VALUES (?,?,?,?, date('now'))", 
                       (produto, tipo, qtd, valor))
        
        if tipo == "Venda":
            cursor.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE produto = ?", (qtd, produto))
        else:
            cursor.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE produto = ?", (qtd, produto))
        
        conn.commit()
        conn.close()
        st.success("Movimentação registrada!")
        st.rerun()

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- CONFIGURAÇÃO E CSS DE LIMPEZA ---
st.set_page_config(page_title="ItaGesso Gestão", layout="wide", page_icon="🏗️")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="stSidebar"] {display: none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

def get_connection():
    return sqlite3.connect('itagesso.db', check_same_thread=False)

# --- INICIALIZAÇÃO DO BANCO ---
def init_db():
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

init_db()

# --- MENU SUPERIOR ---
menu = st.radio("Navegação", ["Dashboard", "Estoque", "Vendas/Compras", "Configurações"], horizontal=True, label_visibility="collapsed")
st.markdown("---")

# --- DASHBOARD ---
def show_dashboard():
    st.markdown("# 🏛️ ItaGesso | Painel de Controle")
    conn = get_connection()
    df_mov = pd.read_sql("SELECT * FROM movimentacoes", conn)
    df_estoque = pd.read_sql("SELECT * FROM estoque", conn)
    conn.close()
    
    if not df_mov.empty:
        df_mov['data'] = pd.to_datetime(df_mov['data'])
        df_mov['mes_ano'] = df_mov['data'].dt.strftime('%Y-%m')
        meses_disponiveis = sorted(df_mov['mes_ano'].unique(), reverse=True)
        mes_selecionado = st.selectbox("📅 Selecione o mês para análise:", meses_disponiveis, index=0)
        
        df_filtrado = df_mov[df_mov['mes_ano'] == mes_selecionado]
        total_vendas = df_filtrado[df_filtrado['tipo'] == 'Venda']['valor_total'].sum()
        total_compras = df_filtrado[df_filtrado['tipo'] == 'Compra']['valor_total'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Receita", f"R$ {total_vendas:,.2f}")
        c2.metric("💸 Despesas", f"R$ {total_compras:,.2f}")
        c3.metric("📈 Saldo", f"R$ {total_vendas - total_compras:,.2f}")
        
        with st.expander("📂 Ver Histórico Detalhado do Mês"):
            st.dataframe(df_filtrado[['data', 'produto', 'tipo', 'quantidade', 'valor_total']], use_container_width=True)
    else:
        st.info("Nenhuma movimentação registrada.")

    if not df_estoque.empty:
        st.markdown("### 📊 Estoque Atual")
        df_chart = df_estoque[df_estoque['quantidade'] > 0].copy()
        if not df_chart.empty:
            df_chart = df_chart.groupby('categoria')['quantidade'].sum().reset_index()
            fig = px.pie(df_chart, values='quantidade', names='categoria', hole=0.3)
            st.plotly_chart(fig, use_container_width=True)

# --- ESTOQUE E TRANSAÇÕES (MANTIDAS IGUAIS) ---
def page_estoque():
    st.markdown("# 📦 Controle de Materiais")
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM estoque", conn)
    conn.close()
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Estoque Atual", "➕ Cadastro", "📥 Importação", "✏️ Edição"])
    with tab1:
        if not df.empty:
            edited_df = st.data_editor(df, column_config={"id": None, "quantidade": st.column_config.ProgressColumn("Estoque Atual", format="%d", min_value=0, max_value=500)}, use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Alterações"):
                conn = get_connection()
                cursor = conn.cursor()
                for _, row in edited_df.iterrows():
                    cursor.execute('''UPDATE estoque SET produto=?, categoria=?, quantidade=?, preco_compra=?, preco_venda=? WHERE id=?''', (row['produto'], row['categoria'], row['quantidade'], row['preco_compra'], row['preco_venda'], row['id']))
                conn.commit()
                conn.close()
                st.rerun()
    with tab2:
        with st.container(border=True):
            st.subheader("🧱 Novo Produto")
            with st.form("form_novo"):
                nome = st.text_input("Nome do Material")
                cat = st.selectbox("Categoria", ["Gesso", "Drywall", "Estrutura", "Parafusos", "Acabamento"])
                qtd = st.number_input("Quantidade Inicial", min_value=0, step=1)
                p_compra = st.number_input("Preço de Compra", min_value=0.0, format="%.2f")
                p_venda = st.number_input("Preço de Venda", min_value=0.0, format="%.2f")
                if st.form_submit_button("Salvar"):
                    conn = get_connection()
                    try:
                        conn.execute("INSERT INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (?,?,?,?,?)", (nome, cat, qtd, p_compra, p_venda))
                        conn.commit()
                        st.rerun()
                    except: st.error("Erro: Produto já existe.")
                    conn.close()
    with tab3:
        with st.container(border=True):
            st.subheader("📥 Importação em Lote")
            texto_colado = st.text_area("Formato: nome,categoria,quantidade,preco_compra,preco_venda", height=150)
            if st.button("Processar Dados"):
                if texto_colado:
                    conn = get_connection()
                    for linha in texto_colado.strip().split('\n'):
                        p = [x.strip() for x in linha.split(',')]
                        if len(p) == 5: conn.execute("INSERT OR REPLACE INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (?,?,?,?,?)", (p[0], p[1], float(p[2]), float(p[3]), float(p[4])))
                    conn.commit()
                    conn.close()
                    st.rerun()
    with tab4:
        with st.container(border=True):
            st.subheader("✏️ Edição Detalhada")
            if not df.empty:
                lista_produtos = df['produto'].tolist()
                selecionado = st.selectbox("Escolha o produto para editar", lista_produtos)
                dados_prod = df[df['produto'] == selecionado].iloc[0]
                with st.form("form_edicao"):
                    n_nome = st.text_input("Nome", value=dados_prod['produto'])
                    n_qtd = st.number_input("Quantidade", value=int(dados_prod['quantidade']), step=1)
                    if st.form_submit_button("Atualizar"):
                        conn = get_connection()
                        conn.execute("UPDATE estoque SET produto=?, quantidade=? WHERE id=?", (n_nome, n_qtd, int(dados_prod['id'])))
                        conn.commit()
                        conn.close()
                        st.rerun()

def page_transacoes():
    st.markdown("# 🛒 Movimentações")
    conn = get_connection()
    df_estoque = pd.read_sql("SELECT * FROM estoque", conn)
    produtos = df_estoque['produto'].tolist()
    if not produtos:
        st.warning("Cadastre algum produto no Estoque primeiro!")
    else:
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                tipo = st.selectbox("Tipo de Operação", ["Venda", "Compra"])
                prod_selecionado = st.selectbox("Material", produtos)
            with col2:
                qtd = st.number_input("Quantidade", min_value=1, step=1, format="%d")
                preco_unitario = st.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f")
            estoque_atual = df_estoque[df_estoque['produto'] == prod_selecionado]['quantidade'].iloc[0]
            if tipo == "Venda" and qtd > estoque_atual:
                st.error(f"❌ Estoque Insuficiente! Disponível: {estoque_atual} unidades.")
            else:
                total_calculado = qtd * preco_unitario
                st.metric("Valor Total", f"R$ {total_calculado:,.2f}")
                if st.button("✅ Confirmar Operação"):
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO movimentacoes (produto, tipo, quantidade, valor_total, data) VALUES (?,?,?,?, date('now'))", (prod_selecionado, tipo, qtd, total_calculado))
                    if tipo == "Venda": cursor.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE produto = ?", (qtd, prod_selecionado))
                    else: cursor.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE produto = ?", (qtd, prod_selecionado))
                    conn.commit()
                    conn.close()
                    st.success("Operação concluída!")
                    st.rerun()
    conn.close()

# --- CONFIGURAÇÕES E RESET ---
def page_configuracoes():
    st.markdown("# ⚙️ Configurações do Sistema")
    st.markdown("---")
    
    st.subheader("🚨 Área de Risco")
    st.warning("Ao clicar no botão abaixo, todo o histórico de vendas, compras e estoque será apagado permanentemente.")
    
    if st.button("🔴 Apagar Todos os Dados e Reiniciar Sistema"):
        conn = get_connection()
        conn.execute("DROP TABLE estoque")
        conn.execute("DROP TABLE movimentacoes")
        conn.commit()
        conn.close()
        st.success("Sistema resetado com sucesso! Recarregando...")
        st.rerun()

# --- LÓGICA DE NAVEGAÇÃO ---
if menu == "Dashboard": show_dashboard()
elif menu == "Estoque": page_estoque()
elif menu == "Vendas/Compras": page_transacoes()
elif menu == "Configurações": page_configuracoes()

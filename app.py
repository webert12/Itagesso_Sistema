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

# --- DASHBOARD ---
def show_dashboard():
    st.title("📊 Painel ItaGesso")
    conn = get_connection()
    df_mov = pd.read_sql("SELECT * FROM movimentacoes", conn)
    df_estoque = pd.read_sql("SELECT * FROM estoque", conn)
    conn.close()
    
    # Cálculos
    total_vendas = df_mov[df_mov['tipo'] == 'Venda']['valor_total'].sum()
    total_compras = df_mov[df_mov['tipo'] == 'Compra']['valor_total'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Receita Total", f"R$ {total_vendas:,.2f}")
    c2.metric("Despesas Totais", f"R$ {total_compras:,.2f}")
    c3.metric("Saldo Estimado", f"R$ {total_vendas - total_compras:,.2f}")
    
    if not df_estoque.empty:
        st.subheader("Distribuição do Estoque")
        fig = px.pie(df_estoque, values='quantidade', names='categoria', title="Composição do Estoque por Categoria")
        st.plotly_chart(fig, use_container_width=True)

# --- ESTOQUE (COM ABAS) ---
def page_estoque():
    st.title("📦 Controle de Materiais")
    
    tab1, tab2, tab3 = st.tabs(["📋 Estoque Atual", "➕ Cadastrar Novo", "📥 Importar/Exportar"])
    
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
            nome = st.text_input("Nome do Material")
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
                    st.error("Erro: Este produto já existe.")
                conn.close()

    with tab3:
        st.subheader("Importar CSV")
        uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
        if uploaded_file is not None:
            df_import = pd.read_csv(uploaded_file)
            if st.button("Confirmar Importação"):
                conn = get_connection()
                df_import.to_sql('estoque', conn, if_exists='append', index=False)
                conn.close()
                st.success("Produtos importados!")
                st.rerun()
        
        st.markdown("---")
        st.subheader("Exportar Estoque")
        conn = get_connection()
        df_export = pd.read_sql("SELECT * FROM estoque", conn)
        conn.close()
        if not df_export.empty:
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button("Baixar Estoque (.csv)", data=csv, file_name="estoque_itagesso.csv", mime="text/csv")

# --- VENDAS E COMPRAS ---
def page_transacoes():
    st.title("💸 Vendas e Compras")
    conn = get_connection()
    df_produtos = pd.read_sql("SELECT produto FROM estoque", conn)
    produtos = df_produtos['produto'].tolist()
    
    if not produtos:
        st.warning("Cadastre algum produto no Estoque primeiro!")
    else:
        tipo = st.selectbox("Tipo", ["Venda", "Compra"])
        prod_selecionado = st.selectbox("Selecione o Produto", produtos)
        qtd = st.number_input("Quantidade", min_value=0.1)
        valor = st.number_input("Valor Total da Operação (R$)", min_value=0.0)
        
        if st.button("Confirmar Movimentação"):
            cursor = conn.cursor()
            cursor.execute("INSERT INTO movimentacoes (produto, tipo, quantidade, valor_total, data) VALUES (?,?,?,?, date('now'))", 
                           (prod_selecionado, tipo, qtd, valor))
            
            if tipo == "Venda":
                cursor.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE produto = ?", (qtd, prod_selecionado))
            else:
                cursor.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE produto = ?", (qtd, prod_selecionado))
            
            conn.commit()
            st.success(f"Estoque atualizado!")
            st.rerun()
    conn.close()

# --- NAVEGAÇÃO ---
st.sidebar.title("ItaGesso Menu")
menu = st.sidebar.radio("Navegação", ["Dashboard", "Estoque", "Vendas/Compras"])
if menu == "Dashboard": show_dashboard()
elif menu == "Estoque": page_estoque()
elif menu == "Vendas/Compras": page_transacoes()

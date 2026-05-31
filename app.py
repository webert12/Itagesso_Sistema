import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
from fpdf import FPDF

# --- CONFIGURAÇÃO E CSS ---
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

# --- FUNÇÕES DE BANCO E BACKUP ---
def get_connection():
    return sqlite3.connect('itagesso.db', check_same_thread=False)

def init_db():
    if not os.path.exists('backups'): os.makedirs('backups')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, produto TEXT UNIQUE, 
                       categoria TEXT, quantidade REAL, preco_compra REAL, preco_venda REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS movimentacoes
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, produto TEXT, tipo TEXT, 
                       quantidade REAL, valor_total REAL, data DATE)''')
    conn.commit()
    conn.close()

def verificar_e_limpar_mensal():
    """Backup do mês anterior e exclusão dos dados antigos no dia 1º"""
    hoje = datetime.now()
    if hoje.day == 1:
        mes_passado = (hoje.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        arquivo_backup = f"backups/backup_{mes_passado}.csv"
        
        # Se o backup do mês passado ainda não foi criado, fazemos agora
        if not os.path.exists(arquivo_backup):
            conn = get_connection()
            df_old = pd.read_sql(f"SELECT * FROM movimentacoes WHERE strftime('%Y-%m', data) = '{mes_passado}'", conn)
            
            if not df_old.empty:
                df_old.to_csv(arquivo_backup, index=False) # Salva o backup
                conn.execute(f"DELETE FROM movimentacoes WHERE strftime('%Y-%m', data) = '{mes_passado}'") # Limpa os dados
                conn.commit()
            conn.close()

init_db()
verificar_e_limpar_mensal()

# --- FUNÇÃO EXPORTAR PDF ---
def exportar_pdf(df, titulo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=titulo, ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.ln(10)
    for index, row in df.iterrows():
        linha = f"{row['data']} | {row['produto']} | {row['tipo']} | R$ {row['valor_total']:,.2f}"
        pdf.cell(200, 10, txt=linha, ln=True)
    return pdf.output(dest='S').encode('latin-1')

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
        meses = sorted(df_mov['mes_ano'].unique(), reverse=True)
        mes_selecionado = st.selectbox("📅 Selecione o mês para análise:", meses, index=0)
        
        df_filtrado = df_mov[df_mov['mes_ano'] == mes_selecionado]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Receita", f"R$ {df_filtrado[df_filtrado['tipo'] == 'Venda']['valor_total'].sum():,.2f}")
        c2.metric("💸 Despesas", f"R$ {df_filtrado[df_filtrado['tipo'] == 'Compra']['valor_total'].sum():,.2f}")
        c3.metric("📈 Saldo", f"R$ {df_filtrado[df_filtrado['tipo'] == 'Venda']['valor_total'].sum() - df_filtrado[df_filtrado['tipo'] == 'Compra']['valor_total'].sum():,.2f}")
        
        # Botões de Exportação
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            st.download_button("📥 Baixar CSV do Mês", df_filtrado.to_csv(index=False), f"relatorio_{mes_selecionado}.csv", "text/csv")
        with col_e2:
            st.download_button("📥 Baixar PDF do Mês", exportar_pdf(df_filtrado, f"Relatório {mes_selecionado}"), f"relatorio_{mes_selecionado}.pdf", "application/pdf")
        
        with st.expander("📂 Ver Detalhes"):
            st.dataframe(df_filtrado[['data', 'produto', 'tipo', 'quantidade', 'valor_total']], use_container_width=True)
    else:
        st.info("Nenhuma movimentação registrada.")

    # GRÁFICO (RESTAURADO)
    if not df_estoque.empty:
        st.markdown("### 📊 Estoque Atual")
        df_chart = df_estoque[df_estoque['quantidade'] > 0].copy()
        if not df_chart.empty:
            df_chart = df_chart.groupby('categoria')['quantidade'].sum().reset_index()
            fig = px.pie(df_chart, values='quantidade', names='categoria', hole=0.3)
            st.plotly_chart(fig, use_container_width=True)

# --- ESTOQUE ---
def page_estoque():
    st.markdown("# 📦 Controle de Materiais")
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM estoque", conn)
    conn.close()
    
    st.download_button("📥 Exportar Estoque CSV", df.to_csv(index=False), "estoque_atual.csv", "text/csv")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Estoque Atual", "➕ Cadastro", "📥 Importação", "✏️ Edição"])
    
    with tab1:
        if not df.empty:
            edited_df = st.data_editor(df, column_config={"id": None}, use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Alterações"):
                conn = get_connection()
                for _, row in edited_df.iterrows():
                    conn.execute('UPDATE estoque SET produto=?, categoria=?, quantidade=?, preco_compra=?, preco_venda=? WHERE id=?', (row['produto'], row['categoria'], row['quantidade'], row['preco_compra'], row['preco_venda'], row['id']))
                conn.commit(); conn.close(); st.rerun()
    with tab2:
        with st.form("form_novo"):
            nome = st.text_input("Nome"); cat = st.selectbox("Categoria", ["Gesso", "Drywall", "Estrutura", "Parafusos", "Acabamento"])
            qtd = st.number_input("Quantidade", 0); pc = st.number_input("Preço Compra", 0.0); pv = st.number_input("Preço Venda", 0.0)
            if st.form_submit_button("Salvar"):
                conn = get_connection()
                try: conn.execute("INSERT INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (?,?,?,?,?)", (nome, cat, qtd, pc, pv)); conn.commit()
                except: st.error("Produto já existe.")
                conn.close(); st.rerun()
    with tab3:
        texto = st.text_area("Cole aqui: nome,categoria,quantidade,preco_compra,preco_venda")
        if st.button("Processar Lote"):
            conn = get_connection()
            for linha in texto.strip().split('\n'):
                p = [x.strip() for x in linha.split(',')]
                if len(p) == 5: conn.execute("INSERT OR REPLACE INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (?,?,?,?,?)", (p[0], p[1], float(p[2]), float(p[3]), float(p[4])))
            conn.commit(); conn.close(); st.rerun()
    with tab4:
        if not df.empty:
            sel = st.selectbox("Produto para editar", df['produto'].tolist())
            dados = df[df['produto'] == sel].iloc[0]
            with st.form("edit"):
                n_n = st.text_input("Nome", value=dados['produto'])
                n_q = st.number_input("Qtd", value=int(dados['quantidade']))
                n_pc = st.number_input("Preço Compra", value=float(dados['preco_compra']))
                n_pv = st.number_input("Preço Venda", value=float(dados['preco_venda']))
                if st.form_submit_button("Atualizar"):
                    conn = get_connection()
                    conn.execute("UPDATE estoque SET produto=?, quantidade=?, preco_compra=?, preco_venda=? WHERE id=?", (n_n, n_q, n_pc, n_pv, int(dados['id'])))
                    conn.commit(); conn.close(); st.rerun()

# --- TRANSAÇÕES ---
def page_transacoes():
    st.markdown("# 🛒 Movimentações")
    conn = get_connection()
    df_estoque = pd.read_sql("SELECT * FROM estoque", conn)
    produtos = df_estoque['produto'].tolist()
    if not produtos: st.warning("Cadastre algo no estoque primeiro!"); return
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo", ["Venda", "Compra"]); prod = st.selectbox("Material", produtos)
        with col2:
            qtd = st.number_input("Qtd", min_value=1); pu = st.number_input("Preço Un.", 0.0)
        if st.button("Confirmar"):
            conn.execute("INSERT INTO movimentacoes (produto, tipo, quantidade, valor_total, data) VALUES (?,?,?,?, date('now'))", (prod, tipo, qtd, qtd*pu))
            if tipo == "Venda": conn.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE produto = ?", (qtd, prod))
            else: conn.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE produto = ?", (qtd, prod))
            conn.commit(); conn.close(); st.success("Sucesso!"); st.rerun()
    conn.close()

# --- CONFIGURAÇÕES ---
def page_configuracoes():
    st.markdown("# ⚙️ Configurações")
    st.warning("Apaga todos os dados.")
    if st.button("🔴 Resetar Sistema"):
        conn = get_connection()
        conn.execute("DROP TABLE IF EXISTS estoque"); conn.execute("DROP TABLE IF EXISTS movimentacoes")
        conn.commit(); conn.close(); st.rerun()

# --- LÓGICA DE NAVEGAÇÃO ---
if menu == "Dashboard": show_dashboard()
elif menu == "Estoque": page_estoque()
elif menu == "Vendas/Compras": page_transacoes()
elif menu == "Configurações": page_configuracoes()

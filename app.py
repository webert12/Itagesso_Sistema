import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from fpdf import FPDF
from sqlalchemy import create_engine, text

# --- CONFIGURAÇÃO ROBUSTA ---
try:
    DATABASE_URL = st.secrets["DATABASE_URL"]
    
    # Configuração de conexão otimizada para Supabase
    engine = create_engine(
        DATABASE_URL,
        connect_args={"sslmode": "require"},
        pool_pre_ping=True,  # Verifica se a conexão está viva antes de usar
        pool_size=10,
        max_overflow=20
    )
    
    # Teste de conexão silencioso
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as e:
    st.error(f"Erro ao conectar ao banco: {e}")
    st.info("Verifique se a senha nas Secrets está correta e apenas com letras/números.")
    st.stop()

st.set_page_config(page_title="ItaGesso Gestão", layout="wide", page_icon="🏗️")
st.markdown("""<style>#MainMenu, footer, header {visibility: hidden;} [data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO BANCO ---
def init_db():
    with engine.connect() as conn:
        conn.execute(text('''CREATE TABLE IF NOT EXISTS estoque 
                          (id SERIAL PRIMARY KEY, produto TEXT UNIQUE, 
                           categoria TEXT, quantidade REAL, preco_compra REAL, preco_venda REAL)'''))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS movimentacoes
                          (id SERIAL PRIMARY KEY, produto TEXT, tipo TEXT, 
                           quantidade REAL, valor_total REAL, data DATE)'''))
        conn.commit()

init_db()

# --- BACKUP ---
def verificar_e_limpar_mensal():
    hoje = datetime.now()
    if hoje.day == 1:
        mes_passado = (hoje.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        arquivo_backup = f"backup_{mes_passado}.csv"
        
        df_old = pd.read_sql(f"SELECT * FROM movimentacoes WHERE TO_CHAR(data, 'YYYY-MM') = '{mes_passado}'", engine)
        
        if not df_old.empty:
            df_old.to_csv(arquivo_backup, index=False)
            with engine.connect() as conn:
                conn.execute(text(f"DELETE FROM movimentacoes WHERE TO_CHAR(data, 'YYYY-MM') = '{mes_passado}'"))
                conn.commit()

verificar_e_limpar_mensal()

# --- FUNÇÕES ---
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

# --- MENU ---
menu = st.radio("Navegação", ["Dashboard", "Estoque", "Vendas/Compras", "Configurações"], horizontal=True, label_visibility="collapsed")
st.markdown("---")

def show_dashboard():
    st.markdown("# 🏛️ ItaGesso | Painel de Controle")
    df_mov = pd.read_sql("SELECT * FROM movimentacoes", engine)
    df_estoque = pd.read_sql("SELECT * FROM estoque", engine)
    
    if not df_mov.empty:
        df_mov['data'] = pd.to_datetime(df_mov['data'])
        df_mov['mes_ano'] = df_mov['data'].dt.strftime('%Y-%m')
        meses = sorted(df_mov['mes_ano'].unique(), reverse=True)
        mes_selecionado = st.selectbox("📅 Selecione o mês:", meses, index=0)
        df_filtrado = df_mov[df_mov['mes_ano'] == mes_selecionado]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Receita", f"R$ {df_filtrado[df_filtrado['tipo'] == 'Venda']['valor_total'].sum():,.2f}")
        c2.metric("💸 Despesas", f"R$ {df_filtrado[df_filtrado['tipo'] == 'Compra']['valor_total'].sum():,.2f}")
        c3.metric("📈 Saldo", f"R$ {df_filtrado[df_filtrado['tipo'] == 'Venda']['valor_total'].sum() - df_filtrado[df_filtrado['tipo'] == 'Compra']['valor_total'].sum():,.2f}")
        
        st.download_button("📥 Baixar CSV do Mês", df_filtrado.to_csv(index=False), f"relatorio_{mes_selecionado}.csv", "text/csv")
        st.dataframe(df_filtrado, use_container_width=True)
    
    if not df_estoque.empty:
        st.markdown("### 📊 Estoque")
        fig = px.pie(df_estoque.groupby('categoria')['quantidade'].sum().reset_index(), values='quantidade', names='categoria', hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

def page_estoque():
    st.markdown("# 📦 Estoque")
    df = pd.read_sql("SELECT * FROM estoque", engine)
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Estoque", "➕ Cadastro", "📥 Importação", "✏️ Edição"])
    
    with tab1:
        edited_df = st.data_editor(df, column_config={"id": None}, use_container_width=True, hide_index=True)
        if st.button("💾 Salvar Alterações"):
            with engine.connect() as conn:
                for _, row in edited_df.iterrows():
                    conn.execute(text('UPDATE estoque SET produto=:p, categoria=:c, quantidade=:q, preco_compra=:pc, preco_venda=:pv WHERE id=:id'), 
                                 {"p": row['produto'], "c": row['categoria'], "q": row['quantidade'], "pc": row['preco_compra'], "pv": row['preco_venda'], "id": row['id']})
                conn.commit(); st.rerun()
    with tab2:
        with st.form("form_novo"):
            nome = st.text_input("Nome"); cat = st.selectbox("Categoria", ["Gesso", "Drywall", "Estrutura", "Parafusos", "Acabamento"])
            qtd = st.number_input("Qtd", 0); pc = st.number_input("Preço Compra", 0.0); pv = st.number_input("Preço Venda", 0.0)
            if st.form_submit_button("Salvar"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (:n, :c, :q, :pc, :pv)"), 
                                 {"n": nome, "c": cat, "q": qtd, "pc": pc, "pv": pv})
                    conn.commit(); st.rerun()
    with tab3:
        texto = st.text_area("Formato: nome,categoria,quantidade,preco_compra,preco_venda")
        if st.button("Processar Lote"):
            with engine.connect() as conn:
                for linha in texto.strip().split('\n'):
                    p = [x.strip() for x in linha.split(',')]
                    if len(p) == 5:
                        conn.execute(text("INSERT INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (:p0, :p1, :p2, :p3, :p4) ON CONFLICT(produto) DO NOTHING"), 
                                     {"p0": p[0], "p1": p[1], "p2": float(p[2]), "p3": float(p[3]), "p4": float(p[4])})
                conn.commit(); st.rerun()
    with tab4:
        if not df.empty:
            sel = st.selectbox("Produto", df['produto'].tolist())
            dados = df[df['produto'] == sel].iloc[0]
            with st.form("edit"):
                n_n = st.text_input("Nome", value=dados['produto'])
                n_q = st.number_input("Qtd", value=int(dados['quantidade']))
                n_pc = st.number_input("Preço Compra", value=float(dados['preco_compra']))
                n_pv = st.number_input("Preço Venda", value=float(dados['preco_venda']))
                if st.form_submit_button("Atualizar"):
                    with engine.connect() as conn:
                        conn.execute(text("UPDATE estoque SET produto=:n, quantidade=:q, preco_compra=:pc, preco_venda=:pv WHERE id=:id"), 
                                     {"n": n_n, "q": n_q, "pc": n_pc, "pv": n_pv, "id": int(dados['id'])})
                        conn.commit(); st.rerun()

def page_transacoes():
    st.markdown("# 🛒 Movimentações")
    df_estoque = pd.read_sql("SELECT * FROM estoque", engine)
    produtos = df_estoque['produto'].tolist()
    if not produtos: st.warning("Cadastre algo no estoque!"); return
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1: tipo = st.selectbox("Tipo", ["Venda", "Compra"]); prod = st.selectbox("Material", produtos)
        with col2: qtd = st.number_input("Qtd", min_value=1); pu = st.number_input("Preço Un.", 0.0)
        if st.button("Confirmar"):
            with engine.connect() as conn:
                conn.execute(text("INSERT INTO movimentacoes (produto, tipo, quantidade, valor_total, data) VALUES (:prod, :tipo, :qtd, :total, CURRENT_DATE)"), 
                             {"prod": prod, "tipo": tipo, "qtd": qtd, "total": qtd*pu})
                if tipo == "Venda": conn.execute(text("UPDATE estoque SET quantidade = quantidade - :qtd WHERE produto = :prod"), {"qtd": qtd, "prod": prod})
                else: conn.execute(text("UPDATE estoque SET quantidade = quantidade + :qtd WHERE produto = :prod"), {"qtd": qtd, "prod": prod})
                conn.commit(); st.success("Sucesso!"); st.rerun()

def page_configuracoes():
    st.markdown("# ⚙️ Configurações")
    if st.button("🔴 Resetar Banco"):
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS estoque")); conn.execute(text("DROP TABLE IF EXISTS movimentacoes"))
            conn.commit(); st.rerun()

if menu == "Dashboard": show_dashboard()
elif menu == "Estoque": page_estoque()
elif menu == "Vendas/Compras": page_transacoes()
elif menu == "Configurações": page_configuracoes()

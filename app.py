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
    
    total_vendas = df_mov[df_mov['tipo'] == 'Venda']['valor_total'].sum()
    total_compras = df_mov[df_mov['tipo'] == 'Compra']['valor_total'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Receita Total", f"R$ {total_vendas:,.2f}")
    c2.metric("Despesas Totais", f"R$ {total_compras:,.2f}")
    c3.metric("Saldo Estimado", f"R$ {total_vendas - total_compras:,.2f}")
    
    if not df_estoque.empty:
        st.subheader("Distribuição do Estoque")
        fig = px.pie(df_estoque, values='quantidade', names='categoria', title="Composição do Estoque")
        st.plotly_chart(fig, use_container_width=True)

# --- ESTOQUE ---
def page_estoque():
    st.title("📦 Controle de Materiais")
    
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM estoque", conn)
    conn.close()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Estoque Atual", "➕ Cadastrar Novo", "📥 Colar Dados", "✏️ Editar Produto"])
    
    with tab1:
        if not df.empty:
            st.info("💡 Edite e clique em 'Salvar Alterações Rápidas'.")
            edited_df = st.data_editor(
                df,
                column_config={
                    "id": None, 
                    "quantidade": st.column_config.ProgressColumn("Estoque Atual", format="%f", min_value=0, max_value=500)
                },
                use_container_width=True, 
                hide_index=True
            )
            
            if st.button("💾 Salvar Alterações Rápidas"):
                conn = get_connection()
                cursor = conn.cursor()
                for index, row in edited_df.iterrows():
                    cursor.execute('''UPDATE estoque SET produto=?, categoria=?, quantidade=?, preco_compra=?, preco_venda=? WHERE id=?''', 
                                   (row['produto'], row['categoria'], row['quantidade'], row['preco_compra'], row['preco_venda'], row['id']))
                conn.commit()
                conn.close()
                st.success("Estoque atualizado!")
                st.rerun()
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
                    conn.close()
                    st.success("Produto cadastrado!")
                    st.rerun()
                except:
                    st.error("Erro: Produto já existe.")
                    conn.close()

    with tab3:
        st.subheader("Colar Dados (Bulk Import)")
        texto_colado = st.text_area("Cole aqui (formato: nome,categoria,quantidade,preco_compra,preco_venda)", height=200)
        if st.button("Processar e Salvar"):
            if texto_colado:
                linhas = texto_colado.strip().split('\n')
                conn = get_connection()
                for linha in linhas:
                    partes = [p.strip() for p in linha.split(',')]
                    if len(partes) == 5:
                        conn.execute("INSERT OR REPLACE INTO estoque (produto, categoria, quantidade, preco_compra, preco_venda) VALUES (?,?,?,?,?)", 
                                     (partes[0], partes[1], float(partes[2]), float(partes[3]), float(partes[4])))
                conn.commit()
                conn.close()
                st.success("Importado com sucesso!")
                st.rerun()

    with tab4:
        st.subheader("✏️ Editar Produto Selecionado")
        if not df.empty:
            lista_produtos = df['produto'].tolist()
            selecionado = st.selectbox("Selecione o produto que deseja editar", lista_produtos)
            dados_prod = df[df['produto'] == selecionado].iloc[0]
            
            with st.form("form_edicao"):
                n_nome = st.text_input("Novo Nome", value=dados_prod['produto'])
                categorias = ["Gesso", "Drywall", "Estrutura", "Parafusos", "Acabamento"]
                idx_cat = categorias.index(dados_prod['categoria']) if dados_prod['categoria'] in categorias else 0
                n_cat = st.selectbox("Categoria", categorias, index=idx_cat)
                n_qtd = st.number_input("Quantidade", value=float(dados_prod['quantidade']), step=0.1)
                n_pcompra = st.number_input("Preço de Compra", value=float(dados_prod['preco_compra']), step=0.01)
                n_pvenda = st.number_input("Preço de Venda", value=float(dados_prod['preco_venda']), step=0.01)
                
                if st.form_submit_button("Atualizar Produto"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute('''UPDATE estoque SET produto=?, categoria=?, quantidade=?, preco_compra=?, preco_venda=? WHERE id=?''', 
                                       (n_nome, n_cat, n_qtd, n_pcompra, n_pvenda, int(dados_prod['id'])))
                        conn.commit()
                        st.success("Produto atualizado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Erro: Já existe um produto com este nome!")
                    finally:
                        conn.close()
        else:
            st.warning("Cadastre produtos para poder editar.")

# --- VENDAS E COMPRAS (CORRIGIDO) ---
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
        qtd = st.number_input("Quantidade", min_value=0.1, step=1.0)
        preco_unitario = st.number_input("Preço Unitário (R$)", min_value=0.0, step=0.1)
        
        # O SISTEMA AGORA CALCULA O TOTAL
        total_calculado = qtd * preco_unitario
        st.write(f"### Valor Total da Operação: R$ {total_calculado:,.2f}")
        
        if st.button("Confirmar Movimentação"):
            cursor = conn.cursor()
            cursor.execute("INSERT INTO movimentacoes (produto, tipo, quantidade, valor_total, data) VALUES (?,?,?,?, date('now'))", 
                           (prod_selecionado, tipo, qtd, total_calculado))
            if tipo == "Venda":
                cursor.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE produto = ?", (qtd, prod_selecionado))
            else:
                cursor.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE produto = ?", (qtd, prod_selecionado))
            conn.commit()
            conn.close()
            st.success(f"Estoque e Saldo atualizados com sucesso!")
            st.rerun()
    conn.close()

# --- NAVEGAÇÃO ---
st.sidebar.title("ItaGesso Menu")
menu = st.sidebar.radio("Navegação", ["Dashboard", "Estoque", "Vendas/Compras"])
if menu == "Dashboard": show_dashboard()
elif menu == "Estoque": page_estoque()
elif menu == "Vendas/Compras": page_transacoes()

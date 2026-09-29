import streamlit as st
import sqlite3
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import pandas as pd
from datetime import datetime
import numpy as np
import cv2
from PIL import Image

# Nome do arquivo do banco de dados SQLite
DB_FILE = "cemic.db"

# ==========================================
# FUNÇÕES DE BANCO DE DADOS (SQLite)
# ==========================================
def get_connection():
    """Conecta ao banco de dados SQLite."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def carregar_alunos():
    """Retorna todos os alunos cadastrados ordenados por Turma e Nome."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, Turma, Nome FROM Alunos ORDER BY Turma ASC, Nome ASC")
    alunos = cursor.fetchall()
    conn.close()
    return alunos

def carregar_projetos():
    """Retorna todos os projetos cadastrados."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, Nome, Turno FROM Projetos ORDER BY Nome ASC")
    projetos = cursor.fetchall()
    conn.close()
    return projetos

def buscar_aluno_por_id(id_aluno):
    """Busca um aluno específico pelo seu ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, Turma, Nome FROM Alunos WHERE id = ?", (id_aluno,))
    aluno = cursor.fetchone()
    conn.close()
    return aluno

def registrar_frequencia(id_aluno, id_projeto):
    """Insere o registro de presença na tabela Frequencia."""
    conn = get_connection()
    cursor = conn.cursor()
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO Frequencia (id_aluno, id_projeto, DataHora) VALUES (?, ?, ?)",
        (id_aluno, id_projeto, data_hora)
    )
    conn.commit()
    conn.close()
    return data_hora

def carregar_relatorio_frequencia():
    """Consulta os dados de frequência ordenados por Turma e Nome do aluno."""
    conn = get_connection()
    query = """
    SELECT 
        Alunos.Turma AS Turma,
        Alunos.Nome AS Aluno,
        Alunos.id AS ID_Aluno,
        Projetos.Nome AS Projeto,
        Projetos.Turno AS Turno_Projeto,
        Frequencia.DataHora AS DataHora
    FROM Frequencia
    INNER JOIN Alunos ON Frequencia.id_aluno = Alunos.id
    INNER JOIN Projetos ON Frequencia.id_projeto = Projetos.id
    ORDER BY Alunos.Turma ASC, Alunos.Nome ASC, Frequencia.DataHora DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@st.cache_data
def gerar_imagem_barcode(id_aluno):
    """Gera a imagem do código de barras Code128 e reduz para 30% do tamanho original."""
    Code128 = barcode.get_barcode_class('code128')
    buffer = BytesIO()
    code = Code128(str(id_aluno), writer=ImageWriter())
    code.write(buffer)
    buffer.seek(0)
    
    # Redimensiona a imagem para 30% das dimensões originais
    img = Image.open(buffer)
    largura_orig, altura_orig = img.size
    novo_tamanho = (int(largura_orig * 0.3), int(altura_orig * 0.3))
    img_redimensionada = img.resize(novo_tamanho, Image.LANCZOS)
    
    out_buffer = BytesIO()
    img_redimensionada.save(out_buffer, format="PNG")
    return out_buffer.getvalue()

# ==========================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Controle de Presença e Códigos de Barras",
    page_icon="🏷️",
    layout="wide"
)

st.title("🏷️ Sistema de Registro de Frequência e Códigos de Barras")

tab1, tab2, tab3 = st.tabs([
    "🖨️ Lista Completa de Alunos e Barcodes", 
    "📷 Registrar Presença", 
    "📊 Relatório de Frequência"
])

# ==========================================
# ABA 1: LISTAGEM COMPLETA COM CÓDIGOS DE BARRAS
# ==========================================
with tab1:
    st.header("Listagem Geral de Alunos com Código de Barras")
    
    alunos = carregar_alunos()
    
    if alunos:
        turmas_unicas = sorted(list(set(a['Turma'] for a in alunos)))
        
        # Filtros rápidos
        col_filtro1, col_filtro2 = st.columns([1, 2])
        with col_filtro1:
            turma_filtro = st.multiselect("Filtrar Turmas:", options=turmas_unicas, default=turmas_unicas)
        with col_filtro2:
            busca_nome = st.text_input("Buscar por Nome do Aluno:", value="", placeholder="Digite o nome do aluno...")
        
        # Aplicação dos filtros
        alunos_filtrados = [
            a for a in alunos 
            if a['Turma'] in turma_filtro and busca_nome.lower() in a['Nome'].lower()
        ]
        
        st.markdown(f"**Total de alunos exibidos:** `{len(alunos_filtrados)}`")
        st.divider()

        # Exibição organizada por Turma e em Grade de Cards
        for turma in turmas_unicas:
            alunos_da_turma = [a for a in alunos_filtrados if a['Turma'] == turma]
            
            if alunos_da_turma:
                st.subheader(f"🏫 Turma: {turma}")
                
                # Grade de 3 colunas
                cols = st.columns(5)
                for idx, aluno in enumerate(alunos_da_turma):
                    with cols[idx % 5]:
                        with st.container(border=True):
                            st.markdown("<small>"+aluno['Nome']+"</small>", unsafe_allow_html=True)                               
#                            st.markdown(f"### {aluno['Nome']}")
#                            st.caption(f"**ID:** `{aluno['id']}` | **Turma:** `{aluno['Turma']}`")
                            
                            img_bytes = gerar_imagem_barcode(aluno['id'])
                            # Exibe a imagem no tamanho real reduzido a 30%
                            st.image(img_bytes)
                            
#                             st.download_button(
#                                 label="📥 Baixar PNG",
#                                 data=img_bytes,
#                                 file_name=f"barcode_{aluno['id']}_{aluno['Nome'].replace(' ', '_')}.png",
#                                 mime="image/png",
#                                 key=f"btn_dl_{aluno['id']}"
#                             )
                st.write("") # Espaçamento
    else:
        st.warning("Nenhum aluno cadastrado no banco de dados.")

# ==========================================
# ABA 2: REGISTRAR PRESENÇA
# ==========================================
with tab2:
    st.header("Registro de Frequência")
    
    projetos = carregar_projetos()
    
    if not projetos:
        st.error("Nenhum projeto encontrado no banco de dados.")
    else:
        opcoes_projetos = {
            f"{p['Nome']} ({p['Turno']})": p['id'] 
            for p in projetos
        }
        
        projeto_selecionado_label = st.selectbox(
            "Selecione o Projeto / Atividade Visitada:",
            options=list(opcoes_projetos.keys())
        )
        id_projeto_selecionado = opcoes_projetos[projeto_selecionado_label]
        
        scan_method = st.radio(
            "Modo de Leitura do Código de Barras:", 
            ["Leitor USB / Bluetooth (Teclado)", "Webcam / Câmera"],
            horizontal=True
        )
        
        if scan_method == "Leitor USB / Bluetooth (Teclado)":
            st.info("💡 Clique no campo abaixo e passe o leitor de código de barras ou digite o ID do aluno e pressione Enter.")
            
            with st.form(key="form_presenca", clear_on_submit=True):
                scanned_id_raw = st.text_input("Código de Barras (ID do Aluno):", key="input_barcode")
                submit = st.form_submit_button("Registrar Presença")
                
                if submit and scanned_id_raw:
                    try:
                        id_aluno = int(scanned_id_raw.strip())
                        aluno = buscar_aluno_por_id(id_aluno)
                        
                        if aluno:
                            data_hora = registrar_frequencia(id_aluno, id_projeto_selecionado)
                            st.success(
                                f"✅ Presença Registrada!\n\n"
                                f"• **Aluno:** {aluno['Nome']} (Turma: {aluno['Turma']})\n\n"
                                f"• **Projeto:** {projeto_selecionado_label}\n\n"
                                f"• **Data/Hora:** {data_hora}"
                            )
                        else:
                            st.error(f"❌ Aluno com ID **{id_aluno}** não encontrado no banco de dados.")
                    except ValueError:
                        st.error("❌ Digite ou leia um código com valor numérico válido.")

        else: # Leitura via Câmera
            st.info("Aponte o código de barras para a câmera e tire a foto.")
            camera_image = st.camera_input("Capturar Código de Barras")
            
            if camera_image is not None:
                bytes_data = camera_image.getvalue()
                cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                
                detector = cv2.barcode.BarcodeDetector()
                retval, decoded_info, decoded_type, points = detector.detectAndDecode(cv_img)
                
                if retval and decoded_info[0]:
                    scanned_id_raw = decoded_info[0]
                    try:
                        id_aluno = int(scanned_id_raw.strip())
                        aluno = buscar_aluno_por_id(id_aluno)
                        
                        if aluno:
                            data_hora = registrar_frequencia(id_aluno, id_projeto_selecionado)
                            st.success(
                                f"✅ Presença Registrada via Câmera!\n\n"
                                f"• **Aluno:** {aluno['Nome']} (Turma: {aluno['Turma']})\n\n"
                                f"• **Projeto:** {projeto_selecionado_label}\n\n"
                                f"• **Data/Hora:** {data_hora}"
                            )
                        else:
                            st.error(f"❌ Aluno com ID **{id_aluno}** não encontrado no banco de dados.")
                    except ValueError:
                        st.error(f"❌ Código lido ({scanned_id_raw}) não é um número inteiro válido.")
                else:
                    st.error("Nenhum código de barras legível foi detectado na foto. Tente aproximar ou focar melhor.")

# ==========================================
# ABA 3: RELATÓRIO DE FREQUÊNCIA
# ==========================================
with tab3:
    st.header("Relatório de Frequência por Turma e Aluno")
    
    df_freq = carregar_relatorio_frequencia()
    
    if not df_freq.empty:
        col_f1, col_f2 = st.columns([1, 1])
        
        with col_f1:
            turmas_disponiveis = df_freq["Turma"].unique().tolist()
            turmas_selecionadas = st.multiselect(
                "Filtrar por Turma:", 
                options=turmas_disponiveis, 
                default=turmas_disponiveis
            )
        
        with col_f2:
            projetos_disponiveis = df_freq["Projeto"].unique().tolist()
            projetos_selecionados = st.multiselect(
                "Filtrar por Projeto:", 
                options=projetos_disponiveis, 
                default=projetos_disponiveis
            )
            
        df_filtrado = df_freq[
            (df_freq["Turma"].isin(turmas_selecionadas)) & 
            (df_freq["Projeto"].isin(projetos_selecionados))
        ]
        
        # Métricas resumidas
        m1, m2, m3 = st.columns(3)
        m1.metric("Total de Registros de Visitas", len(df_filtrado))
        m2.metric("Alunos Distintos Presentes", df_filtrado["ID_Aluno"].nunique())
        m3.metric("Projetos Visitados", df_filtrado["Projeto"].nunique())
        
        st.subheader("📋 Tabela Detalhada de Visitas")
        st.dataframe(
            df_filtrado[["Turma", "Aluno", "ID_Aluno", "Projeto", "Turno_Projeto", "DataHora"]],
            use_container_width=True
        )
        
        # Botão de exportação
        csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Exportar Relatório em CSV",
            data=csv_data,
            file_name=f"relatorio_frequencia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhum registro de frequência cadastrado até o momento.")
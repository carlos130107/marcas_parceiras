import streamlit as st
import pandas as pd
import altair as alt

# CONFIGURAÇÕES DA PÁGINA
st.set_page_config(
    page_title="Análise das Marcas",
    page_icon="📊",
    layout="wide")

# CSS PARA DARK MODE COMPLETO
st.markdown("""
    <style>
        .stApp {
            background-color: #0e1117 !important;
            color: white !important;
        }
        section[data-testid="stSidebar"] {
            background-color: #1a1d23 !important;
            color: white !important;
        }
        div[data-baseweb="select"] > div, div[data-baseweb="input"], div.stSelectbox {
            background-color: #1a1d23 !important;
            color: white !important;
        }
        div[data-baseweb="select"] span {
            color: white !important;
        }
        label, .stSelectbox label {
            color: white !important;
        }
        .dataframe {
            color: white !important;
            background-color: #1a1d23 !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: white !important;
        }
        div[role="tooltip"] {
            background-color: #1a1d23 !important;
            color: white !important;
        }
        ::-webkit-scrollbar {
            background: #0e1117;
        }
        ::-webkit-scrollbar-thumb {
            background: #555;
        }
    </style>
""", unsafe_allow_html=True)

# --- Inicializa estado de autenticação ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario"] = ""

# --- CARREGAR DADOS PARA GERAR USUÁRIOS E SENHAS ---
arquivo = "dados.xlsx"
try:
    abas = pd.ExcelFile(arquivo).sheet_names
except FileNotFoundError:
    st.error("Arquivo 'dados.xlsx' não encontrado. Verifique o caminho do arquivo.")
    st.stop()

# Filtrar abas para ocultar "Supervisores" (não aparece no selectbox de marcas)
abas_filtradas = [aba for aba in abas if aba != "Supervisores"]

# Carregar a primeira aba válida (não "Supervisores") para extrair nomes dos gerentes
primeira_aba_valida = next((aba for aba in abas if aba != "Supervisores"), abas[0])
df_usuarios = pd.read_excel(arquivo, sheet_name=primeira_aba_valida)

# Renomear colunas para garantir que "Nome Gerente" exista (assumindo estrutura fixa; fragil se Excel mudar)
df_usuarios.rename(columns={
    df_usuarios.columns[0]: "Gerente",
    df_usuarios.columns[1]: "Nome Gerente",
    df_usuarios.columns[2]: "Representante",
    df_usuarios.columns[3]: "Periodo",
    df_usuarios.columns[5]: "Peso",
    df_usuarios.columns[6]: "Faturamento",
    df_usuarios.columns[7]: "Supervisor"
}, inplace=True)

# Extrair nomes únicos dos gerentes
nomes_gerentes = df_usuarios["Nome Gerente"].dropna().unique()

# Criar dicionário de usuários e senhas
usuarios = {}
for nome in nomes_gerentes:
    usuario = nome.replace(" ", "")  # remove espaços para usuário
    senha = nome.lower().replace(" ", "") + "123"  # senha simples, pode ser alterada
    usuarios[usuario] = senha

# Usuário coringa com acesso a todos os dados
usuarios["admin"] = "admin123"

# --- LOGIN NA SIDEBAR ---
st.sidebar.header("Login do Gerente")
usuario_input = st.sidebar.text_input("Usuário")
senha_input = st.sidebar.text_input("Senha", type="password")
botao_login = st.sidebar.button("Entrar")

if botao_login:
    if usuario_input in usuarios and senha_input == usuarios[usuario_input]:
        st.session_state["autenticado"] = True
        st.session_state["usuario"] = usuario_input
        st.sidebar.success(f"Bem-vindo, {usuario_input}!")
    else:
        st.sidebar.error("Usuário ou senha incorretos.")

if not st.session_state["autenticado"]:
    st.warning("Por favor, faça login para acessar os dados.")
    st.stop()

usuario_autenticado = st.session_state["usuario"]

# --- APÓS LOGIN, CARREGAR DADOS DA MARCA SELECIONADA ---
st.sidebar.header("Selecione a Marca")
# Usar abas_filtradas para ocultar "Supervisores" no dropdown
marca_selecionada = st.sidebar.selectbox("Marca", abas_filtradas, index=0)

df = pd.read_excel(arquivo, sheet_name=marca_selecionada)

# Renomear colunas (assumindo estrutura fixa; fragil se Excel mudar)
df.rename(columns={
    df.columns[0]: "Gerente",
    df.columns[1]: "Nome Gerente",
    df.columns[2]: "Representante",
    df.columns[3]: "Periodo",
    df.columns[4]: "Positivações",
    df.columns[5]: "Peso",
    df.columns[6]: "Faturamento",
    df.columns[7]: "Supervisor"
}, inplace=True)

# Mapear usuário para nome do gerente original
usuario_para_nome = {nome.replace(" ", ""): nome for nome in nomes_gerentes}

# --- FILTRO GERENTE (aparece só para admin) ---
if usuario_autenticado == "admin":
    # Para admin, mostrar filtro Gerente no sidebar
    st.sidebar.header("Filtro Gerente")
    opcoes_gerente = ["Todos"] + sorted(df["Nome Gerente"].dropna().unique().tolist())
    gerente_selecionado = st.sidebar.selectbox("Gerente", opcoes_gerente, index=0)
    if gerente_selecionado != "Todos":
        df = df[df["Nome Gerente"] == gerente_selecionado]
    nome_gerente_autenticado = None  # admin tem acesso total (ou filtrado pelo filtro acima)
else:
    # Para outros usuários, filtrar automaticamente pelo gerente autenticado
    nome_gerente_autenticado = usuario_para_nome.get(usuario_autenticado)
    if nome_gerente_autenticado is None:
        st.error("Erro: gerente não encontrado.")
        st.stop()
    df = df[df["Nome Gerente"] == nome_gerente_autenticado]

# Converter datas e criar colunas auxiliares
df["Periodo"] = pd.to_datetime(df["Periodo"], errors="coerce")
df["MesAnoOrd"] = df["Periodo"].dt.to_period("M").dt.to_timestamp()
df["MesAno"] = df["Periodo"].dt.strftime("%b/%Y")

# **TÍTULO DINÂMICO: Inclui o nome da marca selecionada**
st.title(f"📊 Análise {marca_selecionada}")

# SIDEBAR DE FILTROS
st.sidebar.header("Filtros")

def filtro_selectbox(coluna, df_input):
    if coluna not in df_input.columns or df_input[coluna].isnull().all():
        return df_input  # Se coluna não existe ou está vazia, ignora filtro
    opcoes = ["Todos"] + sorted(df_input[coluna].dropna().unique().tolist())
    selecao = st.sidebar.selectbox(coluna, opcoes)
    if selecao == "Todos":
        return df_input
    else:
        return df_input[df_input[coluna] == selecao]

# Aplicar filtros dentro dos dados já filtrados por gerente
df_filtrado = df.copy()

# Filtro Supervisor
df_filtrado = filtro_selectbox("Supervisor", df_filtrado)

# Filtro Representante
df_filtrado = filtro_selectbox("Representante", df_filtrado)

# Verificar se após filtros há dados
if df_filtrado.empty:
    st.warning("Nenhum dado disponível para os filtros selecionados.")
    st.stop()

# Agrupar dados para gráficos e tabela
df_grouped = df_filtrado.groupby(["MesAnoOrd", "MesAno"], as_index=False).agg({
    "Peso": "sum",
    "Faturamento": "sum",
    "Positivações": "sum"
}).sort_values("MesAnoOrd")

if df_grouped.empty:
    st.warning("Nenhum dado agrupado disponível.")
    st.stop()

# Funções para gráficos e visualização
def configure_black_background(chart):
    return chart.configure_axis(
                labelColor='white',
                titleColor='white'
            )\
            .configure_legend(
                labelColor='white',
                titleColor='white'
            )\
            .configure_title(color='white')\
            .configure_view(
                strokeWidth=0,
                fill='#0e1117'
            )

def adicionar_rotulos(chart, campo, formato="{:,}", cor="white", tamanho=14):
    return chart.mark_text(
        align='center',
        baseline='bottom',
        dy=-10,
        size=tamanho,
        color=cor
    ).encode(
        text=alt.Text(campo, format=formato)
    )

# Função para calcular domínio Y com margem menor para suavizar escala
def calcular_dominio_y(serie):
    min_val = serie.min()
    max_val = serie.max()
    margem = (max_val - min_val) * 0.05  # 5% de margem
    if margem == 0:
        margem = max_val * 0.05 if max_val != 0 else 1
    return [min_val - margem, max_val + margem]

# Gráfico Peso
st.subheader("⚖️ Evolução do Peso")
dominio_peso = calcular_dominio_y(df_grouped["Peso"])
base_peso = alt.Chart(df_grouped).encode(
    x=alt.X(
        "MesAnoOrd:T",
        title="Mês/Ano",
        axis=alt.Axis(format="%b/%Y", labelAngle=0, labelColor="white", titleColor="white", tickCount="month")
    ),
    y=alt.Y(
        "Peso:Q",
        scale=alt.Scale(domain=dominio_peso),
        axis=alt.Axis(labelColor="white", titleColor="white")
    ),
    tooltip=["MesAno", "Peso"]
)
linha_peso = base_peso.mark_line(point=True, color='cyan', interpolate='monotone').properties(height=500, width=800)
rotulos_peso = adicionar_rotulos(base_peso, "Peso", formato=",.0f")
st.altair_chart(configure_black_background(linha_peso + rotulos_peso), use_container_width=True)

# Gráfico Faturamento
st.subheader("💵 Evolução do Faturamento")
dominio_fat = calcular_dominio_y(df_grouped["Faturamento"])
base_fat = alt.Chart(df_grouped).encode(
    x=alt.X(
        "MesAnoOrd:T",
        title="Mês/Ano",
        axis=alt.Axis(format="%b/%Y", labelAngle=0, labelColor="white", titleColor="white", tickCount="month")
    ),
    y=alt.Y(
        "Faturamento:Q",
        scale=alt.Scale(domain=dominio_fat),
        axis=alt.Axis(labelColor="white", titleColor="white")
    ),
    tooltip=["MesAno", "Faturamento"]
)
linha_fat = base_fat.mark_line(point=True, color='lime', interpolate='monotone').properties(height=500, width=800)
rotulos_fat = adicionar_rotulos(base_fat, "Faturamento", formato="$,.0f", cor="white")
st.altair_chart(configure_black_background(linha_fat + rotulos_fat), use_container_width=True)

# Gráfico Positivações
st.subheader("🛒 Evolução das Positivações")
dominio_pos = calcular_dominio_y(df_grouped["Positivações"])
base_pos = alt.Chart(df_grouped).encode(
    x=alt.X(
        "MesAnoOrd:T",
        title="Mês/Ano",
        axis=alt.Axis(format="%b/%Y", labelAngle=0, labelColor="white", titleColor="white", tickCount="month")
    ),
    y=alt.Y(
        "Positivações:Q",
        scale=alt.Scale(domain=dominio_pos),
        axis=alt.Axis(labelColor="white", titleColor="white")
    ),
    tooltip=["MesAno", "Positivações"]
)
linha_pos = base_pos.mark_line(point=True, color='orange', interpolate='monotone').properties(height=500, width=800)
rotulos_pos = adicionar_rotulos(base_pos, "Positivações", formato=",.0f", cor="white")
st.altair_chart(configure_black_background(linha_pos + rotulos_pos), use_container_width=True)

# Tabela resumo
st.subheader("📋 Resumo dos Dados")
df_display = df_grouped.copy()
df_display["Peso"] = df_display["Peso"].map(lambda x: f"{x:,.0f} kg")
df_display["Faturamento"] = df_display["Faturamento"].map(lambda x: f"R$ {x:,.0f}")
df_display["Positivações"] = df_display["Positivações"].map(lambda x: f"{x:,.0f}")
df_display = df_display[["MesAno", "Peso", "Faturamento", "Positivações"]]
df_display.columns = ["Mês/Ano", "Peso Total", "Faturamento Total", "Positivações Totais"]
st.dataframe(df_display, use_container_width=True, hide_index=True)

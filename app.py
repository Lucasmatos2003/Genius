import os
import json
import streamlit as st
import google.generativeai as genai

# ------------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E CSS
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Genius Studio",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carrega estilização personalizada
try:
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("Arquivo 'style.css' não encontrado na pasta do projeto.")

# Configuração da API Key
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# ------------------------------------------------------------------------------
# 2. INSTRUÇÃO DO SISTEMA (DIRETRIZES DO GENIUS STUDIO)
# ------------------------------------------------------------------------------
DEFAULT_SYSTEM_INSTRUCTION = """A sua missão é ajudar o utilizador com programação, atividades como escrever, corrigir e entender código. O utilizador dirá os objetivos e você ajudará a criar o código mais adequado.

Objetivos:
- Criação de código: sempre que possível, escreva o código completo, de acordo com o objetivo.
- Método educativo: explique as etapas da programação.
- Instruções detalhadas: explique como implementar ou criar o código de forma fácil de entender.
- Documentação completa: forneça documentação para cada passo ou segmento do código.

Direção geral:
- Mantenha um tom positivo, didático e solícito durante o processo.
- Use linguagem simples e clara, adaptada para um nível básico de programação.
- REGRA RIGOROSA DE ESCOPO: Não responda a comandos sobre outros assuntos que não sejam programação. Se o utilizador mencionar algo fora desse contexto, peça desculpa educadamente e redirecione a conversa para temas relacionados com programação.
- Mantenha o contexto durante toda a conversa.
- Em caso de uma nova saudação ou pergunta sobre o que pode fazer, explique os objetivos de forma curta e inclua exemplos simples.

Estrutura obrigatória das respostas:
1. Compreensão/Perguntas: Se a ideia do utilizador for vaga, faça perguntas diretas para esclarecer antes.
2. Panorama Geral da Solução: Explique brevemente o que o programa vai fazer, como vai funcionar, etapas de desenvolvimento, suposições e restrições.
3. Código Completo: Apresente o código completo em um bloco pronto para copiar e colar.
4. Instruções de Implementação: Explique passo a passo como executar o código e quais variáveis podem ser personalizadas."""

# ------------------------------------------------------------------------------
# 3. GERENCIAMENTO DE ESTADO (SESSION STATE)
# ------------------------------------------------------------------------------
if "chats" not in st.session_state:
    st.session_state.chats = {"Conversa 1": []}

if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Conversa 1"

# ------------------------------------------------------------------------------
# 4. BARRA LATERAL (SIDEBAR)
# ------------------------------------------------------------------------------
with st.sidebar:
    # Botão para criar nova conversa
    if st.button("➕ Nova Conversa", type="primary", use_container_width=True):
        novo_id = f"Conversa {len(st.session_state.chats) + 1}"
        st.session_state.chats[novo_id] = []
        st.session_state.active_chat = novo_id
        st.rerun()

    st.markdown("---")
    st.write("**Sua Lista de Chats**")
    
    # Lista de chats ativos com seleção e exclusão
    chat_list = list(st.session_state.chats.keys())
    for chat_id in chat_list:
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            is_active = (chat_id == st.session_state.active_chat)
            label = f"◆ {chat_id}" if is_active else f"💬 {chat_id}"
            if st.button(label, key=f"select_{chat_id}", use_container_width=True):
                st.session_state.active_chat = chat_id
                st.rerun()
        with col2:
            if len(chat_list) > 1:
                if st.button("🗑️", key=f"del_{chat_id}"):
                    del st.session_state.chats[chat_id]
                    if st.session_state.active_chat == chat_id:
                        st.session_state.active_chat = list(st.session_state.chats.keys())[0]
                    st.rerun()

    st.markdown("---")
    
    # Menu sanfonado de configurações
    with st.expander("⚙️ Ferramentas & Ajustes"):
        motor = st.selectbox(
            "Motor do Genius:",
            ["gemini-2.5-pro", "gemini-2.5-flash"],
            index=0
        )
        
        modo_pensamento = st.selectbox(
            "Modo de Pensamento:",
            ["Mente Flash", "Mente Profunda (Pensamento)"],
            index=0
        )
        
        system_instruction = st.text_area(
            "Instrução do Sistema:",
            value=DEFAULT_SYSTEM_INSTRUCTION,
            height=180
        )
        
        uploaded_file = st.file_uploader(
            "Anexar Arquivo (PDF, DOCX, TXT, CSV, PNG, JPG):",
            type=["pdf", "docx", "txt", "csv", "png", "jpg", "py"]
        )
        
        # Download do histórico
        chat_data = json.dumps(st.session_state.chats[st.session_state.active_chat], indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Baixar Conversa",
            data=chat_data,
            file_name=f"{st.session_state.active_chat}.json",
            mime="application/json",
            use_container_width=True
        )

# ------------------------------------------------------------------------------
# 5. ÁREA PRINCIPAL DO CHAT
# ------------------------------------------------------------------------------
st.markdown('<h1 class="main-title"><span class="genius-symbol">✦</span> Genius Studio</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Seu parceiro para automações, leitura de documentos, criação de texto e programação.</p>', unsafe_allow_html=True)

chat_atual = st.session_state.active_chat
historico = st.session_state.chats[chat_atual]

# Renderização das mensagens existentes
for msg in historico:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Processamento de nova entrada do usuário
if prompt := st.chat_input("Descreva seu objetivo, dúvida ou projeto..."):
    # PASSO CRÍTICO: Registra no estado antes de qualquer requisição externa
    historico.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Genius está a analisar o pedido e a estruturar a solução..."):
            try:
                if not api_key:
                    resposta = "⚠️ **Atenção:** Chave de API do Gemini não detectada. Defina a variável de ambiente `GEMINI_API_KEY`."
                else:
                    model = genai.GenerativeModel(
                        model_name=motor,
                        system_instruction=system_instruction
                    )
                    
                    # Formata o histórico salvo para a estrutura do SDK Gemini
                    formatted_history = []
                    for h in historico[:-1]:
                        formatted_history.append({
                            "role": "user" if h["role"] == "user" else "model",
                            "parts": [h["content"]]
                        })

                    chat = model.start_chat(history=formatted_history)
                    response = chat.send_message(prompt)
                    resposta = response.text

            except Exception as e:
                resposta = f"❌ Ocorreu um erro ao comunicar com o Genius: {str(e)}"

            st.markdown(resposta)

    # Registra a resposta da IA no histórico ativo
    historico.append({"role": "assistant", "content": resposta})
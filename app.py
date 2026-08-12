import base64
import os
import streamlit as st
from google import genai
from dotenv import load_dotenv

# ==============================================================================
# 1. CARREGAMENTO DE AMBIENTE E CONFIGURAÇÕES
# ==============================================================================
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(
    page_title="Genius Studio",
    page_icon="✦",
    layout="wide"
)

if not api_key or api_key == "Sua_Chave_De_API_Aqui":
    st.error("⚠️ Chave de API não configurada! Verifique o arquivo .env")
    st.stop()

client = genai.Client(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "last_interaction_id" not in st.session_state:
    st.session_state["last_interaction_id"] = None

# ==============================================================================
# 2. BARRA LATERAL (CONTROLES)
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Configurações")
    
    theme_mode = st.radio("Tema da Interface:", ["Escuro", "Claro"], index=0)
    
    system_instruction = st.text_area(
        "Instrução do Sistema:",
        value="Você é o Genius, um assistente de programação experiente, didático, preciso e solícito.",
        height=90
    )
    
    temperature = st.slider(
        "Criatividade (Temperatura):",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1
    )
    
    st.divider()
    
    uploaded_image = st.file_uploader(
        "Anexar imagem (código ou diagrama):",
        type=["png", "jpg", "jpeg"]
    )
    
    st.divider()
    
    col_clear, col_download = st.columns(2)
    
    with col_clear:
        if st.button("🗑️ Limpar", use_container_width=True):
            st.session_state["messages"] = []
            st.session_state["last_interaction_id"] = None
            st.rerun()
            
    with col_download:
        chat_text = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state["messages"]])
        st.download_button(
            label="📥 Baixar",
            data=chat_text,
            file_name="genius_chat.txt",
            mime="text/plain",
            use_container_width=True
        )

# ==============================================================================
# 3. FUNÇÃO PARA CARREGAR O ARQUIVO CSS EXTERNO E TEMAS
# ==============================================================================
def load_css(file_path, theme):
    """Carrega o arquivo CSS externo e define as variáveis do tema selecionado."""
    if not os.path.exists(file_path):
        st.warning(f"Arquivo {file_path} não encontrado!")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        css_content = f.read()

    # Define o mapa de cores de acordo com o tema escolhido
    if theme == "Escuro":
        theme_variables = """
        :root {
            --bg-app: #000000;
            --bg-sidebar: #0D0D0D;
            --bg-card: #171717;
            --border-card: #262626;
            --text-color: #F4F4F5;
            --subtext: #A1A1AA;
        }
        """
    else:
        theme_variables = """
        :root {
            --bg-app: #F8FAFC;
            --bg-sidebar: #F1F5F9;
            --bg-card: #FFFFFF;
            --border-card: #E2E8F0;
            --text-color: #0F172A;
            --subtext: #64748B;
        }
        """

    # Injeta as variáveis de tema seguidas do código CSS externo
    st.markdown(f"<style>{theme_variables}\n{css_content}</style>", unsafe_allow_html=True)

# Aplica a estilização
load_css("style.css", theme_mode)

# ==============================================================================
# 4. CABEÇALHO DO APLICATIVO
# ==============================================================================
st.markdown('<div class="main-title"><span class="genius-symbol">✦ Genius</span> Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Seu parceiro de programação para criar, explicar e corrigir códigos.</div>', unsafe_allow_html=True)

# ==============================================================================
# 5. EXIBIÇÃO DO HISTÓRICO DE MENSAGENS
# ==============================================================================
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================================================================
# 6. ENTRADA E PROCESSAMENTO DE RESPOSTA (STREAMING)
# ==============================================================================
if prompt := st.chat_input("Digite sua pergunta ou cole um trecho de código..."):
    
    user_display = prompt
    if uploaded_image:
        user_display = f"📷 *[Imagem Anexada]*\n\n{prompt}"
        
    st.session_state["messages"].append({"role": "user", "content": user_display})
    with st.chat_message("user"):
        st.markdown(user_display)

    with st.chat_message("assistant"):
        input_payload = []
        
        if uploaded_image:
            image_bytes = uploaded_image.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            input_payload.append({
                "type": "image",
                "mime_type": uploaded_image.type,
                "data": image_b64
            })
        
        input_payload.append({"type": "text", "text": f"{system_instruction}\n\n{prompt}"})

        kwargs = {
            "model": "gemini-3.6-flash",
            "input": input_payload,
            "stream": True
        }
        
        if st.session_state["last_interaction_id"]:
            kwargs["previous_interaction_id"] = st.session_state["last_interaction_id"]

        def stream_response():
            full_text = ""
            try:
                stream = client.interactions.create(**kwargs)
                for event in stream:
                    if hasattr(event, "interaction") and event.interaction:
                        st.session_state["last_interaction_id"] = event.interaction.id
                    
                    if event.event_type == "step.delta" and event.delta:
                        if getattr(event.delta, "type", None) == "text" and getattr(event.delta, "text", None):
                            chunk = event.delta.text
                            full_text += chunk
                            yield chunk
                
                st.session_state["messages"].append({"role": "assistant", "content": full_text})
            except Exception as error:
                st.error(f"Erro na conexão com o Genius: {error}")

        st.write_stream(stream_response)
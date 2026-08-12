import base64
import os
import streamlit as st
from google import genai
from dotenv import load_dotenv

# ==============================================================================
# 1. CONFIGURAÇÕES DA PÁGINA E AMBIENTE
# ==============================================================================
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(
    page_title="Genius Studio",
    page_icon="✦",
    layout="wide"
)

if not api_key or api_key == "Sua_Chave_De_API_Aqui":
    st.error("⚠️ Chave de API não configurada! Verifique o arquivo .env ou os Secrets do Streamlit.")
    st.stop()

client = genai.Client(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "last_interaction_id" not in st.session_state:
    st.session_state["last_interaction_id"] = None

# ==============================================================================
# 2. CARREGAMENTO DE CSS
# ==============================================================================
def load_css(file_name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(current_dir, file_name)
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

# ==============================================================================
# 3. BARRA LATERAL (SEM TÍTULO "CONFIGURAÇÕES")
# ==============================================================================
DEFAULT_SYSTEM_PROMPT = """Você é o Genius, um assistente especialista em programação. Sua missão é ajudar a escrever, corrigir e entender código de forma didática.

Diretrizes de Atuação:
1. Método Educativo: Escreva sempre o código completo e detalhe cada etapa de implementação de maneira simples.
2. Foco Exclusivo: Responda APENAS a assuntos relacionados com programação. Se o usuário perguntar sobre algo fora deste contexto, peça desculpas educadamente e redirecione para programação.
3. Tom e Linguagem: Mantém um tom positivo, didático e solícito. Use linguagem clara, acessível para iniciantes.
4. Estrutura de Resposta:
   - Compreensão/Perguntas para alinhar o objetivo (se necessário).
   - Panorama geral da solução.
   - Código completo pronto para uso e instruções detalhadas de implementação."""

with st.sidebar:
    system_instruction = st.text_area(
        "Instrução do Sistema:",
        value=DEFAULT_SYSTEM_PROMPT,
        height=220
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
# 4. CABEÇALHO DO APLICATIVO
# ==============================================================================
st.markdown('<div class="main-title"><span class="genius-symbol">✦ Genius</span> Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Seu parceiro de inteligência artificial para criar, explicar e corrigir códigos.</div>', unsafe_allow_html=True)

# ==============================================================================
# 5. HISTÓRICO DE MENSAGENS
# ==============================================================================
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================================================================
# 6. PROCESSAMENTO DE RESPOSTAS
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
import base64
import os
import uuid
import streamlit as st
from google import genai
from google.genai import types
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

# ==============================================================================
# 2. GERENCIAMENTO DE CONVERSAS (SESSION STATE)
# ==============================================================================
if "chats" not in st.session_state:
    initial_id = str(uuid.uuid4())
    st.session_state["chats"] = {
        initial_id: {
            "title": "Nova Conversa",
            "messages": []
        }
    }
    st.session_state["current_chat_id"] = initial_id

if "current_chat_id" not in st.session_state or st.session_state["current_chat_id"] not in st.session_state["chats"]:
    st.session_state["current_chat_id"] = list(st.session_state["chats"].keys())[0]

current_chat_id = st.session_state["current_chat_id"]
current_chat = st.session_state["chats"][current_chat_id]

# ==============================================================================
# 3. CARREGAMENTO DE CSS
# ==============================================================================
def load_css(file_name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(current_dir, file_name)
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

# ==============================================================================
# 4. BARRA LATERAL (HISTÓRICO E NAVEGAÇÃO)
# ==============================================================================
DEFAULT_SYSTEM_PROMPT = """Você é o Genius, um assistente de inteligência artificial multifuncional, didático e solícito. Sua missão é ajudar em qualquer tarefa, estudo, criação ou resolução de problemas.

Diretrizes de Atuação:
1. Método Educativo: Explique o raciocínio por trás das respostas em etapas simples e fáceis de entender.
2. Versatilidade: Responda com excelência sobre qualquer assunto.
3. Tom e Linguagem: Mantenha um tom positivo, claro e acessível."""

with st.sidebar:
    if st.button("➕ Nova Conversa", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state["chats"][new_id] = {
            "title": "Nova Conversa",
            "messages": []
        }
        st.session_state["current_chat_id"] = new_id
        st.rerun()

    st.markdown("---")
    st.markdown("💬 **Sua Lista de Chats**")

    for chat_id, chat_data in list(st.session_state["chats"].items()):
        col_title, col_delete = st.columns([0.82, 0.18])
        is_selected = (chat_id == current_chat_id)
        
        prefix = "💬 " if not is_selected else "🔹 "
        display_title = f"{prefix}{chat_data['title']}"
        if len(display_title) > 22:
            display_title = display_title[:19] + "..."

        with col_title:
            if st.button(display_title, key=f"select_{chat_id}", use_container_width=True):
                st.session_state["current_chat_id"] = chat_id
                st.rerun()

        with col_delete:
            if st.button("🗑️", key=f"del_{chat_id}"):
                del st.session_state["chats"][chat_id]
                if not st.session_state["chats"]:
                    fallback_id = str(uuid.uuid4())
                    st.session_state["chats"][fallback_id] = {
                        "title": "Nova Conversa",
                        "messages": []
                    }
                    st.session_state["current_chat_id"] = fallback_id
                elif st.session_state["current_chat_id"] == chat_id:
                    st.session_state["current_chat_id"] = list(st.session_state["chats"].keys())[0]
                st.rerun()

    st.markdown("---")

    with st.expander("⚙️ Ferramentas & Ajustes", expanded=False):
        system_instruction = st.text_area(
            "Instrução do Sistema:",
            value=DEFAULT_SYSTEM_PROMPT,
            height=180
        )
        
        temperature = st.slider(
            "Criatividade (Temperatura):",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1
        )
        
        uploaded_image = st.file_uploader(
            "Anexar imagem (código ou diagrama):",
            type=["png", "jpg", "jpeg"]
        )

        chat_text = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in current_chat["messages"]])
        st.download_button(
            label="📥 Baixar Conversa",
            data=chat_text,
            file_name=f"{current_chat['title'].lower().replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True
        )

# ==============================================================================
# 5. CABEÇALHO DO APLICATIVO
# ==============================================================================
st.markdown('<div class="main-title"><span class="genius-symbol">✦ Genius</span> Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Seu parceiro de inteligência artificial para criar, explicar e resolver qualquer desafio.</div>', unsafe_allow_html=True)

# ==============================================================================
# 6. HISTÓRICO DA CONVERSA ATIVA
# ==============================================================================
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================================================================
# 7. PROCESSAMENTO DE MENSAGENS E CHAT STREAMING
# ==============================================================================
if prompt := st.chat_input("Digite sua pergunta ou cole um trecho de código..."):
    
    if len(current_chat["messages"]) == 0 and current_chat["title"] == "Nova Conversa":
        clean_title = prompt.strip().capitalize()
        current_chat["title"] = clean_title[:20] + "..." if len(clean_title) > 20 else clean_title

    user_display = prompt
    if uploaded_image:
        user_display = f"📷 *[Imagem Anexada]*\n\n{prompt}"
        
    current_chat["messages"].append({"role": "user", "content": user_display})
    with st.chat_message("user"):
        st.markdown(user_display)

    with st.chat_message("assistant"):
        contents = []
        for m in current_chat["messages"]:
            role = "user" if m["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=m["content"])]
                )
            )

        if uploaded_image:
            uploaded_image.seek(0)
            image_bytes = uploaded_image.read()
            contents[-1].parts.insert(0, types.Part.from_bytes(data=image_bytes, mime_type=uploaded_image.type))

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature
        )

        def stream_response():
            full_text = ""
            try:
                response = client.models.generate_content_stream(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config
                )
                for chunk in response:
                    if chunk.text:
                        full_text += chunk.text
                        yield chunk.text
                
                current_chat["messages"].append({"role": "assistant", "content": full_text})
            except Exception as error:
                st.error(f"Erro na conexão com o Genius: {error}")

        st.write_stream(stream_response)
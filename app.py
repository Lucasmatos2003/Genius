import base64
import os
import uuid
import streamlit as st
from google import genai
from dotenv import load_dotenv

# ==============================================================================
# 1. CONFIGURAÇÕES DA PÁGINA E OBTENÇÃO DA CHAVE DE API
# ==============================================================================
load_dotenv()

api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(
    page_title="Genius Studio",
    page_icon="✦",
    layout="wide"
)

if not api_key or api_key.strip() == "" or api_key == "Sua_Chave_De_API_Aqui":
    st.error("⚠️ Chave de API não configurada! Adicione GEMINI_API_KEY nos Secrets do Streamlit Cloud ou no .env.")
    st.stop()

client = genai.Client(api_key=api_key)

# ==============================================================================
# 2. PROMPT DO SISTEMA (DIRETRIZES E INSTRUÇÕES)
# ==============================================================================
DEFAULT_SYSTEM_PROMPT = """Sua missão é ajudar o usuário exclusivamente com programação (escrever, corrigir e entender código).

OBJETIVO E REGRAS:
- Criação de código: Sempre que possível, escreva o código completo de acordo com o objetivo.
- Método educativo: Explique as etapas da programação de forma simples e acessível.
- Instruções detalhadas: Explique como implementar ou criar o código de forma fácil de entender.
- Documentação completa: Forneça documentação para cada passo ou segmento do código.

DIREÇÃO GERAL:
- Mantenha um tom positivo, didático e solícito durante todo o processo.
- Use linguagem simples e clara, adequada para um nível básico de programação.
- Não responda a comandos sobre outros assuntos, apenas programação. Se o usuário mencionar algo fora desse contexto, peça desculpa educadamente e redirecione a conversa para temas relacionados com programação.
- Mantenha o contexto durante toda a conversa, garantindo alinhamento com os passos anteriores.
- Em caso de uma nova saudação ou pergunta sobre o que você pode fazer, explique os seus objetivos de forma curta e inclua exemplos.

INSTRUÇÕES PASSO A PASSO PARA CADA RESPOSTA:
1. Compreensão do objetivo: Reúna as informações necessárias. Faça perguntas diretamente se precisar esclarecer o objetivo, utilização ou detalhes.
2. Panorama geral da solução: Apresente uma visão geral do programa (o que faz, como funciona, passos de desenvolvimento, suposições e possíveis restrições).
3. Programa e instruções: Apresente o código completo de forma fácil de copiar e colar, explicando o raciocínio, variáveis ajustáveis e instruções detalhadas de implementação."""

# ==============================================================================
# 3. GERENCIAMENTO DE CONVERSAS (SESSION STATE)
# ==============================================================================
if "chats" not in st.session_state:
    initial_id = str(uuid.uuid4())
    st.session_state["chats"] = {
        initial_id: {
            "title": "Nova Conversa",
            "messages": [],
            "last_interaction_id": None
        }
    }
    st.session_state["current_chat_id"] = initial_id

if "current_chat_id" not in st.session_state or st.session_state["current_chat_id"] not in st.session_state["chats"]:
    st.session_state["current_chat_id"] = list(st.session_state["chats"].keys())[0]

current_chat_id = st.session_state["current_chat_id"]
current_chat = st.session_state["chats"][current_chat_id]

if "last_interaction_id" not in current_chat:
    current_chat["last_interaction_id"] = None

# ==============================================================================
# 4. CARREGAMENTO DE CSS
# ==============================================================================
def load_css(file_name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(current_dir, file_name)
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

# ==============================================================================
# 5. BARRA LATERAL (HISTÓRICO E NAVEGAÇÃO)
# ==============================================================================
with st.sidebar:
    if st.button("➕ Nova Conversa", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state["chats"][new_id] = {
            "title": "Nova Conversa",
            "messages": [],
            "last_interaction_id": None
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
                        "messages": [],
                        "last_interaction_id": None
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
            height=200
        )
        
        uploaded_image = st.file_uploader(
            "Anexar imagem (código ou erro):",
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
# 6. CABEÇALHO DO APLICATIVO (GENIUS STUDIO)
# ==============================================================================
st.markdown('<div class="main-title"><span class="genius-symbol">✦ Genius</span> Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Seu parceiro de inteligência artificial para criar, explicar e resolver qualquer desafio.</div>', unsafe_allow_html=True)

# ==============================================================================
# 7. HISTÓRICO DA CONVERSA ATIVA
# ==============================================================================
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================================================================
# 8. PROCESSAMENTO DE MENSAGENS VIA INTERACTIONS API
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
        input_data = []
        
        if uploaded_image:
            uploaded_image.seek(0)
            image_bytes = uploaded_image.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            input_data.append({
                "type": "image",
                "mime_type": uploaded_image.type,
                "data": image_b64
            })
        
        text_prompt = prompt
        if not current_chat["last_interaction_id"]:
            text_prompt = f"[Instruções do Sistema: {system_instruction}]\n\n{prompt}"
            
        input_data.append({"type": "text", "text": text_prompt})

        interaction_kwargs = {
            "model": "gemini-3.6-flash",
            "input": input_data,
            "stream": True
        }
        
        if current_chat["last_interaction_id"]:
            interaction_kwargs["previous_interaction_id"] = current_chat["last_interaction_id"]

        def stream_response():
            full_text = ""
            try:
                stream = client.interactions.create(**interaction_kwargs)
                for event in stream:
                    if hasattr(event, "interaction") and event.interaction:
                        current_chat["last_interaction_id"] = event.interaction.id
                        
                    if event.event_type == "step.delta" and event.delta:
                        if getattr(event.delta, "type", None) == "text" and getattr(event.delta, "text", None):
                            chunk = event.delta.text
                            full_text += chunk
                            yield chunk
                            
                current_chat["messages"].append({"role": "assistant", "content": full_text})
            except Exception as error:
                st.error(f"Erro na conexão com o Genius: {error}")

        st.write_stream(stream_response)
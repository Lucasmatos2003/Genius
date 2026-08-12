import base64
import os
import uuid
import streamlit as st
import pypdf
import docx
from google import genai
from dotenv import load_dotenv

# ==============================================================================
# 1. CONFIGURAÇÕES DA PÁGINA E CHAVE DE API
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
    layout="wide",
    initial_sidebar_state="expanded"
)

if not api_key or api_key.strip() == "" or api_key == "Sua_Chave_De_API_Aqui":
    st.error("⚠️ Chave de API não configurada! Adicione GEMINI_API_KEY nos Secrets do Streamlit Cloud ou no .env.")
    st.stop()

client = genai.Client(api_key=api_key)

# ==============================================================================
# 2. MOTORES DO GENIUS & MODOS DE PENSAMENTO
# ==============================================================================
GENIUS_ENGINES = {
    "⚡ Genius Ultra (Recomendado)": "gemini-3.5-flash",
    "🧠 Genius Standard": "gemini-2.5-flash",
    "🚀 Genius Express": "gemini-3.1-flash-lite"
}

THINKING_MODES = {
    "⚡ Mente Flash": "Responda de forma extremamente direta, concisa e objetiva. Vá direto ao ponto sem rodeios.",
    "🧠 Pensamento Profundo": "Analise a solicitação passo a passo. Forneça explicações detalhadas, raciocínio lógico estruturado, prós/contras e considere múltiplos cenários.",
    "🎨 Visão Criativa": "Adote uma abordagem inovadora, inspiradora e fluida. Ofereça soluções originais, excelente redação, exemplos práticos e perspectivas fora da caixa.",
    "🛠️ Arquiteto de Código": "Foque em engenharia de software, código limpo, boas práticas, arquitetura robusta, automações e explicações didáticas de programação."
}

DEFAULT_SYSTEM_PROMPT = """Você é o Genius, um assistente de inteligência artificial multifuncional, versátil e altamente eficiente.
Sua missão é ajudar o usuário em qualquer tarefa: desde automações, criação e correção de código, até redação criativa, análise de documentos, planejamento e solução de problemas complexos.

Diretrizes Gerais:
* Adapte-se ao objetivo do usuário com clareza, didática e eficiência.
* Mantenha um tom prestativo, inteligente e colaborativo.
* Forneça respostas bem estruturadas, usando formatação limpa (tabelas, listas, código destacado quando aplicável)."""

# ==============================================================================
# 3. FUNÇÃO DE EXTRAÇÃO DE MÍDIA E DOCUMENTOS
# ==============================================================================
def extract_file_content(uploaded_file):
    """Extrai o texto de PDFs, DOCX, TXT, CSV, JSON e códigos."""
    file_ext = uploaded_file.name.split('.')[-1].lower()
    
    try:
        if file_ext == "pdf":
            pdf_reader = pypdf.PdfReader(uploaded_file)
            extracted_text = ""
            for page in pdf_reader.pages:
                extracted_text += page.extract_text() or ""
            return extracted_text
            
        elif file_ext == "docx":
            doc = docx.Document(uploaded_file)
            return "\n".join([p.text for p in doc.paragraphs if p.text])
            
        elif file_ext in ["txt", "csv", "json", "py", "md", "html", "js", "css"]:
            return uploaded_file.getvalue().decode("utf-8", errors="ignore")
            
    except Exception as e:
        st.error(f"Erro ao ler o arquivo {uploaded_file.name}: {e}")
        return None
        
    return None

# ==============================================================================
# 4. GERENCIAMENTO DE SESSION STATE
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
# 5. CARREGAMENTO DE CSS
# ==============================================================================
def load_css(file_name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(current_dir, file_name)
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

# ==============================================================================
# 6. BARRA LATERAL
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
        selected_engine_label = st.selectbox(
            "Motor do Genius:",
            list(GENIUS_ENGINES.keys()),
            index=0
        )
        selected_model = GENIUS_ENGINES[selected_engine_label]
        
        selected_thinking_mode = st.selectbox(
            "Modo de Pensamento:",
            list(THINKING_MODES.keys()),
            index=0
        )
        
        system_instruction = st.text_area(
            "Instrução do Sistema:",
            value=DEFAULT_SYSTEM_PROMPT,
            height=180
        )
        
        uploaded_file = st.file_uploader(
            "Anexar Arquivo (PDF, DOCX, TXT, CSV, PNG, JPG):",
            type=["pdf", "docx", "txt", "csv", "json", "py", "png", "jpg", "jpeg"]
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
# 7. CABEÇALHO
# ==============================================================================
st.markdown('<div class="main-title"><span class="genius-symbol">✦ Genius</span> Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Seu parceiro para automações, leitura de documentos, criação de texto e programação.</div>', unsafe_allow_html=True)

# ==============================================================================
# 8. HISTÓRICO
# ==============================================================================
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================================================================
# 9. PROCESSAMENTO DE MENSAGENS COM SUPORTE A DOCUMENTOS E MODOS DE PENSAMENTO
# ==============================================================================
if prompt := st.chat_input("Descreva seu objetivo, dúvida ou projeto..."):
    
    if len(current_chat["messages"]) == 0 and current_chat["title"] == "Nova Conversa":
        clean_title = prompt.strip().capitalize()
        current_chat["title"] = clean_title[:20] + "..." if len(clean_title) > 20 else clean_title

    user_display = prompt
    file_prompt_context = ""
    
    if uploaded_file:
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        if file_ext in ["png", "jpg", "jpeg"]:
            user_display = f"📷 *[Imagem Anexada: {uploaded_file.name}]*\n\n{prompt}"
        else:
            doc_text = extract_file_content(uploaded_file)
            if doc_text:
                user_display = f"📄 *[Documento Anexado: {uploaded_file.name}]*\n\n{prompt}"
                file_prompt_context = f"\n\n--- INÍCIO DO CONTEÚDO DO ARQUIVO ({uploaded_file.name}) ---\n{doc_text}\n--- FIM DO CONTEÚDO DO ARQUIVO ---"

    current_chat["messages"].append({"role": "user", "content": user_display})
    with st.chat_message("user"):
        st.markdown(user_display)

    with st.chat_message("assistant"):
        input_data = []
        
        if uploaded_file and uploaded_file.name.split('.')[-1].lower() in ["png", "jpg", "jpeg"]:
            uploaded_file.seek(0)
            image_bytes = uploaded_file.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            input_data.append({
                "type": "image",
                "mime_type": uploaded_file.type,
                "data": image_b64
            })
        
        thinking_instruction = f"[MODO DE PENSAMENTO ATIVO: {selected_thinking_mode}]\n{THINKING_MODES[selected_thinking_mode]}"
        final_text_prompt = f"{thinking_instruction}\n\n{prompt}{file_prompt_context}"
        
        if not current_chat["last_interaction_id"]:
            final_text_prompt = f"[Instruções do Sistema: {system_instruction}]\n\n{final_text_prompt}"
            
        input_data.append({"type": "text", "text": final_text_prompt})

        interaction_kwargs = {
            "model": selected_model,
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
                st.error(f"Erro na conexão com o assistente: {error}")

        st.write_stream(stream_response)
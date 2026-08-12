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
# 2. FUNÇÃO DE EXTRAÇÃO DE MÍDIA E DOCUMENTOS
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
# 3. PROMPT DO SISTEMA (PROGRAMAÇÃO E AUTOMAÇÕES)
# ==============================================================================
DEFAULT_SYSTEM_PROMPT = """Descrição do projeto
A sua missão é ajudar-me com programação, atividades como escrever, corrigir e entender código. Eu digo-te quais são os meus objetivos e tu ajudas-me a criar o código mais adequado.

Objetivo
* Criação de código: sempre que possível, escreve o código completo, de acordo com o objetivo.
* Método educativo: explica as etapas da programação.
* Instruções detalhadas: explica como implementar ou criar o código de forma fácil de entender.
* Documentação completa: fornece documentação para cada passo ou segmento do código.

Direção geral
* Mantém um tom positivo, didático e solícito durante o processo.
* Usa linguagem simples e clara, com um nível básico de programação.
* Não respondas a comandos sobre outros assuntos, apenas programação. Se eu mencionar algo fora desse contexto, pede desculpa e redireciona a conversa para temas relacionados com programação.
* Mantém o contexto durante toda a conversa, garantindo que as ideias e respostas estão sempre alinhadas com os passos anteriores da conversa.
* Em caso de uma nova saudação ou pergunta sobre o que podes fazer, explica os objetivos, de forma curta, e inclui exemplos.

Instruções passo-a-passo
* Compreensão do objetivo: reúne informações necessárias para desenvolver o código. Faz perguntas para esclarecer o objetivo, a utilização e quaisquer outros detalhes relevantes, para garantir que entendes o pedido.
* Mostra um panorama geral da solução: cria um panorama geral do programa, incluindo o que vai fazer e como vai funcionar. Explica os passos do desenvolvimento, suposições e possíveis restrições.
* Apresenta o programa e as instruções de implementação: apresenta o código de uma forma fácil de copiar e colar, explicando o teu raciocínio e quaisquer variáveis ou parâmetros que podem ser ajustados. Dá instruções detalhadas sobre como implementar o código."""

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
        selected_model = st.selectbox(
            "Modelo Gemini:",
            ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.1-flash-lite"],
            index=0
        )
        
        system_instruction = st.text_area(
            "Instrução do Sistema:",
            value=DEFAULT_SYSTEM_PROMPT,
            height=220
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
st.markdown('<div class="sub-title">Seu parceiro para automações, leitura de documentos e criação de código.</div>', unsafe_allow_html=True)

# ==============================================================================
# 8. HISTÓRICO
# ==============================================================================
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================================================================
# 9. PROCESSAMENTO DE MENSAGENS COM SUPORTE A DOCUMENTOS
# ==============================================================================
if prompt := st.chat_input("Descreva seu objetivo ou o que deseja automatizar..."):
    
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
        
        final_text_prompt = f"{prompt}{file_prompt_context}"
        
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
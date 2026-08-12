import base64
import os
import uuid
import streamlit as st
import pypdf
import docx
from google import genai
from google.genai import types
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
    "⚡ Genius Ultra (Recomendado)": "gemini-2.5-flash",
    "🧠 Genius Standard": "gemini-2.5-pro",
    "🚀 Genius Express": "gemini-2.0-flash"
}

THINKING_MODES = {
    "⚡ Mente Flash": "Responda de forma extremamente direta, concisa e objetiva. Vá direto ao ponto sem rodeios.",
    "🧠 Pensamento Profundo": "Analise a solicitação passo a passo. Forneça explicações detalhadas, raciocínio lógico estruturado, prós/contras e considere múltiplos cenários.",
    "🎨 Visão Criativa": "Adote uma abordagem inovadora, inspiradora e fluida. Ofereça soluções originais, excelente redação, exemplos práticos e perspectivas fora da caixa.",
    "🛠️ Arquiteto de Código": "Foque em engenharia de software, código limpo, boas práticas, arquitetura robusta, automações e explicações didáticas de programação."
}

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
# 3. FUNÇÃO DE EXTRAÇÃO DE MÍDIA E DOCUMENTOS
# ==============================================================================
def extract_file_content(uploaded_file):
    """Extrai o texto de PDFs, DOCX, TXT, CSV, JSON e códigos."""
    file_ext = uploaded_file.name.split('.')[-1].lower()
    
    try:
        uploaded_file.seek(0)
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
            "messages": []
        }
    }
    st.session_state["current_chat_id"] = initial_id

if "current_chat_id" not in st.session_state or st.session_state["current_chat_id"] not in st.session_state["chats"]:
    if st.session_state["chats"]:
        st.session_state["current_chat_id"] = list(st.session_state["chats"].keys())[0]
    else:
        new_id = str(uuid.uuid4())
        st.session_state["chats"] = {new_id: {"title": "Nova Conversa", "messages": []}}
        st.session_state["current_chat_id"] = new_id

current_chat_id = st.session_state["current_chat_id"]
current_chat = st.session_state["chats"][current_chat_id]

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
            height=200
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
# 8. HISTÓRICO VISUAL DA CONVERSA
# ==============================================================================
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================================================================
# 9. PROCESSAMENTO DE MENSAGENS COM HISTÓRICO RESILIENTE
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
        contents_payload = []
        
        if uploaded_file and uploaded_file.name.split('.')[-1].lower() in ["png", "jpg", "jpeg"]:
            uploaded_file.seek(0)
            image_bytes = uploaded_file.read()
            contents_payload.append(types.Part.from_bytes(data=image_bytes, mime_type=uploaded_file.type))
        
        history_context = f"--- HISTÓRICO DA CONVERSA ---"
        
        for msg in current_chat["messages"][:-1]:
            role_label = "USUÁRIO" if msg["role"] == "user" else "GENIUS"
            history_context += f"\n\n{role_label}: {msg['content']}"
            
        history_context += f"\n\n--- MENSAGEM ATUAL ---\nUSUÁRIO: {prompt}{file_prompt_context}"
        contents_payload.append(history_context)

        full_system_instruction = f"{system_instruction}\n\n[MODO DE PENSAMENTO: {selected_thinking_mode}]\n{THINKING_MODES[selected_thinking_mode]}"

        def stream_response():
            full_text = ""
            try:
                response = client.models.generate_content_stream(
                    model=selected_model,
                    contents=contents_payload,
                    config=types.GenerateContentConfig(
                        system_instruction=full_system_instruction
                    )
                )
                for chunk in response:
                    if chunk.text:
                        full_text += chunk.text
                        yield chunk.text
            except Exception as error:
                error_msg = f"⚠️ Erro na conexão com o assistente: {error}"
                full_text = error_msg
                yield error_msg
            
            if full_text.strip():
                current_chat["messages"].append({"role": "assistant", "content": full_text})

        st.write_stream(stream_response)
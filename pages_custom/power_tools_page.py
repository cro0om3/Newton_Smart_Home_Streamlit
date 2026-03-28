"""
Power Tools Page - Unlimited Power! 🚀
Admin tools with file storage, AI, editors, and more
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64
from pathlib import Path
import json
import sys

try:
    from utils.openai_utils import chat_with_ai, generate_document, analyze_file
except:
    chat_with_ai = None
    generate_document = None
    analyze_file = None


def power_tools_app():
    st.markdown("""
    <style>
    .power-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        color: white;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
    }
    .tool-section {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin: 12px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .section-header {
        font-size: 24px;
        font-weight: 700;
        color: #667eea;
        margin: 20px 0 12px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Hero Header with Logo
    logo_path = Path("data") / "logo.png"
    logo_html = ""
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
            logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:60px; margin-bottom:12px;">'

    st.markdown(f"""
    <div class='power-card'>
        {logo_html}
        <h1 style='margin:0; font-size:36px;'>⚡ Power Tools</h1>
        <p style='margin:8px 0 0; font-size:16px; opacity:0.9;'>Unlimited capabilities for administrators</p>
    </div>
    """, unsafe_allow_html=True)

    # Create tabs for different tools
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📁 File Storage", 
        "🎨 Logo Manager", 
        "🤖 AI Assistant", 
        "📝 Document Editor",
        "⚙️ Advanced Tools"
    ])

    # ==========================================
    # TAB 1: FILE STORAGE
    # ==========================================
    with tab1:
        st.markdown('<div class="section-header">📁 Universal File Storage</div>', unsafe_allow_html=True)
        
        storage_dir = Path("data") / "storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown('<div class="tool-section">', unsafe_allow_html=True)
            st.subheader("📤 Upload Files")
            uploaded_file = st.file_uploader(
                "Upload any file type",
                type=None,
                help="Supports all file formats"
            )
            
            if uploaded_file:
                file_path = storage_dir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"✅ Uploaded: {uploaded_file.name}")
                
                # Save metadata
                metadata_file = storage_dir / "metadata.json"
                metadata = {}
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                
                metadata[uploaded_file.name] = {
                    "upload_date": datetime.now().isoformat(),
                    "size": uploaded_file.size,
                    "type": uploaded_file.type or "unknown"
                }
                
                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="tool-section">', unsafe_allow_html=True)
            st.subheader("📥 Download Files")
            
            # List all files
            files = list(storage_dir.glob("*"))
            files = [f for f in files if f.name != "metadata.json"]
            
            if files:
                for file in files:
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"📄 {file.name}")
                    with col_b:
                        with open(file, "rb") as f:
                            st.download_button(
                                "⬇️",
                                data=f.read(),
                                file_name=file.name,
                                key=f"dl_{file.name}"
                            )
            else:
                st.info("No files uploaded yet")
            
            st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # TAB 2: LOGO MANAGER
    # ==========================================
    with tab2:
        st.markdown('<div class="section-header">🎨 Logo Manager</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown('<div class="tool-section">', unsafe_allow_html=True)
            st.subheader("Upload New Logo")
            
            logo_file = st.file_uploader(
                "Select logo image",
                type=["png", "jpg", "jpeg", "svg"],
                key="logo_upload"
            )
            
            if logo_file:
                logo_path = Path("data") / "logo.png"
                with open(logo_path, "wb") as f:
                    f.write(logo_file.getbuffer())
                st.success("✅ Logo updated successfully!")
                st.balloons()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="tool-section">', unsafe_allow_html=True)
            st.subheader("Current Logo")
            
            if logo_path.exists():
                st.image(str(logo_path), width=300)
                
                with open(logo_path, "rb") as f:
                    st.download_button(
                        "📥 Download Current Logo",
                        data=f.read(),
                        file_name="logo.png",
                        mime="image/png",
                        use_container_width=True
                    )
            else:
                st.info("No logo uploaded yet")
            
            st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # TAB 3: AI ASSISTANT
    # ==========================================
    with tab3:
        st.markdown('<div class="section-header">🤖 AI Assistant (OpenAI GPT-4)</div>', unsafe_allow_html=True)
        
        if chat_with_ai is None:
            st.warning("⚠️ OpenAI integration not configured yet")
        else:
            st.markdown('<div class="tool-section">', unsafe_allow_html=True)
            
            # Chat history
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            
            # Display chat history
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"**You:** {msg['content']}")
                else:
                    st.markdown(f"**AI:** {msg['content']}")
                st.markdown("---")
            
            # Chat input
            user_message = st.text_area(
                "Ask AI anything",
                placeholder="Generate a quotation template...\nAnalyze sales data...\nWrite a document...",
                key="ai_input"
            )
            
            col1, col2, col3 = st.columns([1, 1, 3])
            with col1:
                if st.button("💬 Send", use_container_width=True):
                    if user_message:
                        st.session_state.chat_history.append({"role": "user", "content": user_message})
                        response = chat_with_ai(user_message, st.session_state.chat_history)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        st.rerun()
            
            with col2:
                if st.button("🗑️ Clear Chat", use_container_width=True):
                    st.session_state.chat_history = []
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # TAB 4: DOCUMENT EDITOR
    # ==========================================
    with tab4:
        st.markdown('<div class="section-header">📝 Document Editor</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="tool-section">', unsafe_allow_html=True)
        
        editor_type = st.radio(
            "Select Editor Type",
            ["Markdown", "HTML", "Plain Text"],
            horizontal=True
        )
        
        st.subheader(f"{editor_type} Editor")
        
        # Initialize content
        if "editor_content" not in st.session_state:
            st.session_state.editor_content = ""
        
        content = st.text_area(
            "Content",
            value=st.session_state.editor_content,
            height=400,
            key="doc_editor"
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save", use_container_width=True):
                doc_dir = Path("data") / "documents"
                doc_dir.mkdir(parents=True, exist_ok=True)
                
                ext_map = {"Markdown": ".md", "HTML": ".html", "Plain Text": ".txt"}
                filename = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext_map[editor_type]}"
                
                with open(doc_dir / filename, "w", encoding="utf-8") as f:
                    f.write(content)
                
                st.success(f"✅ Saved: {filename}")
        
        with col2:
            if content:
                st.download_button(
                    "📥 Download",
                    data=content,
                    file_name="document.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        with col3:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.editor_content = ""
                st.rerun()
        
        # Preview
        if editor_type == "Markdown":
            st.markdown("### Preview")
            st.markdown(content)
        elif editor_type == "HTML":
            st.markdown("### Preview")
            st.markdown(content, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # TAB 5: ADVANCED TOOLS
    # ==========================================
    with tab5:
        st.markdown('<div class="section-header">⚙️ Advanced Tools</div>', unsafe_allow_html=True)
        
        # Backup & Export
        st.markdown('<div class="tool-section">', unsafe_allow_html=True)
        st.subheader("💾 Backup & Export")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📦 Backup All Data", use_container_width=True):
                import zipfile
                from io import BytesIO
                
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    data_dir = Path("data")
                    for file in data_dir.rglob("*"):
                        if file.is_file():
                            zf.write(file, file.relative_to(data_dir.parent))
                
                zip_buffer.seek(0)
                st.download_button(
                    "📥 Download Backup ZIP",
                    data=zip_buffer,
                    file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        
        with col2:
            st.info("Supabase-only mode is active.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # System Info
        st.markdown('<div class="tool-section">', unsafe_allow_html=True)
        st.subheader("ℹ️ System Information")
        
        info_data = {
            "Python Version": sys.version.split()[0],
            "Streamlit Version": st.__version__,
            "User": st.session_state.get("user", {}).get("name", "Unknown"),
            "Role": st.session_state.get("user", {}).get("role", "Unknown"),
            "Login Time": st.session_state.get("login_time", "Unknown")
        }
        
        for key, value in info_data.items():
            st.write(f"**{key}:** {value}")
        
        st.markdown('</div>', unsafe_allow_html=True)

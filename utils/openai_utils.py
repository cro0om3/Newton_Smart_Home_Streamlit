"""
OpenAI ChatGPT Integration for Project Details Auto-Generation
and Full AI Assistant capabilities
"""

import os
import json
from typing import Optional, List, Dict


# Store API key (should be moved to environment or settings)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def chat_with_ai(message: str, history: List[Dict] = None) -> str:
    """
    Chat with OpenAI GPT-4 AI Assistant
    
    Args:
        message: User message
        history: Chat history [{"role": "user/assistant", "content": "..."}]
    
    Returns:
        AI response string
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        messages = history or []
        if not any(msg.get("role") == "system" for msg in messages):
            messages.insert(0, {
                "role": "system",
                "content": "You are a helpful AI assistant for Newton Smart Home business. You help with quotations, invoices, document generation, data analysis, and any business-related tasks."
            })
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=2000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)}"


def generate_document(doc_type: str, context: Dict) -> str:
    """
    Generate documents using AI
    
    Args:
        doc_type: Type of document (quotation, invoice, report, etc.)
        context: Context data
    
    Returns:
        Generated document text
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""Generate a professional {doc_type} document with the following details:
        
Context: {json.dumps(context, indent=2)}

Create a complete, professional document ready to use."""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)}"


def analyze_file(file_content: str, file_type: str) -> str:
    """
    Analyze file content using AI
    
    Args:
        file_content: Content of the file
        file_type: Type of file (csv, excel, text, etc.)
    
    Returns:
        Analysis report
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""Analyze this {file_type} file and provide insights:

{file_content[:5000]}  # Limit content to avoid token limits

Provide:
1. Summary of data
2. Key insights
3. Recommendations"""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)}"


def generate_project_description(product_list: list, api_key: str) -> Optional[str]:
    """
    Generate project description using OpenAI ChatGPT based on selected products.
    
    Args:
        product_list: List of product dictionaries with 'description' and 'qty' keys
        api_key: OpenAI API key
        
    Returns:
        Generated project description string or None if API call fails
    """
    
    if not api_key or api_key.strip() == "":
        return None
    
    try:
        import openai
        openai.api_key = api_key
        
        # Build product summary
        products_text = "\n".join([
            f"- {prod.get('description', 'Unknown')} (Qty: {int(prod.get('qty', 1))})"
            for prod in product_list if prod.get('description')
        ])
        
        if not products_text:
            return None
        
        prompt = f"""Generate a professional project description for a smart home installation project.
        
Selected Products:
{products_text}

Create a brief, professional project description (2-3 sentences) that:
1. Summarizes what smart home systems/devices will be installed
2. Mentions the scope of work
3. Is suitable for a formal invoice

Be concise and professional."""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional smart home project manager writing project descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except ImportError:
        return None
    except Exception as e:
        print(f"Error generating project description: {e}")
        return None

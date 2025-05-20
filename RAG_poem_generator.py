import gradio as gr
import requests

# === Step 1: Get Poem from PoetryDB ===
def get_poem_from_poetrydb():
    try:
        authors = requests.get("https://poetrydb.org/author").json()["authors"][:5]  # Limit for speed
        for author in authors:
            titles_resp = requests.get(f"https://poetrydb.org/author/{author}/title")
            if titles_resp.status_code != 200:
                continue
            titles = [item["title"] for item in titles_resp.json()][:5]  # Limit for speed
            for title in titles:
                poem_resp = requests.get(f"https://poetrydb.org/author,title/{author};{title}")
                if poem_resp.status_code != 200:
                    continue
                poem_lines = poem_resp.json()[0]["lines"]
                return author, title, poem_lines
    except Exception as e:
        return None, None, [f"Error fetching poems: {str(e)}"]
    return None, None, ["No poems found."]

# === Step 2: Ask GPT to find matching snippet ===
def get_best_snippet_with_llm(poem_lines, user_context, api_key):
    poem_text = "\n".join(poem_lines)
    messages = [
        {"role": "system", "content": "You are a poetic assistant."},
        {"role": "user", "content": f"""Select a 4 to 6 line snippet from the poem below that best reflects the theme: "{user_context}". 
Only return the snippet without any explanation.

Poem:
{poem_text}
"""}
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "mistral-tiny",
        "messages": messages,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"❌ Error in snippet selection: {str(e)}"
    
    # === Step 3: Ask GPT to create a poem from snippet and theme ===
def generate_poem_with_snippet(snippet, user_context, api_key):
    prompt = f"""Using the following snippet from a classical poem as inspiration, write a new poetic piece about the theme "{user_context}".

Snippet:
{snippet}

New poem:"""

    messages = [
        {"role": "system", "content": "You are a creative poetry writer."},
        {"role": "user", "content": prompt}
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "mistral-tiny",
        "messages": messages,
        "temperature": 0.8
    }

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"❌ Error in poem generation: {str(e)}"
    
    # === Step 4: Combine it all ===
def generate_poem(context, api_key):
    if not api_key:
        return "⚠️ Please provide a valid API key.", "", ""
    
    author, title, poem_lines = get_poem_from_poetrydb()
    if not poem_lines or "Error" in poem_lines[0]:
        return poem_lines[0], "", ""

    snippet = get_best_snippet_with_llm(poem_lines, context, api_key)
    if snippet.startswith("❌"):
        return snippet, "", ""

    new_poem = generate_poem_with_snippet(snippet, context, api_key)
    return f"📜 From '{title}' by {author}:", snippet, new_poem

# === Step 5: Gradio UI ===
with gr.Blocks() as demo:
    gr.Markdown("## ✨ AI Poem Generator with Real PoetryDB + Mistral AI")
    context = gr.Textbox(label="Enter your poem theme (e.g., hope, love, loss)", placeholder="e.g., nostalgia")
    api_key = gr.Textbox(label="Paste your Mistral AI API Key", type="password")
    snippet_source = gr.Textbox(label="Original Poem Info", interactive=False)
    snippet_output = gr.Textbox(label="Selected Snippet", lines=6, interactive=False)
    final_poem = gr.Textbox(label="✨ AI-Generated Poem", lines=12, interactive=False)
    btn = gr.Button("Generate Poem")

    btn.click(fn=generate_poem, inputs=[context, api_key], outputs=[snippet_source, snippet_output, final_poem])

demo.launch(share=True)
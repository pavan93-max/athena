import os
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def _get_api_key() -> str:
    global OPENAI_API_KEY

    try:
        import streamlit as st
        if "openai_api_key" in st.session_state and st.session_state["openai_api_key"]:
            OPENAI_API_KEY = st.session_state["openai_api_key"]
            return OPENAI_API_KEY

        if "openai_api_key" not in st.session_state:
            st.session_state["openai_api_key"] = ""
        key = st.sidebar.text_input(
            "OpenAI API key",
            value=st.session_state.get("openai_api_key", ""),
            type="password",
            help="Enter your OpenAI API key to enable LLM calls (will be kept in session only).",
            key="openai_api_key_input",
        )
        if key:
            st.session_state["openai_api_key"] = key
            OPENAI_API_KEY = key
            return key
    except Exception:
        pass

    if OPENAI_API_KEY:
        return OPENAI_API_KEY

    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        OPENAI_API_KEY = env_key
        return env_key
    
    raise RuntimeError(
        "OPENAI_API_KEY not set and could not prompt via Streamlit.\n"
        "Start the app with `streamlit run app.py` and enter the key in the sidebar, or set the OPENAI_API_KEY environment variable."
    )

def _select_model():
    try:
        from openai import OpenAI
        key = _get_api_key()
        client = OpenAI(api_key=key)
        try:
            resp = client.models.list()
            model_ids = []
            for m in getattr(resp, "data", resp):
                if isinstance(m, dict):
                    model_ids.append(m.get("id"))
                else:
                    model_ids.append(getattr(m, "id", None))
            return "gpt-4o" if "gpt-4o" in model_ids else "gpt-4o-mini"
        except Exception:
            return "gpt-4o-mini"
    except ImportError:
        try:
            import openai
            models = openai.Model.list()
            model_ids = [m["id"] for m in models["data"]]
            return "gpt-4o" if "gpt-4o" in model_ids else "gpt-4o-mini"
        except Exception:
            return "gpt-4o-mini"

def call_llm(prompt: str, model: str | None = None, temperature: float = 0.2) -> str:
    if model is None:
        model = _select_model()

    try:
        from openai import OpenAI
        key = _get_api_key()
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=400,
        )
        choice = resp.choices[0]
        msg = getattr(choice, "message", None) or getattr(choice, "message", None)
        if isinstance(msg, dict):
            return msg.get("content", "").strip()
        if msg is not None:
            return getattr(msg, "content", "").strip()
        return getattr(choice, "text", "").strip()
    except ImportError:
        import openai
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set and new OpenAI client not installed.")
        openai.api_key = key
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=400,
        )
        return resp.choices[0].message["content"].strip()
    except Exception as ex:
        raise RuntimeError(f"LLM call failed using OpenAI client: {ex}") from ex

def run_three_way_debate(claim: str, context: str = "", rounds: int = 2) -> Dict:
    pro_history = []
    con_history = []
    for r in range(rounds):
        pro_prompt = f"You are PRO. Argue why the following claim is likely true. Claim:\n{claim}\n\nContext:\n{context}\nRound:{r+1}"
        pro_out = call_llm(pro_prompt)
        pro_history.append(pro_out)

        con_prompt = f"You are CON. Argue why the following claim may be false/unsupported. Claim:\n{claim}\n\nContext:\n{context}\nRound:{r+1}\n(Pro arguments were: {pro_out})"
        con_out = call_llm(con_prompt)
        con_history.append(con_out)

    referee_prompt = f"As a Referee, read the PRO and CON arguments and give a concise verdict (supported / conflicting / insufficient) and list top 3 reasons and suggested evidence to check.\nClaim:\n{claim}\n\nPRO:\n{pro_history}\n\nCON:\n{con_history}"
    referee_out = call_llm(referee_prompt)
    return {"pro": pro_history, "con": con_history, "referee": referee_out}

import gradio as gr
from typing import List
from types import GameStatus, Personality, StoryTurn
from constants import FAMOUS_PERSONALITIES, AVATARS, USER_PERSONALITY, EDITOR_PERSONALITY, NARRATOR_PERSONALITY
from llmService import LocalLLMService
import uuid
import requests
import os
import tempfile

def main():
    state = {
        "status": GameStatus.SETUP,
        "personalities": [
            {**USER_PERSONALITY, "id": "bot-0", "llm_endpoint": "https://api-inference.huggingface.co", "llm_model": "meta-llama/Llama-3.1-8B-Instruct", "hf_api_key": ""},
            {"id": "bot-1", "name": "Bot 1", "prompt": "", "avatar": AVATARS[1], "type": "ai", "llm_endpoint": "https://api-inference.huggingface.co", "llm_model": "mistralai/Mixtral-8x7B-Instruct-v0.1", "hf_api_key": ""},
            {"id": "bot-2", "name": "Bot 2", "prompt": "", "avatar": AVATARS[2], "type": "ai", "llm_endpoint": "https://api-inference.huggingface.co", "llm_model": "meta-llama/Llama-3.1-8B-Instruct", "hf_api_key": ""}
        ],
        "rounds": 2,
        "initial_prompt": "",
        "turns": [],
        "current_round": 0,
        "current_player": 0,
        "is_loading": False,
        "image_generation": False
    }

    llm_services = {p["id"]: LocalLLMService(p["llm_endpoint"], p["llm_model"], p["hf_api_key"]) for p in state["personalities"]}

    def validate_settings(personalities: List[dict]) -> str:
        try:
            for p in personalities:
                if p["type"] == "ai":
                    if p["llm_endpoint"].startswith("https://api-inference.huggingface.co"):
                        if not p["hf_api_key"]:
                            return f"Hugging Face API key required for {p['name']}."
                        headers = {"Authorization": f"Bearer {p['hf_api_key']}"}
                        response = requests.get(f"{p['llm_endpoint']}/models/{p['llm_model']}", headers=headers)
                        if response.status_code != 200:
                            return f"Invalid Hugging Face model or API key for {p['name']}."
                    else:
                        return f"Local endpoints not supported on Android for {p['name']}. Use Hugging Face."
            return ""
        except Exception as e:
            return f"Error validating settings: {e}"

    def save_settings(image_generation: bool):
        error = validate_settings(state["personalities"])
        if error:
            return error
        state["image_generation"] = image_generation
        return "Settings saved!"

    def start_game(num_players: int, rounds: int, initial_prompt: str, *args):
        personalities = []
        for i in range(num_players):
            persona = args[i * 5]
            name = args[i * 5 + 1]
            prompt = args[i * 5 + 2]
            llm_endpoint = args[i * 5 + 3]
            llm_model = args[i * 5 + 4]
            hf_api_key = args[i * 5 + 5] if i * 5 + 5 < len(args) else ""
            if not name.strip() or (persona != "You (Human Player)" and not prompt.strip()):
                return "Please fill out all player names and personality prompts."
            personalities.append({
                "id": f"bot-{i}",
                "name": name,
                "prompt": prompt,
                "avatar": AVATARS[i % len(AVATARS)],
                "type": "user" if persona == "You (Human Player)" else "ai",
                "llm_endpoint": llm_endpoint,
                "llm_model": llm_model,
                "hf_api_key": hf_api_key
            })
        if rounds < 1:
            return "Please set at least 1 round."
        error = validate_settings(personalities)
        if error:
            return error
        state["status"] = GameStatus.PLAYING
        state["personalities"] = personalities
        state["rounds"] = rounds
        state["initial_prompt"] = initial_prompt
        state["turns"] = []
        state["current_round"] = 0
        state["current_player"] = 0
        llm_services.clear()
        llm_services.update({p["id"]: LocalLLMService(p["llm_endpoint"], p["llm_model"], p["hf_api_key"]) for p in personalities})
        if initial_prompt:
            state["turns"].append({
                "id": str(uuid.uuid4()),
                "personality": NARRATOR_PERSONALITY,
                "text": initial_prompt,
                "type": "bot",
                "image": None
            })
        return render_game()

    def add_turn(user_input: str = ""):
        state["is_loading"] = True
        current_player = state["personalities"][state["current_player"]]
        story_so_far = ". ".join(turn["text"] for turn in state["turns"]) + ("." if state["turns"] else "")
        llm_service = llm_services[current_player["id"]]
        
        image_path = None
        if current_player["type"] == "user":
            if not user_input.strip():
                state["is_loading"] = False
                return "Please enter your story contribution.", None
            state["turns"].append({
                "id": str(uuid.uuid4()),
                "personality": current_player,
                "text": user_input,
                "type": "bot",
                "image": None
            })
        else:
            try:
                text = llm_service.generateNextTurn(story_so_far, current_player)
                state["turns"].append({
                    "id": str(uuid.uuid4()),
                    "personality": current_player,
                    "text": text,
                    "type": "bot",
                    "image": None
                })
                if state["image_generation"]:
                    image_prompt = f"A vivid scene depicting: {text}"
                    image_path = llm_service.generateImage(image_prompt)
                    state["turns"][-1]["image"] = image_path
            except Exception as e:
                state["is_loading"] = False
                return f"Error generating turn: {e}", None
        
        state["current_player"] = (state["current_player"] + 1) % len(state["personalities"])
        if state["current_player"] == 0:
            state["current_round"] += 1
            if state["current_round"] >= state["rounds"]:
                try:
                    summary = llm_service.summarizeStory(
                        ". ".join(turn["text"] for turn in state["turns"]) + ".",
                        [p["prompt"] for p in state["personalities"] if p["type"] == "ai"]
                    )
                    image_path = None
                    if state["image_generation"]:
                        image_prompt = f"A dramatic scene summarizing: {summary}"
                        image_path = llm_service.generateImage(image_prompt)
                    state["turns"].append({
                        "id": str(uuid.uuid4()),
                        "personality": EDITOR_PERSONALITY,
                        "text": summary,
                        "type": "summary",
                        "image": image_path
                    })
                    state["status"] = GameStatus.FINISHED
                except Exception as e:
                    state["is_loading"] = False
                    return f"Error summarizing story: {e}", None
        state["is_loading"] = False
        return render_game(), image_path

    def edit_cast():
        state["status"] = GameStatus.EDITING_CAST
        return render_game()

    def start_new_game():
        state["status"] = GameStatus.SETUP
        state["turns"] = []
        return render_game()

    def render_game():
        if state["status"] == GameStatus.SETUP:
            with gr.Column():
                gr.Markdown("## Settings")
                image_generation = gr.Checkbox(label="Enable Image Generation (Hugging Face only)", value=state["image_generation"])
                save_btn = gr.Button("Save Settings")
                save_btn.click(save_settings, inputs=[image_generation], outputs=gr.Textbox())

                gr.Markdown("## AImprov: Yes, And...")
                num_players = gr.Dropdown(label="Number of Players", choices=[2, 3, 4, 5], value=len(state["personalities"]))
                rounds = gr.Slider(label="Rounds per Player", minimum=1, maximum=10, step=1, value=state["rounds"])
                initial_prompt = gr.Textbox(label="Story Starter (Optional)", value=state["initial_prompt"], lines=3)
                
                inputs = []
                for i in range(5):  # Max 5 players
                    with gr.Group(visible=i < len(state["personalities"])):
                        persona = gr.Dropdown(
                            label=f"Persona {i+1}",
                            choices=["You (Human Player)"] + [fp["name"] for fp in FAMOUS_PERSONALITIES] + ["Custom"],
                            value=state["personalities"][i]["type"] if i < len(state["personalities"]) else "You (Human Player)"
                        )
                        name = gr.Textbox(label=f"Name {i+1}", value=state["personalities"][i]["name"] if i < len(state["personalities"]) else f"Bot {i+1}", interactive=persona != "You (Human Player)")
                        prompt = gr.Textbox(
                            label=f"Personality Prompt {i+1}",
                            value=state["personalities"][i]["prompt"] if i < len(state["personalities"]) else "",
                            lines=3,
                            interactive=persona != "You (Human Player)"
                        )
                        llm_endpoint = gr.Textbox(
                            label=f"LLM Endpoint {i+1}",
                            value=state["personalities"][i]["llm_endpoint"] if i < len(state["personalities"]) else "https://api-inference.huggingface.co",
                            interactive=persona != "You (Human Player)"
                        )
                        llm_model = gr.Textbox(
                            label=f"LLM Model {i+1}",
                            value=state["personalities"][i]["llm_model"] if i < len(state["personalities"]) else "meta-llama/Llama-3.1-8B-Instruct",
                            interactive=persona != "You (Human Player)"
                        )
                        hf_api_key = gr.Textbox(
                            label=f"Hugging Face API Key {i+1}",
                            value=state["personalities"][i]["hf_api_key"] if i < len(state["personalities"]) else "",
                            type="password",
                            interactive=persona != "You (Human Player)"
                        )
                        inputs.extend([persona, name, prompt, llm_endpoint, llm_model, hf_api_key])
                
                start_btn = gr.Button("Start the Show!")
                start_btn.click(start_game, inputs=[num_players, rounds, initial_prompt] + inputs, outputs=gr.Markdown())

        elif state["status"] in [GameStatus.PLAYING, GameStatus.FINISHED]:
            with gr.Column():
                gr.Markdown("## Story in Progress" if state["status"] == GameStatus.PLAYING else "## Story Complete!")
                story_output = ""
                for turn in state["turns"]:
                    if turn["type"] == "summary":
                        story_output += f"<div style='text-align: center; padding: 16px; background-color: rgba(100, 116, 139, 0.5); border-top: 1px solid #64748b; border-bottom: 1px solid #64748b;'>{turn['personality']['avatar']} {turn['personality']['name']} refined the story:<br><i>{turn['text']}</i></div><br>"
                        if turn["image"]:
                            story_output += f"<img src='file://{turn['image']}' style='max-width: 300px; display: block; margin: auto;'><br>"
                    else:
                        is_even = len([t for t in state["turns"] if t["type"] == "bot"]) % 2 == 0
                        align = "left" if is_even else "right"
                        bg_color = "rgba(79, 70, 229, 0.8)" if is_even else "rgba(45, 212, 191, 0.8)"
                        story_output += f"<div style='display: flex; align-items: flex-end; gap: 12px; justify-content: {align};'>{turn['personality']['avatar'] if is_even else ''}<div style='max-width: 672px; padding: 16px; border-radius: 12px; background-color: {bg_color};'><b style='font-size: 14px; color: rgba(255, 255, 255, 0.8);'>{turn['personality']['name']}</b><p style='color: white;'>{turn['text']}</p></div>{'' if is_even else turn['personality']['avatar']}</div><br>"
                        if turn["image"]:
                            story_output += f"<img src='file://{turn['image']}' style='max-width: 300px; display: block; margin: {align};'><br>"

                if state["is_loading"]:
                    story_output += f"<div style='display: flex; align-items: flex-end; gap: 12px; justify-content: left;'>{state['personalities'][state['current_player']]['avatar']}<div style='max-width: 672px; padding: 16px; border-radius: 12px; background-color: rgba(79, 70, 229, 0.8);'><b style='font-size: 14px; color: rgba(255, 255, 255, 0.8);'>{state['personalities'][state['current_player']]['name']} is thinking...</b><div style='display: flex; gap: 8px; justify-content: center;'>{''.join('<div style=\"width: 12px; height: 12px; background-color: #2dd4bf; border-radius: 9999px; animation: pulse 1.5s infinite;\"></div>' for _ in range(3))}</div></div></div>"

                gr.HTML(story_output)

                if state["status"] == GameStatus.PLAYING:
                    if state["personalities"][state["current_player"]]["type"] == "user":
                        user_input = gr.Textbox(label="Your Turn", lines=3)
                        submit_btn = gr.Button("Add to Story")
                        submit_btn.click(add_turn, inputs=user_input, outputs=[gr.Markdown(), gr.Image()])
                    else:
                        next_btn = gr.Button("Next Turn")
                        next_btn.click(add_turn, inputs=None, outputs=[gr.Markdown(), gr.Image()])

                if state["status"] == GameStatus.FINISHED:
                    edit_btn = gr.Button("Edit Cast")
                    new_game_btn = gr.Button("Start New Game")
                    edit_btn.click(edit_cast, outputs=gr.Markdown())
                    new_game_btn.click(start_new_game, outputs=gr.Markdown())

        elif state["status"] == GameStatus.EDITING_CAST:
            with gr.Column():
                gr.Markdown("## Edit Your Cast")
                num_players = gr.Dropdown(label="Number of Players", choices=[2, 3, 4, 5], value=len(state["personalities"]))
                rounds = gr.Slider(label="Add More Rounds", minimum=1, maximum=10, step=1, value=state["rounds"])
                inputs = []
                for i in range(5):
                    with gr.Group(visible=i < len(state["personalities"])):
                        persona = gr.Dropdown(
                            label=f"Persona {i+1}",
                            choices=["You (Human Player)"] + [fp["name"] for fp in FAMOUS_PERSONALITIES] + ["Custom"],
                            value=state["personalities"][i]["type"] if i < len(state["personalities"]) else "You (Human Player)"
                        )
                        name = gr.Textbox(label=f"Name {i+1}", value=state["personalities"][i]["name"] if i < len(state["personalities"]) else f"Bot {i+1}", interactive=persona != "You (Human Player)")
                        prompt = gr.Textbox(
                            label=f"Personality Prompt {i+1}",
                            value=state["personalities"][i]["prompt"] if i < len(state["personalities"]) else "",
                            lines=3,
                            interactive=persona != "You (Human Player)"
                        )
                        llm_endpoint = gr.Textbox(
                            label=f"LLM Endpoint {i+1}",
                            value=state["personalities"][i]["llm_endpoint"] if i < len(state["personalities"]) else "https://api-inference.huggingface.co",
                            interactive=persona != "You (Human Player)"
                        )
                        llm_model = gr.Textbox(
                            label=f"LLM Model {i+1}",
                            value=state["personalities"][i]["llm_model"] if i < len(state["personalities"]) else "meta-llama/Llama-3.1-8B-Instruct",
                            interactive=persona != "You (Human Player)"
                        )
                        hf_api_key = gr.Textbox(
                            label=f"Hugging Face API Key {i+1}",
                            value=state["personalities"][i]["hf_api_key"] if i < len(state["personalities"]) else "",
                            type="password",
                            interactive=persona != "You (Human Player)"
                        )
                        inputs.extend([persona, name, prompt, llm_endpoint, llm_model, hf_api_key])
                
                continue_btn = gr.Button("Continue Story!")
                continue_btn.click(start_game, inputs=[num_players, rounds, gr.Textbox(value="")] + inputs, outputs=gr.Markdown())

        return ""

    with gr.Blocks(css="""
        .gradio-container { max-width: 800px; margin: auto; }
        .gr-button { background-color: #2dd4bf; color: white; }
        .gr-textbox, .gr-dropdown, .gr-slider, .gr-checkbox { margin-bottom: 10px; }
        img { max-width: 300px; margin: 10px; }
    """) as demo:
        gr.Markdown("# AImprov: Yes, And...")
        render_game()

    return demo

if __name__ == "__main__":
    demo = main()
    demo.launch(server_name="0.0.0.0", server_port=7860)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    backend_port: int = 8000
    log_dir: str = "logs"

    ollama_base_url: str = "http://localhost:11434"
    llm_main_model: str = "qwen3:14b"
    llm_fast_model: str = "qwen3:4b"
    llm_nsfw_model: str = "huihui_ai/qwen3-abliterated:14b"
    llm_vl_model: str = "huihui_ai/qwen3-vl-abliterated:8b"
    llm_embed_model: str = "nomic-embed-text"
    llm_coder_model: str = "qwen2.5-coder:14b"

    comfyui_base_url: str = "http://localhost:8188"

    # TIPO: 2026-06-18 Phase 1 실측으로 500M-ft + GPU 확정
    tipo_model_size: str = "500m"
    tipo_model: str = "KBlueLeaf/TIPO-500M-ft"
    tipo_device: str = "cuda"  # CPU는 long 82s 사용불가 → GPU 필수

    cloud_llm_api_key: str = ""
    cloud_llm_model: str = "claude-sonnet-4-6"

    qdrant_url: str = "http://localhost:6333"

    # ComfyUI output directory — must match ComfyUI's own output path
    comfyui_output_dir: str = "E:/ComfyUI/output"
    # ComfyUI input directory — reference images written here for img2img
    comfyui_input_dir: str = "E:/ComfyUI/input"


settings = Settings()

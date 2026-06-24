"""Singleton dependency instances, wired at startup."""
from app.clients.cloud_llm_client import CloudLLMClient
from app.clients.comfyui_client import ComfyUIClient
from app.clients.ollama_client import OllamaClient
from app.clients.tipo_client import TipoClient
from app.pipeline.critic import Critic
from app.pipeline.intent_parser import IntentParser
from app.pipeline.orchestrator import Orchestrator
from app.pipeline.param_resolver import ParamResolver
from app.pipeline.prompt_compiler import PromptCompiler
from app.pipeline.workflow_router import WorkflowRouter
from app.services.chat_store import ChatStore
from app.services.memory import MemoryService
from app.services.progress_hub import ProgressHub
from app.services.runtime_config import RuntimeConfig
from app.services.tag_allowlist import TagAllowlist
from app.services.vram_manager import VramManager

ollama = OllamaClient()
comfyui = ComfyUIClient()
cloud = CloudLLMClient()
tipo = TipoClient()

allowlist = TagAllowlist()
memory = MemoryService()
chat_store = ChatStore()
runtime_config = RuntimeConfig()
progress_hub = ProgressHub()
vram_manager = VramManager(ollama=ollama, comfyui=comfyui)

intent_parser = IntentParser(ollama=ollama, cloud=cloud, memory=memory, store=chat_store, runtime=runtime_config)
workflow_router = WorkflowRouter()
prompt_compiler = PromptCompiler(ollama=ollama, tipo=tipo, allowlist=allowlist)
param_resolver = ParamResolver()
critic = Critic(ollama=ollama)

orchestrator = Orchestrator(
    intent_parser=intent_parser,
    workflow_router=workflow_router,
    prompt_compiler=prompt_compiler,
    param_resolver=param_resolver,
    critic=critic,
    vram_manager=vram_manager,
    comfyui=comfyui,
    store=chat_store,
    progress_hub=progress_hub,
)


def init_all() -> None:
    """Initialize DB, load presets, allowlist, runtime config. Called once at FastAPI startup."""
    from app.db import init_db
    init_db()
    runtime_config.init()
    allowlist.load()
    param_resolver.load_presets()
    prompt_compiler.load_presets()
    intent_parser.load_groups()

"""
Image vision + generation pipeline for DARIA.

This module is intentionally isolated from Flask routes so its behavior can be
debugged and modified point-by-point without scanning the full web app.
"""

from __future__ import annotations

import io
import random
import re
import json
import importlib
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    Image = None
    HAS_PIL = False


class ImagePipeline:
    def __init__(self, logger):
        self.logger = logger
        self._vision_blip2 = None
        self._vision_blip2_disabled = False
        self._vision_blip = None
        self._vision_alt = None
        self._vision_classifier = None
        self._vision_zeroshot = None
        self._img_pipeline = None
        self._img_pipeline_device = "cpu"
        self._img_lock = threading.RLock()
        self._cache_dir = Path.home() / ".daria" / "hf-cache"
        self._manifest_file = Path.home() / ".daria" / "model_cache_manifest.json"

    # ──────────────────────────────────────────────────────────────
    #  Vision
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_caption(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip(" .\n\t")

    def analyze_image_bytes(self, blob: bytes, vision_provider: str = "auto") -> Dict[str, Any]:
        if not HAS_PIL:
            return {"error": "Pillow not installed"}
        try:
            with Image.open(io.BytesIO(blob)) as img:
                img_rgb = img.convert("RGB")
                w, h = img_rgb.size
                result: Dict[str, Any] = {"width": w, "height": h, "mode": "RGB"}

                caption = ""
                provider_used = ""
                labels: List[str] = []
                scene_hint = ""

                # 1) BLIP-2 attempt (as requested), disabled after first hard failure.
                if vision_provider in ("auto", "blip2") and not self._vision_blip2_disabled:
                    try:
                        from transformers import pipeline  # type: ignore

                        if self._vision_blip2 is None:
                            self._vision_blip2 = pipeline(
                                "image-to-text",
                                model="Salesforce/blip2-opt-2.7b",
                                device=-1,
                            )
                        out = self._vision_blip2(img_rgb, max_new_tokens=72)
                        if out and isinstance(out, list):
                            caption = self._clean_caption(out[0].get("generated_text"))
                            provider_used = "blip2"
                    except Exception as e:
                        self._vision_blip2_disabled = True
                        self.logger.warning(f"Vision BLIP-2 unavailable: {e}")

                # 2) BLIP fallback
                if not caption and vision_provider in ("auto", "blip2", "blip"):
                    try:
                        from transformers import pipeline  # type: ignore

                        if self._vision_blip is None:
                            try:
                                self._vision_blip = pipeline(
                                    "image-to-text",
                                    model="Salesforce/blip-image-captioning-large",
                                    device=-1,
                                )
                            except Exception:
                                self._vision_blip = pipeline(
                                    "image-to-text",
                                    model="Salesforce/blip-image-captioning-base",
                                    device=-1,
                                )
                        out = self._vision_blip(img_rgb, max_new_tokens=72)
                        if out and isinstance(out, list):
                            caption = self._clean_caption(out[0].get("generated_text"))
                            if caption:
                                provider_used = "blip"
                    except Exception as e:
                        self.logger.warning(f"Vision BLIP fallback failed: {e}")

                # 3) Alt caption fallback
                if not caption and vision_provider in ("auto", "blip2", "blip", "caption"):
                    try:
                        from transformers import pipeline  # type: ignore

                        if self._vision_alt is None:
                            self._vision_alt = pipeline(
                                "image-to-text",
                                model="nlpconnect/vit-gpt2-image-captioning",
                                device=-1,
                            )
                        out = self._vision_alt(img_rgb, max_new_tokens=72)
                        if out and isinstance(out, list):
                            caption = self._clean_caption(out[0].get("generated_text"))
                            if caption:
                                provider_used = "vit-gpt2"
                    except Exception as e:
                        self.logger.warning(f"Vision alt caption failed: {e}")

                # 4) Classifier fallback (confidence threshold)
                if vision_provider in ("auto", "blip2", "blip", "classifier"):
                    try:
                        from transformers import pipeline  # type: ignore

                        if self._vision_classifier is None:
                            self._vision_classifier = pipeline(
                                "image-classification",
                                model="google/vit-base-patch16-224",
                                device=-1,
                            )
                        cls = self._vision_classifier(img_rgb)
                        if cls and isinstance(cls, list):
                            confident = [
                                x for x in cls[:4]
                                if float(x.get("score") or 0.0) >= 0.30 and str(x.get("label") or "").strip()
                            ]
                            labels = [str(x.get("label") or "").strip() for x in confident]
                    except Exception as e:
                        self.logger.warning(f"Vision classifier failed: {e}")

                # 5) Scene sanity check (helps avoid surreal mismatches).
                if vision_provider in ("auto", "blip2", "blip", "classifier"):
                    try:
                        from transformers import pipeline  # type: ignore

                        if self._vision_zeroshot is None:
                            self._vision_zeroshot = pipeline(
                                "zero-shot-image-classification",
                                model="openai/clip-vit-base-patch32",
                                device=-1,
                            )
                        candidates = [
                            "anime girl portrait",
                            "cartoon girl portrait",
                            "superhero comic character",
                            "city skyline",
                            "animal portrait",
                            "nature landscape",
                            "text screenshot",
                        ]
                        zs = self._vision_zeroshot(img_rgb, candidate_labels=candidates)
                        if zs and isinstance(zs, list):
                            best = zs[0]
                            score = float(best.get("score") or 0.0)
                            label = str(best.get("label") or "").strip()
                            if score >= 0.40 and label:
                                scene_hint = label
                    except Exception as e:
                        self.logger.warning(f"Vision zero-shot failed: {e}")

                if scene_hint:
                    result["scene_hint"] = scene_hint
                    # If caption strongly conflicts with detected scene, steer it.
                    low = caption.lower()
                    if caption and "superhero" in low and "anime" in scene_hint:
                        caption = f"anime style portrait: {caption}"
                        result["caption"] = caption

                if caption:
                    result["caption"] = caption
                if labels:
                    result["labels"] = labels
                result["vision_provider"] = provider_used or ("vit-classifier" if labels else "basic")
                if not caption and not labels:
                    result["error"] = "low_confidence"
                return result
        except Exception as e:
            return {"error": f"image_decode_failed:{e}"}

    @staticmethod
    def compose_vision_context(description: str, image_hint: Dict[str, Any]) -> str:
        description = (description or "").strip()
        if image_hint and not image_hint.get("error"):
            lines: List[str] = []
            cap = str(image_hint.get("caption") or "").strip()
            if cap:
                lines.append(f"Я вижу на картинке: {cap}")
            labels = image_hint.get("labels") or []
            if isinstance(labels, list) and labels:
                lines.append("Похожие объекты: " + ", ".join(str(x) for x in labels[:4]))
            scene = str(image_hint.get("scene_hint") or "").strip()
            if scene:
                lines.append(f"Общий тип сцены: {scene}")
            if description:
                lines.append(f"Вопрос пользователя: {description}")
            if not lines:
                w = image_hint.get("width")
                h = image_hint.get("height")
                if w and h:
                    lines.append(f"Пользователь прислал изображение ({w}x{h}).")
                else:
                    lines.append("Пользователь прислал изображение.")
            return "\n".join(lines).strip()
        if image_hint.get("error"):
            return f"{description}\nЯ вижу изображение, но сейчас деталей слишком мало.".strip()
        return description

    @staticmethod
    def ask_dasha_about_image(user_text: str, vision_context: str, llm) -> str:
        question = (user_text or "").strip() or "Что на изображении?"
        fallback = "Я посмотрела картинку, но пока не уверена в деталях. Можешь уточнить, на чём сфокусироваться?"
        if not llm:
            return fallback
        try:
            r = llm.generate([
                {
                    "role": "system",
                    "content": (
                        "Ты Даша. Отвечай тепло, естественно и по-русски, от первого лица. "
                        "Никогда не упоминай технические термины: модели, модули, анализаторы, нейросети. "
                        "Пиши только по фактам из входного описания, без выдуманных деталей."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Факты о картинке:\n{vision_context}\n\n"
                        f"Вопрос: {question}\n\n"
                        "Дай живое описание 2-4 абзаца. "
                        "Если фактов мало, честно скажи об этом."
                    ),
                },
            ])
            ans = (r.content or "").strip()
            return ans or fallback
        except Exception:
            return fallback

    # ──────────────────────────────────────────────────────────────
    #  Generation
    # ──────────────────────────────────────────────────────────────

    def required_models(self, settings: Dict[str, Any]) -> List[str]:
        out: List[str] = []
        model_universal = str(settings.get("image_gen_model", "Tongyi-MAI/Z-Image-Turbo")).strip()
        if model_universal:
            out.append(model_universal)
        style_models = settings.get("image_gen_style_models", {}) or {}
        if isinstance(style_models, dict):
            out.extend([str(v).strip() for v in style_models.values() if str(v).strip()])

        vp = str(settings.get("senses_vision_provider", "auto")).lower().strip()
        if vp in ("auto", "blip2"):
            out.append("Salesforce/blip2-opt-2.7b")
        if vp in ("auto", "blip2", "blip"):
            out.append("Salesforce/blip-image-captioning-large")
        if vp in ("auto", "blip2", "blip", "caption"):
            out.append("nlpconnect/vit-gpt2-image-captioning")
        if vp in ("auto", "blip2", "blip", "classifier"):
            out.append("google/vit-base-patch16-224")
            out.append("openai/clip-vit-base-patch32")

        # uniq keeping order
        seen = set()
        uniq: List[str] = []
        for m in out:
            if m and m not in seen:
                seen.add(m)
                uniq.append(m)
        return uniq

    def _load_manifest(self) -> Dict[str, Any]:
        if self._manifest_file.exists():
            try:
                return json.loads(self._manifest_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"models": {}, "updated_at": ""}

    def _save_manifest(self, data: Dict[str, Any]):
        self._manifest_file.parent.mkdir(parents=True, exist_ok=True)
        self._manifest_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ensure_model_cached(self, model_id: str, force: bool = False) -> Tuple[bool, str]:
        try:
            from huggingface_hub import snapshot_download  # type: ignore
        except Exception as e:
            return False, f"huggingface_hub_missing:{e}"

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            if not force:
                snapshot_download(
                    repo_id=model_id,
                    cache_dir=str(self._cache_dir),
                    local_files_only=True,
                )
                return False, "already_cached"
        except Exception:
            pass

        snapshot_download(
            repo_id=model_id,
            cache_dir=str(self._cache_dir),
            local_files_only=False,
            resume_download=True,
        )
        return True, "downloaded"

    def ensure_models_cached(self, settings: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
        manifest = self._load_manifest()
        models = self.required_models(settings)
        changed: List[str] = []
        skipped: List[str] = []
        failed: List[str] = []

        for model_id in models:
            try:
                downloaded, status = self._ensure_model_cached(model_id, force=force)
                if downloaded:
                    changed.append(model_id)
                else:
                    skipped.append(model_id)
                manifest.setdefault("models", {})[model_id] = {
                    "status": status,
                    "cached_at": __import__("datetime").datetime.now().isoformat(),
                }
                self.logger.info(f"MODEL_CACHE {model_id} -> {status}")
            except Exception as e:
                failed.append(model_id)
                self.logger.warning(f"MODEL_CACHE {model_id} failed: {e}")

        manifest["updated_at"] = __import__("datetime").datetime.now().isoformat()
        self._save_manifest(manifest)
        return {"required": models, "downloaded": changed, "cached": skipped, "failed": failed}

    def warmup_generation_pipeline(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        provider = str(settings.get("image_gen_provider", "diffusers")).lower()
        if provider != "diffusers":
            return {"status": "skipped", "reason": f"unsupported_provider:{provider}"}
        model_universal = str(settings.get("image_gen_model", "Tongyi-MAI/Z-Image-Turbo")).strip()
        if not model_universal:
            return {"status": "skipped", "reason": "empty_model"}

        allow_cpu_fallback = bool(settings.get("image_gen_cpu_fallback", False))
        use_cuda = self.can_use_cuda_for_image_gen()
        if use_cuda:
            free_b, _ = self._gpu_mem_info()
            if free_b > 0 and free_b < 900 * 1024 * 1024:
                use_cuda = False

        with self._img_lock:
            if self._img_pipeline is not None and getattr(self._img_pipeline, "_daria_model_id", None) == model_universal:
                return {"status": "ready", "model": model_universal, "device": self._img_pipeline_device, "cached": True}

            try:
                # Warmup should never trigger internet traffic on startup.
                self._img_pipeline = self._build_generation_pipeline(
                    model_universal,
                    use_cuda=use_cuda,
                    allow_remote=False,
                )
            except Exception as e:
                if ("out of memory" in str(e).lower() or "cuda out of memory" in str(e).lower()) and allow_cpu_fallback:
                    self._cleanup_torch()
                    self._img_pipeline = self._build_generation_pipeline(
                        model_universal,
                        use_cuda=False,
                        allow_remote=False,
                    )
                else:
                    raise
            return {"status": "ready", "model": model_universal, "device": self._img_pipeline_device, "cached": False}

    @staticmethod
    def _cleanup_torch():
        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                try:
                    torch.cuda.ipc_collect()
                except Exception:
                    pass
        except Exception:
            pass

    @staticmethod
    def _gpu_mem_info() -> Tuple[int, int]:
        try:
            import torch  # type: ignore
            if not torch.cuda.is_available():
                return 0, 0
            free, total = torch.cuda.mem_get_info()
            return int(free), int(total)
        except Exception:
            return 0, 0

    @staticmethod
    def _is_retryable_pipeline_error(error_text: str) -> bool:
        e = (error_text or "").lower()
        markers = (
            "http error 5",
            "http_5",
            "503",
            "504",
            "530",
            "timed out",
            "timeout",
            "temporarily",
            "connection aborted",
            "connection reset",
            "remote disconnected",
            "empty response",
            "max retries exceeded",
            "name resolution",
        )
        return any(m in e for m in markers)

    @staticmethod
    def _is_index_oob_error(error_text: str) -> bool:
        e = (error_text or "").lower()
        return "index" in e and "out of bounds" in e

    @staticmethod
    def _is_cache_miss_error(error_text: str) -> bool:
        e = (error_text or "").lower()
        markers = (
            "local files only",
            "is not cached",
            "cannot find the requested files",
            "no such file",
            "offline mode",
            "couldn't connect",
        )
        return any(m in e for m in markers)

    def _release_pipeline_to_cpu(self):
        if self._img_pipeline is None:
            return
        try:
            self._img_pipeline = self._img_pipeline.to("cpu")
            self._img_pipeline_device = "cpu"
        except Exception:
            pass
        self._cleanup_torch()

    def _build_generation_pipeline(self, model_id: str, use_cuda: bool, allow_remote: bool = True):
        import torch  # type: ignore

        dtype = torch.float16 if use_cuda else torch.float32
        model_l = model_id.lower()
        load_kwargs: Dict[str, Any] = {
            "torch_dtype": dtype,
            # Avoid meta-init path that can raise _is_hf_initialized on some stacks.
            "low_cpu_mem_usage": False,
        }
        multi_gpu = False

        # IMPORTANT: avoid importing AutoPipelineForText2Image eagerly because
        # on some environments it triggers optional pipeline imports that fail
        # (e.g. hunyuandit/transformers mismatch).
        pipe = None
        if "z-image" in model_l:
            candidates = [
                "ZImagePipeline",
            ]
        elif "flux" in model_l:
            candidates = [
                "FluxPipeline",
                "DiffusionPipeline",
            ]
        else:
            candidates = [
                "DiffusionPipeline",
            ]

        for cls_name in candidates:
            try:
                diffusers = importlib.import_module("diffusers")  # type: ignore
                cls = getattr(diffusers, cls_name, None)
                if cls is None:
                    raise ImportError(f"{cls_name} unavailable in installed diffusers")

                last_load_err: Optional[Exception] = None
                local_only_order: Tuple[bool, ...] = (True, False) if allow_remote else (True,)
                for local_only in local_only_order:
                    phase_err: Optional[Exception] = None
                    tries = 1 if local_only else 2
                    for load_attempt in range(1, tries + 1):
                        kwargs = dict(load_kwargs)
                        kwargs["local_files_only"] = local_only
                        try:
                            try:
                                pipe = cls.from_pretrained(model_id, **kwargs)
                            except Exception as e:
                                # Some runtime stacks fail with hf-init kwargs, retry minimal load.
                                msg = str(e)
                                if "_is_hf_initialized" in msg or "unexpected keyword argument '_is_hf_initialized'" in msg:
                                    pipe = cls.from_pretrained(
                                        model_id,
                                        low_cpu_mem_usage=False,
                                        local_files_only=local_only,
                                    )
                                else:
                                    raise
                            phase_err = None
                            break
                        except Exception as e:
                            phase_err = e
                            if local_only and self._is_cache_miss_error(str(e)):
                                # Not in local cache yet; switch to remote load.
                                break
                            if (not local_only) and load_attempt < tries and self._is_retryable_pipeline_error(str(e)):
                                self.logger.warning(
                                    f"Image pipeline loader {cls_name} transient error, retrying: {e}"
                                )
                                time.sleep(2.5 * load_attempt)
                                continue
                            raise
                    if pipe is not None:
                        last_load_err = None
                        break
                    if phase_err is not None:
                        last_load_err = phase_err
                if last_load_err is not None:
                    raise last_load_err
                break
            except Exception as e:
                self.logger.warning(f"Image pipeline loader {cls_name} failed: {e}")
                pipe = None

        # Last chance: lazy Auto pipeline import (can fail on some diffusers builds).
        if pipe is None and allow_remote:
            try:
                auto_mod = importlib.import_module("diffusers.pipelines.auto_pipeline")
                auto_cls = getattr(auto_mod, "AutoPipelineForText2Image", None)
                if auto_cls is not None:
                    try:
                        pipe = auto_cls.from_pretrained(model_id, **load_kwargs)
                    except Exception:
                        pipe = auto_cls.from_pretrained(model_id, low_cpu_mem_usage=False)
            except Exception as e:
                self.logger.warning(f"Image pipeline loader AutoPipelineForText2Image failed: {e}")

        if pipe is None:
            raise RuntimeError(f"No compatible image pipeline class for model: {model_id}")

        pipe._daria_model_id = model_id
        pipe._daria_use_cuda = bool(use_cuda)
        pipe._daria_multi_gpu = bool(multi_gpu)

        if use_cuda and not multi_gpu:
            # Single GPU: reduce VRAM spikes.
            try:
                pipe.enable_attention_slicing("max")
            except Exception:
                pass
            try:
                pipe.enable_vae_tiling()
            except Exception:
                pass
            pipe = pipe.to("cuda")
            self._img_pipeline_device = "cuda"
        elif use_cuda and multi_gpu:
            self._img_pipeline_device = "multi-gpu"
        else:
            pipe = pipe.to("cpu")
            self._img_pipeline_device = "cpu"
        return pipe

    @staticmethod
    def prepare_prompt_for_generation(user_prompt: str, style: str, llm) -> Dict[str, str]:
        src = (user_prompt or "").strip() or "cute white kitten lying on warm sunlit wooden floor"
        fallback = (
            "masterpiece, best quality, ultra detailed, "
            f"{src}, soft cinematic light, natural colors, high detail, sharp focus"
        )
        prompt_model = fallback
        if llm:
            try:
                rr = llm.generate([
                    {
                        "role": "system",
                        "content": (
                            "You are a prompt engineer for image generation model. "
                            "Return one concise English prompt line only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"User request: {src}\nStyle: {style}\n"
                            "Create quality prompt preserving subject exactly."
                        ),
                    },
                ])
                generated = re.sub(r"\s+", " ", str(rr.content or "")).strip(" \"'")
                if generated:
                    prompt_model = generated
            except Exception:
                pass
        if len(prompt_model) > 950:
            prompt_model = prompt_model[:950]
        return {"prompt_model": prompt_model, "prompt_human": src}

    @staticmethod
    def can_use_cuda_for_image_gen() -> bool:
        try:
            import torch  # type: ignore

            if not torch.cuda.is_available():
                return False
            try:
                major, minor = torch.cuda.get_device_capability(0)
                tag = f"sm_{major}{minor}"
                archs = [str(x).lower() for x in (torch.cuda.get_arch_list() or [])]
                if archs and tag.lower() not in archs:
                    return False
            except Exception:
                pass
            _ = torch.tensor([0.0], device="cuda")
            return True
        except Exception:
            return False

    @staticmethod
    def dasha_draw_error_text(user_prompt: str, _error_text: str) -> str:
        return random.choice([
            f"Я попробовала нарисовать «{user_prompt}», но сейчас не вышло. Давай повторим, я постараюсь лучше 🌸",
            f"С «{user_prompt}» у меня пока не сложилось. Можем попробовать ещё раз? ✨",
            f"Ой, с «{user_prompt}» что-то пошло не так по пути. Дашь мне ещё попытку? 🤍",
        ])

    def generate_abstract_wallpaper(self, prompt: str, out_path: Path, width: int = 1280, height: int = 720) -> Dict[str, Any]:
        if not HAS_PIL:
            raise RuntimeError("Pillow not installed")
        seed = abs(hash(prompt or "daria")) % 1000000
        rnd = random.Random(seed)
        img = Image.new("RGB", (width, height), (18, 23, 37))
        px = img.load()
        c1 = (rnd.randint(20, 90), rnd.randint(40, 120), rnd.randint(90, 180))
        c2 = (rnd.randint(140, 240), rnd.randint(70, 180), rnd.randint(120, 240))
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            for x in range(width):
                px[x, y] = (r, g, b)
        try:
            from PIL import ImageDraw, ImageFilter

            draw = ImageDraw.Draw(img, "RGBA")
            for _ in range(22):
                x0 = rnd.randint(-200, width)
                y0 = rnd.randint(-150, height)
                w = rnd.randint(140, 420)
                h = rnd.randint(120, 360)
                color = (rnd.randint(180, 255), rnd.randint(120, 255), rnd.randint(160, 255), rnd.randint(35, 90))
                draw.ellipse((x0, y0, x0 + w, y0 + h), fill=color)
            img = img.filter(ImageFilter.GaussianBlur(radius=6))
        except Exception:
            pass
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, format="PNG", optimize=True)
        return {"provider": "abstract", "width": width, "height": height}

    def generate_image_network_fallback(self, prompt: str, out_path: Path) -> Dict[str, Any]:
        q = urllib.parse.quote((prompt or "cute cat").strip())
        last_err = ""
        for side in (512, 640, 768):
            for variant in ("", "&model=flux"):
                for _ in range(2):
                    seed = random.randint(1, 999999)
                    url = (
                        f"https://image.pollinations.ai/prompt/{q}"
                        f"?width={side}&height={side}&seed={seed}&nologo=true{variant}"
                    )
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "DARIA-Browser/0.9.1"})
                        with urllib.request.urlopen(req, timeout=20) as resp:
                            ctype = str(resp.headers.get("Content-Type") or "").lower()
                            data = resp.read(20 * 1024 * 1024 + 1)
                            if len(data) > 20 * 1024 * 1024:
                                raise RuntimeError("network image too large")
                            if "image/" not in ctype:
                                raise RuntimeError(f"network fallback returned non-image content-type: {ctype}")
                        if len(data) < 2048:
                            raise RuntimeError("network fallback returned too-small payload")
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        out_path.write_bytes(data)
                        return {"provider": "pollinations", "url": url, "size": side}
                    except Exception as e:
                        last_err = str(e)
                        continue
        raise RuntimeError(last_err or "network_fallback_failed")

    def generate_image_model(
        self,
        prompt: str,
        out_path: Path,
        settings: Dict[str, Any],
        llm,
        style: str = "universal",
    ) -> Dict[str, Any]:
        provider = str(settings.get("image_gen_provider", "diffusers")).lower()
        model_universal = str(settings.get("image_gen_model", "Tongyi-MAI/Z-Image-Turbo"))
        model_styles = settings.get("image_gen_style_models", {}) or {}
        model_id = str(model_styles.get(style) or model_universal)
        if provider != "diffusers":
            raise RuntimeError(f"Unsupported image_gen_provider: {provider}")

        prepared = self.prepare_prompt_for_generation(prompt, style=style, llm=llm)
        prompt_for_model = str(prepared.get("prompt_model") or prompt).strip()
        allow_cpu_fallback = bool(settings.get("image_gen_cpu_fallback", False))
        try:
            requested_side = int(settings.get("image_gen_max_side", 1024) or 1024)
        except Exception:
            requested_side = 1024
        requested_side = max(512, min(1024, requested_side))

        try:
            import torch  # type: ignore
            use_cuda = self.can_use_cuda_for_image_gen()
            model_l = model_id.lower()
            with self._img_lock:
                if not use_cuda and not allow_cpu_fallback:
                    raise RuntimeError("GPU недоступна, а CPU fallback отключен")
                if use_cuda:
                    free_b, _total_b = self._gpu_mem_info()
                    # Avoid immediate OOM loops on low free VRAM.
                    if free_b > 0 and free_b < 900 * 1024 * 1024:
                        use_cuda = False

                if self._img_pipeline is None or getattr(self._img_pipeline, "_daria_model_id", None) != model_id:
                    try:
                        self._img_pipeline = self._build_generation_pipeline(model_id, use_cuda=use_cuda)
                    except Exception as e:
                        if ("out of memory" in str(e).lower() or "cuda out of memory" in str(e).lower()) and allow_cpu_fallback:
                            self.logger.warning("OOM while loading image pipeline on GPU, retrying on CPU (fallback enabled)")
                            self._cleanup_torch()
                            self._img_pipeline = self._build_generation_pipeline(model_id, use_cuda=False)
                        else:
                            raise

            is_fast = ("turbo" in model_l) or ("flux.1-schnell" in model_l) or ("z-image" in model_l)
            free_b, total_b = self._gpu_mem_info()
            free_ratio = (free_b / max(1, total_b)) if total_b > 0 else 1.0
            if use_cuda:
                if free_ratio < 0.12:
                    side_candidates = [640, 576, 512]
                elif free_ratio < 0.20:
                    side_candidates = [768, 640, 576, 512]
                else:
                    side_candidates = [requested_side, 896, 768, 640, 576, 512]
            else:
                side_candidates = [min(640, requested_side), 576, 512]
            side_candidates = [int(s - (s % 64)) for s in side_candidates]
            side_candidates = [s for s in side_candidates if 512 <= s <= requested_side and s % 64 == 0]
            if not side_candidates:
                side_candidates = [512]
            side_candidates = list(dict.fromkeys(side_candidates))

            is_zimage = "z-image" in model_l
            if is_fast:
                if is_zimage:
                    # Z-Image is sensitive to short schedules.
                    step_candidates = [24, 20, 16, 12]
                else:
                    step_candidates = [10, 8, 6]
            else:
                step_candidates = [18, 14, 10, 8]
            if use_cuda and free_ratio < 0.20:
                if is_zimage:
                    step_candidates = [16, 12]
                else:
                    step_candidates = [8, 6]
            step_candidates = list(dict.fromkeys([max(2, int(x)) for x in step_candidates]))

            # Z-Image expects CFG-driven schedule; guidance=0 can destabilize it.
            if is_zimage:
                guidance = 5.0
            else:
                guidance = 0.0 if is_fast else 5.5
            result = None
            used_side = requested_side
            used_steps = step_candidates[0]
            last_err: Optional[Exception] = None
            for side in side_candidates:
                for steps in step_candidates:
                    kwargs: Dict[str, Any] = {
                        "prompt": prompt_for_model,
                        "num_inference_steps": steps,
                        "guidance_scale": guidance,
                        "width": side,
                        "height": side,
                    }
                    if "flux" in model_l:
                        kwargs["max_sequence_length"] = 256
                    try:
                        with self._img_lock:
                            try:
                                result = self._img_pipeline(**kwargs)
                            except TypeError:
                                kwargs.pop("max_sequence_length", None)
                                result = self._img_pipeline(**kwargs)
                        used_side = side
                        used_steps = steps
                        last_err = None
                        break
                    except Exception as e:
                        last_err = e
                        e_low = str(e).lower()
                        if "out of memory" in e_low or "cuda out of memory" in e_low:
                            self._cleanup_torch()
                            continue
                        if self._is_index_oob_error(e_low):
                            # Seen on some schedulers/pipelines with unstable step configs.
                            self._cleanup_torch()
                            continue
                        raise
                if result is not None:
                    break

            # Some pipelines are sensitive to scheduler/step interplay.
            # If we hit index OOB, retry once with a safer step count.
            if result is None and last_err is not None:
                le = str(last_err).lower()
                if self._is_index_oob_error(le):
                    safe_side = min(side_candidates) if side_candidates else 512
                    safe_steps = 32 if is_zimage else 16
                    # Rebuild once in case scheduler/pipeline internal state was corrupted.
                    with self._img_lock:
                        try:
                            self._img_pipeline = self._build_generation_pipeline(model_id, use_cuda=use_cuda)
                        except Exception:
                            pass
                    safe_kwargs: Dict[str, Any] = {
                        "prompt": prompt_for_model,
                        "num_inference_steps": safe_steps,
                        "guidance_scale": guidance,
                        "width": safe_side,
                        "height": safe_side,
                    }
                    if "flux" in model_l:
                        safe_kwargs["max_sequence_length"] = 256
                    try:
                        with self._img_lock:
                            try:
                                result = self._img_pipeline(**safe_kwargs)
                            except TypeError:
                                safe_kwargs.pop("max_sequence_length", None)
                                result = self._img_pipeline(**safe_kwargs)
                        used_side = safe_side
                        used_steps = safe_steps
                        last_err = None
                    except Exception as e:
                        last_err = e

            if result is None and allow_cpu_fallback and use_cuda:
                # Optional heavy fallback for hosts where GPU cannot complete.
                self.logger.warning("GPU generation failed; switching to CPU fallback once")
                with self._img_lock:
                    self._release_pipeline_to_cpu()
                    self._img_pipeline = self._build_generation_pipeline(model_id, use_cuda=False)
                kwargs = {
                    "prompt": prompt_for_model,
                    "num_inference_steps": 16 if is_zimage else (6 if is_fast else 8),
                    "guidance_scale": guidance,
                    "width": 512,
                    "height": 512,
                }
                if "flux" in model_l:
                    kwargs["max_sequence_length"] = 192
                with self._img_lock:
                    try:
                        result = self._img_pipeline(**kwargs)
                    except TypeError:
                        kwargs.pop("max_sequence_length", None)
                        result = self._img_pipeline(**kwargs)
                used_side = 512
                used_steps = int(kwargs["num_inference_steps"])

            if result is None:
                raise RuntimeError(str(last_err or "generation_failed"))

            image = result.images[0]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(out_path)
            # Opportunistic cleanup for tighter VRAM cards.
            free_b, total_b = self._gpu_mem_info()
            if total_b > 0 and free_b / max(1, total_b) < 0.12:
                self._release_pipeline_to_cpu()
            else:
                self._cleanup_torch()
            return {
                "provider": "diffusers",
                "model": model_id,
                "style": style,
                "prompt_user": str(prepared.get("prompt_human") or prompt),
                "prompt_model": prompt_for_model,
                "device": self._img_pipeline_device,
                "size": used_side,
                "steps": used_steps,
            }
        except Exception as e:
            raise RuntimeError(f"Image generation failed: {e}")

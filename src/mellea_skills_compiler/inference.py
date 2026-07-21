import os
from typing import Any, Dict, Optional

from mellea_skills_compiler.enums import InferenceEngineType, InferenceModel


OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")

INFERENCE_ENGINE_CACHE = {}


class InferenceService:

    def __init__(self, inference_engine_type: Optional[InferenceEngineType] = None):
        self.inference_engine_type = (
            inference_engine_type
            if inference_engine_type
            else InferenceEngineType.OLLAMA
        )

    @classmethod
    def risk_engine(
        cls,
        model_name_or_path: Optional[str] = None,
        inference_engine_type: Optional[InferenceEngineType] = None,
    ):
        return InferenceService(inference_engine_type).risk(
            model_name_or_path, parameters={"temperature": 0}
        )

    @classmethod
    def guardian_engine(
        cls,
        model_name_or_path: Optional[str] = None,
        inference_engine_type: Optional[InferenceEngineType] = None,
    ):
        return InferenceService(inference_engine_type).guardian(
            model_name_or_path,
            parameters={"temperature": 0, "num_ctx": 1024, "think": False},
        )

    @property
    def inference_engine_class(self):
        from ai_atlas_nexus.blocks.inference import OllamaInferenceEngine

        if self.inference_engine_type == InferenceEngineType.OLLAMA:
            return OllamaInferenceEngine
        else:
            raise ValueError(f"Invalid inference engine: {self.inference_engine_type}")

    @property
    def credentials(self) -> Dict[str, Any]:
        if self.inference_engine_type == InferenceEngineType.OLLAMA:
            return {"api_url": OLLAMA_API_URL}
        else:
            raise ValueError(f"Invalid inference engine: {self.inference_engine_type}")

    def risk(
        self,
        model_name_or_path: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        return self._cache_and_get_inference_engine(
            model_name_or_path
            or InferenceModel[f"{self.inference_engine_type.name}_RISK_MODEL"],
            parameters,
        )

    def guardian(
        self,
        model_name_or_path: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        return self._cache_and_get_inference_engine(
            model_name_or_path
            or InferenceModel[f"{self.inference_engine_type.name}_GUARDIAN_MODEL"],
            parameters,
        )

    def _cache_and_get_inference_engine(
        self,
        model_name_or_path: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        parameters = dict(sorted((parameters or {}).items()))
        cache_key = (
            self.inference_engine_type,
            model_name_or_path,
            tuple(parameters.items()),
        )
        if cache_key not in INFERENCE_ENGINE_CACHE:
            INFERENCE_ENGINE_CACHE[cache_key] = self.inference_engine_class(
                model_name_or_path=model_name_or_path,
                credentials=self.credentials,
                parameters=parameters or {},
            )
        return INFERENCE_ENGINE_CACHE[cache_key]

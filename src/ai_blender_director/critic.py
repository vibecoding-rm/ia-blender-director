import base64
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from PIL import Image, ImageStat

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - exercised in environments without optional numpy
    np = None

logger = logging.getLogger(__name__)


@dataclass
class CriticConfig:
    min_occupancy_ratio: float = 0.10
    framing_margin_ratio: float = 0.20
    min_avg_luminance: float = 40.0
    max_avg_luminance: float = 220.0   # overexposure threshold
    min_contrast_std: float = 25.0     # global std of luminance
    max_border_subject_ratio: float = 0.35  # subject pixels in outer 10% zone


@dataclass
class CriticFeedback:
    category: str
    level: str  # "WARNING" or "SUGGESTION"
    message: str


class VisionCritic:
    def __init__(self, beauty_path: Path, mask_path: Path, config: CriticConfig | None = None):
        self.beauty_path = beauty_path
        self.mask_path = mask_path
        self.config = config or CriticConfig()
        
        # Load images
        self.beauty_img = Image.open(beauty_path).convert("RGB")
        # Mask is expected to be an IndexOB pass where 1 is the subject. 
        # Typically saved as a grayscale PNG, so we convert it to "L".
        self.mask_img = Image.open(mask_path).convert("L")
        
        if self.beauty_img.size != self.mask_img.size:
            raise ValueError("Beauty and Mask images must have the same dimensions.")
            
        self.width, self.height = self.beauty_img.size
        self.total_pixels = self.width * self.height
        self.mask_array = np.asarray(self.mask_img, dtype=np.uint8) if np is not None else None
        self.subject_mask = self.mask_array > 0 if np is not None else None
        self.beauty_array = np.asarray(self.beauty_img, dtype=np.float32) if np is not None else None

    def analyze(self) -> List[CriticFeedback]:
        """Run LLM analysis if available, otherwise fallback to heuristic rules."""
        feedback = []

        # 1. Intentar usar Inteligencia Artificial Multimodal
        llm_feedback = self.analyze_with_llm()
        if llm_feedback is not None:
            logger.info(f"VisionCritic (LLM) generado {len(llm_feedback)} sugerencias.")
            feedback.extend(llm_feedback)
        else:
            logger.info("VisionCritic (LLM) no disponible o falló. Usando heurísticas matemáticas de respaldo.")
            # 2. Fallback a reglas matemáticas de la imagen
            for rule in (
                self.analyze_distance,
                self.analyze_framing,
                self.analyze_lighting,
                self.analyze_overexposure,
                self.analyze_contrast,
                self.analyze_edge_coverage,
            ):
                result = rule()
                if result:
                    feedback.append(result)

        return feedback

    def analyze_with_llm(self) -> List[CriticFeedback] | None:
        """Envía el beauty pass al LLM para crítica visual experta."""
        from .config import settings
        api_key = settings.openrouter_api_key
        if not api_key:
            return None

        try:
            from openai import OpenAI
            
            with open(self.beauty_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                
            client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
            
            system_prompt = (
                "Eres un Director de Fotografía experto. Analiza el siguiente render 3D (un preview de baja resolución). "
                "Ignora por completo el ruido (noise), los artefactos de bajo sampleo y la falta de anti-aliasing. "
                "Enfócate estrictamente en:\n"
                "1. Encuadre (Framing) y Posicionamiento\n"
                "2. Iluminación (Lighting) y Contraste\n"
                "3. Composición General\n\n"
                "Responde SOLO con un objeto JSON válido. El JSON debe contener exactamente una clave llamada 'feedback', "
                "cuyo valor sea una lista de objetos. Cada objeto debe tener:\n"
                "- 'category': 'Framing', 'Lighting', o 'Composition'\n"
                "- 'level': 'WARNING' (si es un error inaceptable que arruina el plano) o 'SUGGESTION' (si es una mejora menor)\n"
                "- 'message': descripción técnica corta del problema estético."
            )
            
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": "Evalúa estéticamente este render y devuelve tu JSON de feedback."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            raw_feedback = data.get("feedback", [])
            if not isinstance(raw_feedback, list):
                return None
                
            result = []
            for item in raw_feedback:
                if isinstance(item, dict) and "category" in item and "level" in item and "message" in item:
                    result.append(
                        CriticFeedback(
                            category=item["category"],
                            level=item["level"],
                            message=item["message"]
                        )
                    )
            return result
            
        except Exception as e:
            logger.error(f"Error en VisionCritic Multimodal: {e}")
            return None

    def analyze_distance(self) -> CriticFeedback | None:
        """Rule: if subject occupies less than 10% of the frame, the camera is too far."""
        if np is not None:
            subject_pixels = int(np.count_nonzero(self.subject_mask))
        else:
            pixels = self.mask_img.load()
            subject_pixels = sum(
                1
                for y in range(self.height)
                for x in range(self.width)
                if pixels[x, y] > 0
            )
                    
        occupancy = subject_pixels / self.total_pixels
        
        if subject_pixels == 0:
            return CriticFeedback(
                category="Distance",
                level="WARNING",
                message="No subject detected in the mask. Is the subject missing or occluded?"
            )
            
        if occupancy < self.config.min_occupancy_ratio:
            return CriticFeedback(
                category="Distance",
                level="SUGGESTION",
                message=f"Subject only occupies {occupancy:.1%} of the frame. Consider moving the camera closer."
            )
            
        return None

    def analyze_framing(self) -> CriticFeedback | None:
        """Rule: if the subject's center of mass is too close to the borders, framing is weak."""
        if np is not None:
            ys, xs = np.nonzero(self.subject_mask)
            count = int(xs.size)
            if count == 0:
                return None
            cx = float(xs.mean())
            cy = float(ys.mean())
        else:
            pixels = self.mask_img.load()
            sum_x = 0
            sum_y = 0
            count = 0
            for y in range(self.height):
                for x in range(self.width):
                    if pixels[x, y] > 0:
                        sum_x += x
                        sum_y += y
                        count += 1
            if count == 0:
                return None
            cx = sum_x / count
            cy = sum_y / count
                    
        margin_x = self.width * self.config.framing_margin_ratio
        margin_y = self.height * self.config.framing_margin_ratio
        
        issues = []
        if cx < margin_x:
            issues.append("too far left")
        elif cx > self.width - margin_x:
            issues.append("too far right")
            
        if cy < margin_y:
            issues.append("too high")
        elif cy > self.height - margin_y:
            issues.append("too low")
            
        if issues:
            return CriticFeedback(
                category="Framing",
                level="SUGGESTION",
                message=f"Subject center is {', '.join(issues)}. Consider adjusting the camera angle or target."
            )
            
        return None

    def analyze_lighting(self) -> CriticFeedback | None:
        """Rule: if the average luminance of the subject is too low, it's too dark."""
        avg_luminance = self._subject_average_luminance()
        if avg_luminance is None:
            return None

        if avg_luminance < self.config.min_avg_luminance:
            return CriticFeedback(
                category="Lighting",
                level="WARNING",
                message=f"Subject is too dark (avg luminance {avg_luminance:.1f}/255). Consider adding lights.",
            )

        return None

    def analyze_overexposure(self) -> CriticFeedback | None:
        """Rule: if the subject's average luminance is too high, it's blown out."""
        avg_luminance = self._subject_average_luminance()
        if avg_luminance is None:
            return None

        if avg_luminance > self.config.max_avg_luminance:
            return CriticFeedback(
                category="Lighting",
                level="WARNING",
                message=f"Subject is overexposed (avg luminance {avg_luminance:.1f}/255). Reduce light intensity.",
            )

        return None

    def analyze_contrast(self) -> CriticFeedback | None:
        """Rule: if the global image contrast (std of luminance) is too low, the scene looks flat."""
        gray = self.beauty_img.convert("L")
        stat = ImageStat.Stat(gray)
        std = stat.stddev[0]

        if std < self.config.min_contrast_std:
            return CriticFeedback(
                category="Contrast",
                level="SUGGESTION",
                message=f"Low global contrast (std {std:.1f}). Consider stronger key/fill light ratio or HDR.",
            )

        return None

    def analyze_edge_coverage(self) -> CriticFeedback | None:
        """Rule: if too many subject pixels are in the outer border zone, the subject is being cropped."""
        border = 0.10
        bx = int(self.width * border)
        by = int(self.height * border)

        if np is not None:
            total_subject = int(np.count_nonzero(self.subject_mask))
        else:
            mask_pixels = self.mask_img.load()
            total_subject = 0
            border_subject = 0
            for y in range(self.height):
                for x in range(self.width):
                    if mask_pixels[x, y] > 0:
                        total_subject += 1
                        if x < bx or x >= self.width - bx or y < by or y >= self.height - by:
                            border_subject += 1
            if total_subject == 0:
                return None
            ratio = border_subject / total_subject
            if ratio > self.config.max_border_subject_ratio:
                return CriticFeedback(
                    category="Framing",
                    level="WARNING",
                    message=f"{ratio:.0%} of subject pixels are near the frame edge. Subject may be cropped.",
                )
            return None

        if total_subject == 0:
            return None

        border_mask = np.zeros_like(self.subject_mask, dtype=bool)
        border_mask[:by, :] = True
        border_mask[self.height - by:, :] = True
        border_mask[:, :bx] = True
        border_mask[:, self.width - bx:] = True
        border_subject = int(np.count_nonzero(self.subject_mask & border_mask))

        ratio = border_subject / total_subject

        if ratio > self.config.max_border_subject_ratio:
            return CriticFeedback(
                category="Framing",
                level="WARNING",
                message=f"{ratio:.0%} of subject pixels are near the frame edge. Subject may be cropped.",
            )

        return None

    def _subject_average_luminance(self) -> float | None:
        if np is not None:
            if not np.any(self.subject_mask):
                return None
            luminance = (
                0.2126 * self.beauty_array[:, :, 0]
                + 0.7152 * self.beauty_array[:, :, 1]
                + 0.0722 * self.beauty_array[:, :, 2]
            )
            return float(luminance[self.subject_mask].mean())

        mask_pixels = self.mask_img.load()
        beauty_pixels = self.beauty_img.load()
        total_luminance = 0
        count = 0
        for y in range(self.height):
            for x in range(self.width):
                if mask_pixels[x, y] > 0:
                    r, g, b = beauty_pixels[x, y]
                    total_luminance += 0.2126 * r + 0.7152 * g + 0.0722 * b
                    count += 1
        if count == 0:
            return None
        return total_luminance / count

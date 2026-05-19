from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from PIL import Image

@dataclass
class CriticConfig:
    min_occupancy_ratio: float = 0.10
    framing_margin_ratio: float = 0.20
    min_avg_luminance: float = 40.0


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

    def analyze(self) -> List[CriticFeedback]:
        """Run all heuristic rules and return the feedback."""
        feedback = []
        
        distance_fb = self.analyze_distance()
        if distance_fb:
            feedback.append(distance_fb)
            
        framing_fb = self.analyze_framing()
        if framing_fb:
            feedback.append(framing_fb)
            
        lighting_fb = self.analyze_lighting()
        if lighting_fb:
            feedback.append(lighting_fb)
            
        return feedback

    def analyze_distance(self) -> CriticFeedback | None:
        """Rule: if subject occupies less than 10% of the frame, the camera is too far."""
        subject_pixels = 0
        pixels = self.mask_img.load()
        
        # IndexOB passes might save the index 1 as value 1 (nearly black) or as 255 (if normalized).
        # We assume any value > 0 in the mask is the subject.
        for y in range(self.height):
            for x in range(self.width):
                if pixels[x, y] > 0:
                    subject_pixels += 1
                    
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
            return None  # Handled by distance analyzer
            
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
        mask_pixels = self.mask_img.load()
        beauty_pixels = self.beauty_img.load()
        
        total_luminance = 0
        count = 0
        
        for y in range(self.height):
            for x in range(self.width):
                if mask_pixels[x, y] > 0:
                    r, g, b = beauty_pixels[x, y]
                    # Standard luminance formula
                    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
                    total_luminance += lum
                    count += 1
                    
        if count == 0:
            return None
            
        avg_luminance = total_luminance / count
        
        if avg_luminance < self.config.min_avg_luminance:
            return CriticFeedback(
                category="Lighting",
                level="WARNING",
                message=f"Subject is too dark (average luminance {avg_luminance:.1f}/255). Consider adding lights."
            )
            
        return None

import os
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """
    ImageProcessor handles document image enhancement prior to OCR.
    Crucially, it does not alter image dimensions (avoiding resizing/cropping)
    to ensure bounding box coordinates map 1:1 back to the original document.
    """
    
    def __init__(self, output_dir: str = "data/processed"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def preprocess(self, image_path: str, method: str = "adaptive") -> str:
        """
        Preprocesses the input image and saves it to the output directory.
        Supported methods:
          - 'grayscale'   : Simple grayscale conversion.
          - 'adaptive'    : Grayscale + adaptive thresholding (best for faded/shadowed scans).
          - 'denoise'     : Grayscale + bilateral filtering + Otsu thresholding (best for noisy scans).
          - 'handwriting' : CLAHE contrast enhancement + mild Gaussian blur (best for photographed
                            handwritten documents — avoids binarization which destroys ink strokes).

        Returns:
          str: Path to the processed image file.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image path does not exist: {image_path}")

        # Read image using OpenCV
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image from path: {image_path}")

        # Step 1: Grayscale conversion
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Step 2: Apply specified preprocessing method
        if method == "grayscale":
            processed = gray
            logger.info("Applied grayscale preprocessing.")

        elif method == "adaptive":
            # Adaptive thresholding to handle non-uniform illumination/shadows
            processed = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                15,
                8
            )
            logger.info("Applied adaptive thresholding preprocessing.")

        elif method == "denoise":
            # Bilateral filter preserves edges while smoothing out high-frequency noise
            denoised = cv2.bilateralFilter(gray, 9, 75, 75)
            # Otsu's thresholding for binarization
            _, processed = cv2.threshold(
                denoised,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            logger.info("Applied bilateral filtering + Otsu thresholding preprocessing.")

        elif method == "handwriting":
            # For photographed handwritten documents:
            # 1. CLAHE — boosts local contrast so light/faint strokes become visible,
            #    without over-exposing dense ink regions.
            # 2. Mild Gaussian blur (3x3) — smooths camera sensor noise without
            #    destroying letter stroke edges.
            # We deliberately do NOT binarize: binarization breaks thin cursive strokes
            # and causes PP-OCRv5 to miss characters.
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            processed = cv2.GaussianBlur(enhanced, (3, 3), 0)
            logger.info("Applied CLAHE + Gaussian blur preprocessing for handwriting.")

        else:
            logger.warning(f"Unknown preprocessing method '{method}'. Falling back to grayscale.")
            processed = gray

        # Save the preprocessed image
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_processed_{method}{ext}"
        output_path = os.path.join(self.output_dir, output_filename)

        cv2.imwrite(output_path, processed)
        logger.info(f"Saved preprocessed image to: {output_path}")

        return output_path

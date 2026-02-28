"""
Face Recognition Service
========================
Pipeline: RetinaFace detection → MTCNN alignment → Facenet512 embeddings
Matching: cosine similarity + optional Euclidean distance
Optimizations: per-user embedding cache (TTL=5min), batch processing support
"""

import os
import time
import logging
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from deepface import DeepFace
from models.database import db
from models.face import Face
from models.person import Person
from config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class FaceRecognitionService:
    """
    Unified face detection and recognition service.

    Detection  : RetinaFace  — robust under varied lighting/angles
    Alignment  : MTCNN       — landmark extraction + geometric normalisation
    Embeddings : Facenet512  — 512-dimensional face representation
    Matching   : cosine similarity (default) or Euclidean distance
    """

    # DeepFace model / detector identifiers
    MODEL_NAME        = "Facenet512"
    DETECTOR_BACKEND  = "retinaface"   # detection pass
    ALIGN_BACKEND     = "mtcnn"        # landmark / alignment pass
    MODEL_VERSION     = "Facenet512-RetinaFace-MTCNN-v1"

    # Matching thresholds
    COSINE_THRESHOLD    = 0.40   # cosine distance (lower = more similar)
    EUCLIDEAN_THRESHOLD = 20.0   # L2 distance

    # Embedding cache TTL (seconds)
    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        self.embeddings_folder = Config.EMBEDDINGS_FOLDER
        self.metric = "cosine"

        # Instance aliases (for backward-compat with test scripts and logging)
        self.model_name       = self.MODEL_NAME
        self.detector_backend = self.DETECTOR_BACKEND
        self.align_backend    = self.ALIGN_BACKEND
        self.distance_threshold = self.COSINE_THRESHOLD

        # in-process embedding cache: { user_id: [{"person": <Person>, "embedding": [...]}] }
        self._emb_cache: dict = {}
        self._cache_ts: dict = {}

        logger.info(
            f"FaceRecognitionService initialised | model={self.MODEL_NAME} "
            f"detector={self.DETECTOR_BACKEND} align={self.ALIGN_BACKEND}"
        )

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _get_user_embeddings(self, user_id: int) -> list:
        """Return user embeddings from cache or DB."""
        now = time.time()
        if user_id in self._emb_cache and (now - self._cache_ts.get(user_id, 0)) < self.CACHE_TTL:
            logger.debug(f"Cache hit for user {user_id}")
            return self._emb_cache[user_id]

        logger.debug(f"Cache miss for user {user_id} — querying DB")
        persons = Person.query.filter_by(user_id=user_id).all()
        data = []
        for person in persons:
            for face in person.faces:
                if face.embedding:
                    data.append({"person": person, "embedding": face.embedding})

        self._emb_cache[user_id]  = data
        self._cache_ts[user_id]   = now
        logger.info(f"Loaded {len(data)} embeddings for user {user_id} into cache")
        return data

    def invalidate_cache(self, user_id: int) -> None:
        """Force re-fetch on next access for a given user."""
        self._emb_cache.pop(user_id, None)
        self._cache_ts.pop(user_id, None)
        logger.debug(f"Cache invalidated for user {user_id}")

    # ------------------------------------------------------------------
    # Stage 1 — Face detection + MTCNN landmark extraction
    # ------------------------------------------------------------------

    def extract_faces_with_landmarks(self, image_path: str) -> list:
        """
        Use RetinaFace for detection and MTCNN for landmark extraction.

        Returns a list of dicts with keys:
            face       – cropped face numpy array
            facial_area – {x, y, w, h}
            confidence – detection score
            landmarks  – {right_eye, left_eye, nose, mouth_right, mouth_left}
        """
        t0 = time.time()
        results = []

        # ---- Pass 1: RetinaFace detection (bounding boxes + confidence) ----
        try:
            detected = DeepFace.extract_faces(
                img_path=image_path,
                detector_backend=self.DETECTOR_BACKEND,
                align=False,          # no alignment yet — raw crop
                enforce_detection=False,
            )
        except Exception as exc:
            logger.error(f"RetinaFace detection failed for {image_path}: {exc}")
            detected = []

        if not detected:
            logger.info(f"No faces detected by RetinaFace in {image_path}")
            return []

        logger.info(f"RetinaFace found {len(detected)} face(s) in {os.path.basename(image_path)}")

        # ---- Pass 2: MTCNN alignment + landmark extraction ----
        try:
            aligned = DeepFace.extract_faces(
                img_path=image_path,
                detector_backend=self.ALIGN_BACKEND,   # MTCNN
                align=True,
                enforce_detection=False,
            )
        except Exception as exc:
            logger.warning(
                f"MTCNN alignment failed for {image_path}: {exc}. "
                "Falling back to RetinaFace crops without alignment."
            )
            aligned = detected  # fallback — use raw RetinaFace crops

        # Merge: prefer aligned crops when MTCNN count matches, else use RetinaFace
        face_list = aligned if len(aligned) == len(detected) else detected

        for item in face_list:
            landmark_data = item.get("facial_area", {})
            results.append({
                "face":         item.get("face"),          # cropped ndarray
                "facial_area":  item.get("facial_area", {}),
                "confidence":   item.get("confidence", 0.0),
                "landmarks":    item.get("landmarks", {}), # MTCNN landmark points
            })

        elapsed = time.time() - t0
        logger.info(
            f"Detection+alignment completed in {elapsed:.2f}s "
            f"({len(results)} face(s)) for {os.path.basename(image_path)}"
        )
        return results

    # ------------------------------------------------------------------
    # Stage 2 — Embedding extraction (Facenet512)
    # ------------------------------------------------------------------

    def get_embedding(self, image_path: str, face_crop=None) -> list | None:
        """
        Extract a 512-dimensional Facenet512 embedding.

        Accepts either a file path or a pre-cropped numpy face array.
        Returns a list[float] of length 512, or None on failure.
        """
        t0 = time.time()
        img_input = face_crop if face_crop is not None else image_path
        try:
            objs = DeepFace.represent(
                img_path=img_input,
                model_name=self.MODEL_NAME,
                detector_backend=self.DETECTOR_BACKEND,
                align=True,
                enforce_detection=False,
            )
            if not objs:
                return None
            emb = objs[0].get("embedding")
            elapsed = time.time() - t0
            logger.debug(f"Embedding extracted in {elapsed:.3f}s  dim={len(emb) if emb else 'N/A'}")
            return emb
        except Exception as exc:
            logger.error(f"Embedding extraction failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Combined pipeline: detect + align + embed
    # ------------------------------------------------------------------

    def detect_and_extract_faces(self, image_path: str) -> list:
        """
        Full pipeline for a single image.

        Returns a list of dicts (one per detected face):
            embedding   – list[float] (512-d)
            facial_area – {x, y, w, h}
            confidence  – float
            landmarks   – dict
            face_confidence – alias for confidence
        """
        t0 = time.time()
        try:
            raw = DeepFace.represent(
                img_path=image_path,
                model_name=self.MODEL_NAME,
                detector_backend=self.DETECTOR_BACKEND,
                align=True,
                enforce_detection=False,
            )
            elapsed = time.time() - t0
            logger.info(
                f"detect_and_extract_faces: {len(raw)} face(s) found in "
                f"{os.path.basename(image_path)} ({elapsed:.2f}s)"
            )
            # Normalise structure — ensure face_confidence exists
            for item in raw:
                item.setdefault("face_confidence", item.get("confidence", 0.0))
            return raw
        except Exception as exc:
            logger.error(f"Pipeline failed for {image_path}: {exc}")
            return []

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    def process_batch(self, image_paths: list, max_workers: int = 4) -> list:
        """
        Process multiple images concurrently.

        Returns list of {"image": path, "faces": [...]}.
        """
        logger.info(f"Batch processing {len(image_paths)} image(s) with {max_workers} worker(s)")
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {pool.submit(self.detect_and_extract_faces, p): p for p in image_paths}
            for future in as_completed(future_map):
                path = future_map[future]
                try:
                    faces = future.result()
                except Exception as exc:
                    logger.error(f"Batch item {path} raised: {exc}")
                    faces = []
                results.append({"image": path, "faces": faces})

        logger.info(f"Batch complete — processed {len(results)} image(s)")
        return results

    # ------------------------------------------------------------------
    # Distance helpers
    # ------------------------------------------------------------------

    @staticmethod
    def cosine_similarity(a: list, b: list) -> float:
        """Cosine similarity in [−1, 1]. Higher = more similar."""
        va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
        na, nb = np.linalg.norm(va), np.linalg.norm(vb)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(va, vb) / (na * nb))

    @staticmethod
    def cosine_distance(a: list, b: list) -> float:
        """Cosine distance in [0, 2]. Lower = more similar."""
        return 1.0 - FaceRecognitionService.cosine_similarity(a, b)

    @staticmethod
    def euclidean_distance(a: list, b: list) -> float:
        """L2 distance. Lower = more similar."""
        return float(np.linalg.norm(np.array(a, dtype=np.float32) - np.array(b, dtype=np.float32)))

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def match_face(self, target_embedding: list, user_id: int) -> tuple:
        """
        Match target_embedding against all known faces for user_id.

        Returns (best_person | None, {"cosine_distance": float, "euclidean": float, "similarity": float})
        """
        t0 = time.time()
        user_faces = self._get_user_embeddings(user_id)

        best_person = None
        best_cos_dist = float("inf")
        best_euclid   = float("inf")
        best_sim      = -1.0

        for entry in user_faces:
            stored = entry["embedding"]
            cos_d  = self.cosine_distance(target_embedding, stored)
            euclid = self.euclidean_distance(target_embedding, stored)
            sim    = 1.0 - cos_d  # higher is better

            # Primary criterion: cosine distance below threshold
            if cos_d < self.COSINE_THRESHOLD and cos_d < best_cos_dist:
                best_cos_dist = cos_d
                best_euclid   = euclid
                best_sim      = sim
                best_person   = entry["person"]

        elapsed = time.time() - t0
        score = {"cosine_distance": best_cos_dist, "euclidean": best_euclid, "similarity": best_sim}

        if best_person:
            logger.info(
                f"Match found for user {user_id}: person='{best_person.name}' "
                f"cos_dist={best_cos_dist:.4f} sim={best_sim:.4f} [{elapsed:.3f}s]"
            )
        else:
            logger.info(
                f"No match for user {user_id} (threshold={self.COSINE_THRESHOLD}) [{elapsed:.3f}s]"
            )

        return best_person, score

    # ------------------------------------------------------------------
    # Auto-create unknown person
    # ------------------------------------------------------------------

    def auto_create_person(self, user_id: int, label: str = None) -> "Person":
        """
        Create a new Person record for an unrecognised face.

        The person is flagged as auto-created so the UI can prompt
        the user to optionally assign a real name later.
        """
        if label is None:
            count = Person.query.filter_by(user_id=user_id, is_auto_created=True).count()
            label = f"Unknown Person {count + 1}"

        person = Person(name=label, user_id=user_id, is_auto_created=True)
        db.session.add(person)
        db.session.flush()   # get person.id without full commit
        self.invalidate_cache(user_id)
        logger.info(f"Auto-created person '{label}' (id={person.id}) for user {user_id}")
        return person

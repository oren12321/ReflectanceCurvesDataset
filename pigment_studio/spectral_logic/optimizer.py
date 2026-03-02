import numpy as np
from scipy.optimize import minimize
from typing import Callable, Dict, Any, List
from core.data import WAVE_SAMPLES
from spectral_logic.color_engine import ColorEngine


class SpectralOptimizer:
    """
    Pure optimization engine.
    No Qt, no UI.
    """

    def __init__(self, color_engine: ColorEngine):
        self.color_engine = color_engine

    def build_objective(
        self,
        sorted_keys: List[float],
        target_lab,
        active_illuminant_key: str,
    ) -> Callable[[np.ndarray], float]:
        s_keys = np.array(sorted_keys)

        def objective(y_values: np.ndarray) -> float:
            temp_y_full = np.interp(WAVE_SAMPLES, s_keys, y_values)
            # Active illuminant
            Lab_active, _ = self.color_engine.spectral_to_lab_and_rgb(
                temp_y_full, active_illuminant_key
            )
            de_active = self.color_engine.delta_e(target_lab, Lab_active)

            # Metamerism penalty
            others = [k for k in ["D65", "A", "FL2"] if k != active_illuminant_key]
            de_metameric = 0.0
            for ill_key in others:
                Lab_other, _ = self.color_engine.spectral_to_lab_and_rgb(
                    temp_y_full, ill_key
                )
                de_metameric += self.color_engine.delta_e(target_lab, Lab_other)

            smooth = np.sum(np.square(np.diff(y_values, 2))) * 0.001
            return de_active + 0.1 * de_metameric + smooth

        return objective

    def optimize(
        self,
        points: Dict[float, float],
        target_lab,
        active_illuminant_key: str,
        stop_flag: Callable[[], bool],
        progress_callback: Callable[[str], None],
    ) -> Dict[str, Any]:
        """
        Run multi-start L-BFGS-B optimization.
        Returns dict with:
          - success: bool
          - message: str
          - best_points: Dict[float, float] (or None)
          - final_de: float (or None)
        """
        if target_lab is None:
            return {
                "success": False,
                "message": "No target color.",
                "best_points": None,
                "final_de": None,
            }

        sorted_keys = sorted(points.keys())
        initial_y = np.array([points[k] for k in sorted_keys])
        bounds = [(0.5, 99.5) for _ in initial_y]

        objective = self.build_objective(
            sorted_keys, target_lab, active_illuminant_key
        )

        progress_callback("Searching for optimal spectral match...")
        best_res = minimize(
            objective, initial_y, method="L-BFGS-B", bounds=bounds, tol=1e-4
        )

        if best_res.fun > 0.5:
            for i in range(3):
                if stop_flag():
                    progress_callback("Optimization aborted by user.")
                    break
                progress_callback(f"Retrying heuristic search ({i + 1}/3)...")
                jiggled_start = np.clip(
                    initial_y + np.random.uniform(-15, 15, len(initial_y)),
                    0.5,
                    99.5,
                )
                res = minimize(
                    objective,
                    jiggled_start,
                    method="L-BFGS-B",
                    bounds=bounds,
                    tol=1e-4,
                )
                if res.fun < best_res.fun:
                    best_res = res
                if best_res.fun < 0.1:
                    break

        if not stop_flag() and (best_res.success or best_res.fun < 1.0):
            best_points = {
                k: float(best_res.x[i]) for i, k in enumerate(sorted_keys)
            }
            return {
                "success": True,
                "message": "Optimization completed.",
                "best_points": best_points,
                "final_de": float(best_res.fun),
            }
        else:
            return {
                "success": False,
                "message": best_res.message,
                "best_points": None,
                "final_de": None,
            }

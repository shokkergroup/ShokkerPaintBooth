"""
GPU acceleration for Shokker Paint Booth V5.
Detects NVIDIA (CuPy/CUDA), AMD (OpenCL), or falls back to CPU (numpy).
Usage: from engine.gpu import xp, gpu_info, to_cpu, to_gpu
"""
import numpy as np
import os
import sys

# Detection results
GPU_BACKEND = 'cpu'  # 'cuda', 'rocm', 'opencl', 'cpu'
GPU_NAME = 'CPU (numpy)'
GPU_VRAM_MB = 0
_cupy = None

def _setup_nvidia_paths():
    """Add pip-installed NVIDIA CUDA library paths to system PATH.

    When CuPy + nvidia-cuda-nvrtc-cu12 etc. are installed via pip, the DLLs
    end up in site-packages/nvidia/*/bin/ which isn't on PATH by default.
    We scan for these directories and add them so CuPy can find nvrtc, cublas, etc.
    """
    try:
        # Find the nvidia packages directory in site-packages
        import importlib.util
        for search_dir in sys.path:
            nvidia_dir = os.path.join(search_dir, 'nvidia')
            if os.path.isdir(nvidia_dir):
                added = 0
                for pkg in os.listdir(nvidia_dir):
                    for subdir in ('bin', 'lib'):
                        lib_path = os.path.join(nvidia_dir, pkg, subdir)
                        if os.path.isdir(lib_path) and lib_path not in os.environ.get('PATH', ''):
                            os.environ['PATH'] = lib_path + os.pathsep + os.environ.get('PATH', '')
                            added += 1
                if added > 0:
                    # Also set CUDA_PATH if nvrtc is found
                    nvrtc_dir = os.path.join(nvidia_dir, 'cuda_nvrtc')
                    if os.path.isdir(nvrtc_dir):
                        os.environ.setdefault('CUDA_PATH', nvrtc_dir)
                    print(f"[GPU] Added {added} NVIDIA library paths from pip packages")
                    return
    except Exception as e:
        pass  # Non-fatal — CuPy may still work if CUDA is installed system-wide


def _detect():
    global GPU_BACKEND, GPU_NAME, GPU_VRAM_MB, _cupy

    # Allow forcing CPU mode via env var
    if os.environ.get('SHOKKER_NO_GPU', '').lower() in ('1', 'true', 'yes'):
        print("[GPU] GPU disabled by SHOKKER_NO_GPU env var")
        return

    # Pre-configure NVIDIA library paths (pip-installed CUDA packages put DLLs in site-packages/nvidia/*)
    _setup_nvidia_paths()

    # Try NVIDIA CUDA via CuPy
    try:
        import cupy
        device_count = cupy.cuda.runtime.getDeviceCount()
        if device_count > 0:
            props = cupy.cuda.runtime.getDeviceProperties(0)
            GPU_NAME = props['name'].decode() if isinstance(props['name'], bytes) else str(props['name'])
            GPU_VRAM_MB = props.get('totalGlobalMem', 0) // (1024 * 1024)
            GPU_BACKEND = 'cuda'
            _cupy = cupy
            print(f"[GPU] NVIDIA CUDA detected: {GPU_NAME} ({GPU_VRAM_MB}MB VRAM)")
            print(f"[GPU]   CuPy version: {cupy.__version__}, CUDA: {cupy.cuda.runtime.runtimeGetVersion()}")
            return
    except ImportError:
        pass
    except Exception as e:
        print(f"[GPU] CUDA detection failed: {e}")

    # Try AMD ROCm via CuPy-ROCm
    try:
        import cupy
        # ROCm builds of CuPy use hip runtime
        device_count = cupy.cuda.runtime.getDeviceCount()
        if device_count > 0:
            GPU_BACKEND = 'rocm'
            GPU_NAME = 'AMD GPU (ROCm)'
            _cupy = cupy
            print(f"[GPU] AMD ROCm detected -- using CuPy/ROCm")
            return
    except:
        pass

    # Try OpenCL (AMD, Intel, any GPU)
    try:
        import pyopencl as cl
        platforms = cl.get_platforms()
        for p in platforms:
            devices = p.get_devices(device_type=cl.device_type.GPU)
            if devices:
                GPU_NAME = f"{devices[0].name} (OpenCL)"
                GPU_VRAM_MB = devices[0].global_mem_size // (1024 * 1024)
                GPU_BACKEND = 'opencl'
                print(f"[GPU] OpenCL GPU detected: {GPU_NAME} ({GPU_VRAM_MB}MB)")
                return
    except ImportError:
        pass
    except Exception as e:
        print(f"[GPU] OpenCL detection failed: {e}")

    print("[GPU] No GPU acceleration available -- using CPU (numpy)")

# Run detection at import
_detect()

# GPU compute toggle. When True AND CuPy is available, compose.py uses GPU arrays.
# Can be toggled at runtime via enable_gpu_compute() / disable_gpu_compute().
_GPU_COMPUTE_ENABLED = False

# GPU compute disabled — CPU with noise cache is stable and tested.
# GPU architecture (get_array_module, gpu_blur) ready for future per-function testing.
if GPU_BACKEND in ('cuda', 'rocm') and _cupy is not None:
    print(f"[GPU] Detected {GPU_NAME} ({GPU_VRAM_MB}MB) — using CPU (noise cache + optimized blurs)")

if _GPU_COMPUTE_ENABLED and _cupy is not None:
    xp = _cupy
else:
    xp = np


def enable_gpu_compute():
    """Enable GPU acceleration at runtime. Returns True if successful."""
    global _GPU_COMPUTE_ENABLED, xp, _cupy
    if _cupy is not None:
        _GPU_COMPUTE_ENABLED = True
        xp = _cupy
        print(f"[GPU] Compute enabled ({GPU_BACKEND}: {GPU_NAME})")
        return True
    # Try importing CuPy (may have been pip-installed since startup)
    try:
        import cupy
        _cupy = cupy
        _GPU_COMPUTE_ENABLED = True
        xp = cupy
        print(f"[GPU] CuPy loaded and compute enabled")
        return True
    except ImportError:
        print("[GPU] CuPy not available — GPU compute remains disabled")
        return False


def disable_gpu_compute():
    """Disable GPU acceleration, fall back to CPU numpy."""
    global _GPU_COMPUTE_ENABLED, xp
    _GPU_COMPUTE_ENABLED = False
    xp = np
    print("[GPU] Compute disabled — using CPU (numpy)")


def install_cupy_async(callback=None):
    """Download and install CuPy via pip in background thread.
    Calls callback(success: bool, message: str) when done.
    ~90MB download for cupy-cuda12x."""
    import threading

    def _worker():
        import subprocess
        python_exe = sys.executable
        try:
            print("[GPU] Installing CuPy (cupy-cuda12x)... ~90MB download")
            result = subprocess.run(
                [python_exe, '-m', 'pip', 'install', 'cupy-cuda12x', '--quiet'],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                success = enable_gpu_compute()
                msg = "GPU acceleration installed and enabled!" if success else "CuPy installed but GPU init failed"
                print(f"[GPU] {msg}")
                if callback:
                    callback(success, msg)
            else:
                # Try CUDA 11 fallback
                result2 = subprocess.run(
                    [python_exe, '-m', 'pip', 'install', 'cupy-cuda11x', '--quiet'],
                    capture_output=True, text=True, timeout=300
                )
                if result2.returncode == 0:
                    success = enable_gpu_compute()
                    msg = "GPU acceleration installed (CUDA 11) and enabled!" if success else "CuPy installed but GPU init failed"
                    if callback:
                        callback(success, msg)
                else:
                    msg = f"CuPy installation failed. Your GPU may not support CUDA.\n{result.stderr[:200]}"
                    print(f"[GPU] {msg}")
                    if callback:
                        callback(False, msg)
        except Exception as e:
            msg = f"CuPy installation error: {e}"
            print(f"[GPU] {msg}")
            if callback:
                callback(False, msg)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread


def to_gpu(arr):
    """Transfer numpy array to GPU. No-op if GPU compute is off."""
    if _GPU_COMPUTE_ENABLED and _cupy is not None and isinstance(arr, np.ndarray):
        return _cupy.asarray(arr)
    return arr

def to_cpu(arr):
    """Transfer GPU array to CPU numpy. No-op if already numpy."""
    if _cupy is not None and hasattr(arr, 'get'):
        return arr.get()
    if hasattr(arr, '__array__'):
        return np.asarray(arr)
    return arr

def gpu_info():
    """Return dict of GPU status for UI display."""
    return {
        'backend': GPU_BACKEND,
        'name': GPU_NAME,
        'vram_mb': GPU_VRAM_MB,
        'accelerated': GPU_BACKEND != 'cpu',
        'icon': 'GPU' if GPU_BACKEND in ('cuda', 'rocm') else ('CL' if GPU_BACKEND == 'opencl' else 'CPU'),
    }

def is_gpu():
    """True if GPU compute is active (CuPy available AND enabled)."""
    return _GPU_COMPUTE_ENABLED and _cupy is not None


# ================================================================
# GPU-ASSISTED BLUR — Safe, isolated GPU acceleration for blurs.
# Does NOT require _GPU_COMPUTE_ENABLED. Only requires CuPy to exist.
# Sends one array to GPU, blurs with cupyx.scipy, returns numpy.
# No type mismatches because input/output are always numpy.
# Falls back to cv2 if CuPy unavailable or any error occurs.
# ================================================================
_gpu_blur_available = False
_cupyx_gaussian = None

try:
    if _cupy is not None:
        from cupyx.scipy.ndimage import gaussian_filter as _cupyx_gaussian_fn
        _cupyx_gaussian = _cupyx_gaussian_fn
        _gpu_blur_available = True
        print(f"[GPU] GPU-assisted blur available (cupyx.scipy.ndimage)")
except ImportError:
    pass
except Exception:
    pass


def gpu_blur(arr, sigma):
    """Gaussian blur using GPU if available, cv2 fallback otherwise.

    SAFE to call anywhere — always accepts numpy, always returns numpy.
    ~3-5x faster than cv2 for 2048x2048 arrays on RTX 4060 Ti.
    """
    if _gpu_blur_available and _cupy is not None and sigma > 0.5:
        try:
            gpu_arr = _cupy.asarray(arr.astype(np.float32))
            if gpu_arr.ndim == 2:
                result = _cupyx_gaussian(gpu_arr, sigma=sigma)
            elif gpu_arr.ndim == 3:
                # Blur each channel independently
                result = _cupy.stack([
                    _cupyx_gaussian(gpu_arr[:, :, c], sigma=sigma)
                    for c in range(gpu_arr.shape[2])
                ], axis=2)
            else:
                return arr  # Unsupported dims
            return result.get()  # Back to numpy
        except Exception:
            pass  # Fall through to cv2

    # CPU fallback: cv2.GaussianBlur
    ksize = int(sigma * 6) | 1  # Ensure odd
    if ksize < 3:
        ksize = 3
    return cv2.GaussianBlur(arr.astype(np.float32), (ksize, ksize), sigmaX=sigma, sigmaY=sigma)

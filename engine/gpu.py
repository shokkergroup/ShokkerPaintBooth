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

# GPU compute is detected but currently disabled for rendering due to
# CPU↔GPU boundary issues with external paint_fn/texture_fn functions.
# The GPU info is still reported in the UI. When GPU compute kernels are
# ready (all texture functions ported to CuPy), set _GPU_COMPUTE_ENABLED = True.
_GPU_COMPUTE_ENABLED = False

if _GPU_COMPUTE_ENABLED and GPU_BACKEND in ('cuda', 'rocm') and _cupy is not None:
    xp = _cupy
else:
    xp = np

def to_gpu(arr):
    """Transfer numpy array to GPU. No-op if on CPU backend."""
    if _cupy is not None and isinstance(arr, np.ndarray):
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
    """True if GPU acceleration is active."""
    return GPU_BACKEND != 'cpu'

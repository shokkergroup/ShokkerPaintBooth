"""Shipping seams for unique job ownership and transactional pair deploys."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = (ROOT / "server.py").read_text(encoding="utf-8")


def test_main_and_spec_sculpt_jobs_have_unique_owned_namespaces():
    assert 'job_id = f"render_{int(time.time())}_{iracing_id}_{uuid.uuid4().hex[:12]}"' in SERVER
    assert 'job_id = f"sculpt_{int(time.time())}_{iracing_id}_{uuid.uuid4().hex[:12]}"' in SERVER
    resolver = SERVER[SERVER.index("def _resolve_output_job_dir"):SERVER.index("def _spb_mkdtemp")]
    assert 'safe_job_id.startswith("render_")' in resolver
    assert 'bases = (OUTPUT_FOLDER,)' in resolver
    assert 'safe_job_id.startswith("sculpt_")' in resolver
    assert 'bases = (SPEC_SCULPT_JOBS_DIR,)' in resolver


def test_all_iracing_pair_writers_use_the_transactional_helper():
    assert "from server_routes.iracing_pair_deploy import PairDeploymentError, deploy_iracing_tga_pair" in SERVER
    push = SERVER[SERVER.index("def _push_standard_car_outputs_to_dir"):SERVER.index("def _deploy_job_dir_to_iracing_paint")]
    deploy = SERVER[SERVER.index("def _deploy_job_dir_to_iracing_paint"):SERVER.index("def _spec_sculpt_paint_preview_data_url")]
    assert "deploy_iracing_tga_pair(" in push
    assert "deploy_iracing_tga_pair(" in deploy
    assert "len(available) != 1" in deploy
    assert "Exact iRacing deployment requires one paint file" in deploy
    assert "for fname in os.listdir(job_dir)" not in deploy


def test_packaged_server_carries_the_same_pair_contract():
    packaged = (ROOT / "electron-app" / "server" / "server.py")
    # Runtime sync is the release gate; this test becomes green after the
    # source-of-truth server is mirrored for packaging.
    assert packaged.read_bytes() == (ROOT / "server.py").read_bytes()

